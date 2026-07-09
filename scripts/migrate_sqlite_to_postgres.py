from __future__ import annotations

import argparse
from collections.abc import Iterable, Iterator

from sqlalchemy import Integer, create_engine, func, select, text
from sqlalchemy.engine import Engine

from secondopinion.server.database import Base, init_db
from secondopinion.server import models  # noqa: F401 - register metadata


def clean_value(value):
    if isinstance(value, str):
        return value.replace("\x00", "")
    if isinstance(value, dict):
        return {key: clean_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clean_value(item) for item in value]
    return value


def row_batches(source: Engine, table_name: str, *, batch_size: int) -> Iterator[list[dict]]:
    table = Base.metadata.tables[table_name]
    with source.connect() as source_conn:
        result = source_conn.execution_options(stream_results=True).execute(table.select())
        batch: list[dict] = []
        for row in result:
            batch.append({key: clean_value(value) for key, value in row._mapping.items()})
            if len(batch) >= batch_size:
                yield batch
                batch = []
        if batch:
            yield batch


def copy_table(source: Engine, target: Engine, table_name: str, *, batch_size: int) -> int:
    table = Base.metadata.tables[table_name]
    copied = 0
    for batch in row_batches(source, table_name, batch_size=batch_size):
        with target.begin() as target_conn:
            target_conn.execute(table.insert(), batch)
        copied += len(batch)
        print(f"{table_name}: copied {copied}", flush=True)
    return copied


def table_count(engine: Engine, table_name: str) -> int:
    table = Base.metadata.tables[table_name]
    with engine.connect() as conn:
        return int(conn.execute(select(func.count()).select_from(table)).scalar_one())


def reset_sequences(target: Engine, table_names: Iterable[str]) -> None:
    with target.begin() as conn:
        for table_name in table_names:
            table = Base.metadata.tables[table_name]
            for column in table.columns:
                if not column.primary_key or not isinstance(column.type, Integer):
                    continue
                conn.execute(
                    text(
                        "select setval(pg_get_serial_sequence(:table_name, :column_name), "
                        f"coalesce((select max({column.name}) from {table_name}), 1), "
                        f"(select max({column.name}) from {table_name}) is not null)"
                    ),
                    {"table_name": table_name, "column_name": column.name},
                )


def main() -> None:
    parser = argparse.ArgumentParser(description="Copy SecondOpinion SQLite data into Postgres.")
    parser.add_argument("--sqlite-url", required=True)
    parser.add_argument("--postgres-url", required=True)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    source = create_engine(args.sqlite_url, future=True)
    target = create_engine(args.postgres_url, future=True)
    table_names = [table.name for table in Base.metadata.sorted_tables]

    source_counts = {table_name: table_count(source, table_name) for table_name in table_names}
    print("source counts:")
    for table_name, count in source_counts.items():
        print(f"{table_name}: {count}")
    if args.dry_run:
        print("dry run: no target changes made")
        return

    if args.replace:
        print("dropping target tables", flush=True)
        Base.metadata.drop_all(target)
    init_db(target)

    total = 0
    for table_name in table_names:
        count = copy_table(source, target, table_name, batch_size=args.batch_size)
        total += count
        print(f"{table_name}: {count}", flush=True)
    reset_sequences(target, table_names)

    target_counts = {table_name: table_count(target, table_name) for table_name in table_names}
    print("target counts:")
    for table_name, count in target_counts.items():
        expected = source_counts[table_name]
        status = "ok" if count == expected else f"expected {expected}"
        print(f"{table_name}: {count} ({status})")
    print(f"total: {total}")


if __name__ == "__main__":
    main()
