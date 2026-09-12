#!/usr/bin/env python3
"""Index prepared PDF manuals through Kotaemon's configured upload pipeline."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from gradio_client import Client, handle_file


APP_URL = "http://127.0.0.1:7860"
MANUAL_DIR = Path("/app/manuals")
DATABASE = Path("/app/ktem_app_data/user_data/sql.db")
API_NAME = "/index_fn_file_with_default_loaders"


def indexed_names() -> set[str]:
    if not DATABASE.exists():
        return set()
    with sqlite3.connect(DATABASE) as connection:
        return {
            row[0]
            for row in connection.execute(
                """
                SELECT source.name
                FROM index__1__source AS source
                JOIN index__1__index AS relation
                  ON relation.source_id = source.id
                WHERE source.name IS NOT NULL
                GROUP BY source.id, source.name
                HAVING SUM(relation.relation_type = 'document') > 0
                   AND SUM(relation.relation_type = 'vector') > 0
                """
            )
        }


def main() -> int:
    manuals = sorted(MANUAL_DIR.glob("*.pdf"))
    done = indexed_names()
    pending = [manual for manual in manuals if manual.name not in done]
    print(
        f"Found {len(manuals)} manuals: {len(done)} already indexed, "
        f"{len(pending)} pending",
        flush=True,
    )
    client = Client(APP_URL, verbose=False)
    failures: list[tuple[str, str]] = []
    started = time.monotonic()

    for position, manual in enumerate(pending, 1):
        item_started = time.monotonic()
        try:
            client.predict(
                [handle_file(str(manual))],
                api_name=API_NAME,
            )
        except Exception as error:  # continue so one damaged PDF cannot stop the run
            failures.append((manual.name, str(error)))
            outcome = f"FAILED: {error}"
        else:
            outcome = "indexed"
        elapsed = time.monotonic() - item_started
        total_elapsed = time.monotonic() - started
        print(
            f"[{position}/{len(pending)}] {manual.name}: {outcome} "
            f"({elapsed:.1f}s; total {total_elapsed / 60:.1f}m)",
            flush=True,
        )

    print(f"Completed with {len(failures)} failure(s)", flush=True)
    for name, error in failures:
        print(f"FAIL {name}: {error}", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
