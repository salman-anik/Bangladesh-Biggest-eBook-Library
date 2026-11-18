#!/usr/bin/env python3
"""Delegate repository catalog rebuild to build_merged_github_and_report.main()."""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_merged_github_and_report as bm  # noqa: E402


def main() -> None:
    bm.main()


if __name__ == "__main__":
    main()
