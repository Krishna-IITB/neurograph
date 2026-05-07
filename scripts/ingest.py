"""CLI: python -m scripts.ingest <pdf_or_dir>"""

import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.ingest <pdf_or_dir>")
        sys.exit(1)
    source = Path(sys.argv[1])
    raise NotImplementedError("Phase 1: wire up to ingestion.pipeline.run_ingestion")


if __name__ == "__main__":
    main()
