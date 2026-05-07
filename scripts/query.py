"""CLI: python -m scripts.query "your question here" [--mode hybrid|vector|graph]"""

import sys


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python -m scripts.query "your question"')
        sys.exit(1)
    raise NotImplementedError("Phase 2: wire up to retrieval + generation")


if __name__ == "__main__":
    main()
