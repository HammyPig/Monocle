#!/usr/bin/env python3
"""
This script downloads all data files and saves them to data/raw/.
"""

from utils.paths import get_project_root
from utils.download import download_file
from utils.convert import excel_sheet_to_csv

# Output directory
PROJECT_ROOT = get_project_root()
OUTPUT_DIR = PROJECT_ROOT / "data" / "raw"


def main():
    """Download all required data files."""

    # Download Simba's backtesting spreadsheet
    print("Downloading Simba's backtesting spreadsheet...")

    excel_file = OUTPUT_DIR / "simba_backtesting.xlsx"
    success = download_file(
        "https://drive.usercontent.google.com/download?id=1fTGKVC2DaHiW-NxC9J-N0PyDSYWu_Vmp&export=download&authuser=0",
        excel_file,
    )

    if success and excel_file.exists():
        print("Converting Simba's backtesting Data_Series sheet to CSV...")
        csv_file = OUTPUT_DIR / "simba_backtesting.csv"
        excel_sheet_to_csv(excel_file, "Data_Series", csv_file)

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
