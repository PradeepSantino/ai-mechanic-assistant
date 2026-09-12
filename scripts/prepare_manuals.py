#!/usr/bin/env python3
"""Copy service-manual PDFs into the local ingest folder with safe names."""

import json
import re
import shutil
import sys
from pathlib import Path


def safe_name(name: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(name).stem).strip("._-")
    return f"{stem}.pdf"


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: prepare_manuals.py SOURCE_DIR DEST_DIR")

    source = Path(sys.argv[1]).resolve()
    destination = Path(sys.argv[2]).resolve()
    destination.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(source.rglob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"no PDFs found under {source}")

    manifest = []
    seen = set()
    for original in pdfs:
        prepared_name = safe_name(original.name)
        if prepared_name.casefold() in seen:
            raise RuntimeError(f"safe filename collision: {prepared_name}")
        seen.add(prepared_name.casefold())
        prepared = destination / prepared_name
        shutil.copy2(original, prepared)
        manifest.append(
            {
                "original": str(original.relative_to(source)),
                "prepared": prepared.name,
                "bytes": prepared.stat().st_size,
            }
        )

    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Prepared {len(manifest)} PDFs in {destination}")


if __name__ == "__main__":
    main()
