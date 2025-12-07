"""Download utility functions."""

import requests
from pathlib import Path

# Download chunk size (8KB)
CHUNK_SIZE = 8192


def download_file(url: str, output_path: Path) -> bool:
    """
    Download a file from a URL to a specified path.

    Args:
        url: URL to download from
        output_path: Path where the file should be saved

    Returns:
        True if download succeeded, False otherwise
    """

    # Create output directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Downloading from: {url}")
    print(f"Save to: {output_path}")

    try:
        # Download the file
        response = requests.get(url, stream=True)
        response.raise_for_status()

        # Save to file in chunks
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                f.write(chunk)

        file_size = output_path.stat().st_size / (1024 * 1024)  # Size in MB
        print(f"Downloaded successfully: {output_path}")
        print(f"File size: {file_size:.2f} MB")

        return True

    except requests.exceptions.RequestException as e:
        print(f"Error downloading file: {e}")
        return False
