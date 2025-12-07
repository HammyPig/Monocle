"""Path utility functions."""

from pathlib import Path


def get_project_root():
    """
    Find project root by walking up from current file looking for pyproject.toml.
    Similar to how Node.js/npm tools find project root by looking for package.json.

    Raises:
        FileNotFoundError: If pyproject.toml is not found in any parent directory.
    """

    # Start from the current file's directory and walk up
    path = Path(__file__).resolve().parent
    while path != path.parent:
        if (path / "pyproject.toml").exists():
            return path
        path = path.parent

    # If not found, raise an error with details
    raise FileNotFoundError(
        "Could not find project root: pyproject.toml not found in any parent directory."
    )
