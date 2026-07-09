from __future__ import annotations

from ..openreview_scope_audit import main


if __name__ == "__main__":
    main(__import__("sys").argv[1:])
