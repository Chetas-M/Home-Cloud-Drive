"""
Validation helpers for folder/file tree metadata.
"""
import unicodedata
from typing import List

from fastapi import HTTPException


def sanitize_tree_name(name: str | None) -> str:
    """Normalize a single folder/file path segment."""
    if name is None:
        raise HTTPException(status_code=400, detail="File/folder name is invalid")

    sanitized_chars: list[str] = []
    for char in name.replace("\x00", ""):
        if char in {"/", "\\", "\r", "\n"}:
            sanitized_chars.append("_")
            continue
        if unicodedata.category(char).startswith("C"):
            continue
        sanitized_chars.append(char)

    sanitized = "".join(sanitized_chars).strip().strip(".")
    if not sanitized:
        raise HTTPException(status_code=400, detail="File/folder name is invalid")
    return sanitized


def normalize_tree_path(path: List[str] | None) -> List[str]:
    """Validate and normalize a JSON path array from the client."""
    if path is None:
        return []
    if not isinstance(path, list):
        raise HTTPException(status_code=400, detail="Path is invalid")
    return [sanitize_tree_name(segment) for segment in path]
