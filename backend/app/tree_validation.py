"""
Validation helpers for folder/file tree metadata.
"""
import unicodedata
from typing import List

from fastapi import HTTPException


def sanitize_tree_name(name: str | None) -> str:
    """Validate a single folder/file path segment without rewriting it."""
    if name is None or name == "":
        raise HTTPException(status_code=400, detail="File/folder name is invalid")

    if name != name.strip() or name != name.strip("."):
        raise HTTPException(status_code=400, detail="File/folder name is invalid")

    for char in name:
        if char in {"/", "\\", "\r", "\n", "\x00"}:
            raise HTTPException(status_code=400, detail="File/folder name is invalid")
        if unicodedata.category(char).startswith("C"):
            raise HTTPException(status_code=400, detail="File/folder name is invalid")

    return name


def normalize_tree_path(path: List[str] | None) -> List[str]:
    """Validate a JSON path array from the client without changing segments."""
    if path is None:
        return []
    if not isinstance(path, list):
        raise HTTPException(status_code=400, detail="Path is invalid")
    return [sanitize_tree_name(segment) for segment in path]
