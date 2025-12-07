# Monocle

This project uses `pyproject.toml` for dependency management, similar to `package.json` in Node.js projects.

## Installation

1. **Create virtual environment** (creates a `venv/` directory like `node_modules/`):
   ```bash
   python3 -m venv venv
   ```

1. **Activate the virtual environment**:
   
   On macOS/Linux:
   ```bash
   source venv/bin/activate
   ```
   
   On Windows:
   ```bash
   venv\Scripts\activate
   ```

1. **Install dependencies** (like `npm install`):
   ```bash
   pip3 install .
   ```

1. **Download data**:
   ```bash
   python scripts/download_data.py
   ```
   
   This downloads all required data files and saves them to `data/raw/`.

## Usage

1. **Activate the virtual environment** before working on the project:

    On macOS/Linux:
    ```bash
    source venv/bin/activate
    ```

    On Windows:
    ```bash
    venv\Scripts\activate
    ```
