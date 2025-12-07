#!/usr/bin/env python3
"""
This script downloads all data files and saves them to data/raw/.
"""

from utils.paths import get_project_root
from utils.download import download_file

# Output directory
PROJECT_ROOT = get_project_root()
OUTPUT_DIR = PROJECT_ROOT / "data" / "raw"


def main():
    """Download all required data files."""

    print("Downloading Simba's backtesting spreadsheet...")
    success = download_file(
        "https://drive.usercontent.google.com/download?id=1fTGKVC2DaHiW-NxC9J-N0PyDSYWu_Vmp&export=download&authuser=0",
        OUTPUT_DIR / "data.xlsx",
    )

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
