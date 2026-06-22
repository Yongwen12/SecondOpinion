from __future__ import annotations

import argparse
from collections.abc import Iterable

from sqlalchemy import Integer, create_engine, text
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


def copy_table(source: Engine, target: Engine, table_name: str) -> int:
    table = Base.metadata.tables[table_name]
    with source.connect() as source_conn:
        rows = [
            {key: clean_value(value) for key, value in row._mapping.items()}
            for row in source_conn.execute(table.select())
        ]
    if not rows:
        return 0
    with target.begin() as target_conn:
        target_conn.execute(table.insert(), rows)
    return len(rows)


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
    args = parser.parse_args()

    source = create_engine(args.sqlite_url, future=True)
    target = create_engine(args.postgres_url, future=True)
    table_names = [table.name for table in Base.metadata.sorted_tables]
    if args.replace:
        Base.metadata.drop_all(target)
    init_db(target)

    total = 0
    for table_name in table_names:
        count = copy_table(source, target, table_name)
        total += count
        print(f"{table_name}: {count}")
    reset_sequences(target, table_names)
    print(f"total: {total}")


if __name__ == "__main__":
    main()
