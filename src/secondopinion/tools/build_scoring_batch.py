from __future__ import annotations

from ..batch_review_scoring import main


if __name__ == "__main__":
    main(["build-batch", *(__import__("sys").argv[1:])])
