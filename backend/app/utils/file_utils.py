from __future__ import annotations

from pathlib import Path
import json
from typing import Any
import pandas as pd


def ensure_parent_dir(path: Path) -> None:
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)


def safe_to_csv(df: pd.DataFrame, path: Path, mode: str = "w", header: bool = True, index: bool = False) -> None:
    ensure_parent_dir(path)
    # If writing fresh and file doesn't exist, write headers
    if mode == "w":
        df.to_csv(path, index=index, header=header)
    else:
        df.to_csv(path, mode=mode, header=header, index=index)


def safe_append_csv(df: pd.DataFrame, path: Path) -> None:
    ensure_parent_dir(path)
    df.to_csv(path, mode="a", header=not path.exists(), index=False)


def safe_json_dump(data: Any, path: Path, indent: int = 4) -> None:
    ensure_parent_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, default=str)


def safe_write_text(text: str, path: Path) -> None:
    ensure_parent_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
