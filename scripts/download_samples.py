"""Download a few public Wikipedia article PDFs into data/sample_pdfs/.

CLI: `python -m scripts.download_samples`

Wikipedia exposes a PDF rendering endpoint at:
    https://en.wikipedia.org/api/rest_v1/page/pdf/<Article_Title>

This is the simplest way to get realistic, multi-entity PDFs for the
demo without bundling binaries in the repo.
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx
from loguru import logger

ARTICLES = [
    "Elon_Musk",
    "Tesla,_Inc.",
    "SpaceX",
]

DEST = Path("data/sample_pdfs")


def download_one(title: str, dest: Path) -> bool:
    url = f"https://en.wikipedia.org/api/rest_v1/page/pdf/{title}"
    out = dest / f"{title}.pdf"
    if out.exists():
        logger.info(f"  ✓ Already have {out.name} ({out.stat().st_size // 1024} KB)")
        return True
    logger.info(f"  → Downloading {title}...")
    try:
        with httpx.Client(follow_redirects=True, timeout=60.0) as client:
            r = client.get(url, headers={"User-Agent": "neurograph/0.1 (academic project)"})
            r.raise_for_status()
            out.write_bytes(r.content)
        logger.info(f"  ✓ Saved {out.name} ({len(r.content) // 1024} KB)")
        return True
    except Exception as e:
        logger.error(f"  ✗ Failed for {title}: {e}")
        return False


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    logger.info(f"Downloading {len(ARTICLES)} sample PDFs into {DEST}/")
    ok = sum(download_one(a, DEST) for a in ARTICLES)
    logger.info(f"Done: {ok}/{len(ARTICLES)} succeeded.")
    if ok == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
