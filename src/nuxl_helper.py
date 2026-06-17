import shutil
from pathlib import Path

def reset_directory(path: Path) -> None:
    """
    Remove the given directory and re-create it.

    Args:
        path (Path): Path to the directory to be reset.

    Returns:
        None
    """
    path = Path(path)
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
