"""Conversion utility functions."""

from pathlib import Path
from xlsx2csv import Xlsx2csv


def excel_sheet_to_csv(excel_file: Path, sheet_name: str, csv_file: Path) -> bool:
    """
    Convert an Excel sheet to CSV using xlsx2csv.

    Args:
        excel_file: Path to the Excel file
        sheet_name: Name of the sheet to convert
        csv_file: Path where the CSV file should be saved

    Returns:
        True if conversion succeeded, False otherwise
    """
    try:
        Xlsx2csv(str(excel_file)).convert(str(csv_file), sheetname=sheet_name)
        print(f"Converted {sheet_name} to {csv_file}")
        return True

    except Exception as e:
        print(f"Error converting {sheet_name} to CSV: {e}")
        return False
