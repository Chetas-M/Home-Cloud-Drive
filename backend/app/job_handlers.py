"""
Home Cloud Drive - Job Handlers
================================
Registers concrete async handlers for each background job type.

Job types
---------
``thumbnail``     – Generate a thumbnail for an uploaded file.
``search_index``  – Build/refresh ``content_index`` for a file.
``email``         – Send a transactional email via Resend.
``trash_cleanup`` – Purge expired trashed files.
``log_cleanup``   – Prune old activity-log rows.

Call ``register_all_handlers()`` once at startup (done in ``main.py``).
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict

from app.job_queue import register_handler, job_queue

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# thumbnail
# ---------------------------------------------------------------------------

async def _handle_thumbnail(payload: Dict[str, Any]) -> None:
    """
    Generate a thumbnail for an image file and update the database.

    Expected payload keys:
        file_id         : str  – UUID of the file row
        storage_path    : str  – Absolute path to the source file
        thumbnail_dir   : str  – Directory to store thumbnails
    """
    import asyncio
    from app.thumbnails import generate_thumbnail
    from app.database import async_session
    from app.models import File as FileModel
    from sqlalchemy import select

    file_id: str = payload["file_id"]
    storage_path: str = payload["storage_path"]
    thumbnail_dir: str = payload["thumbnail_dir"]

    if not os.path.exists(storage_path):
        raise FileNotFoundError(f"Source file not found: {storage_path}")

    thumb_path = await asyncio.to_thread(
        generate_thumbnail, storage_path, thumbnail_dir, file_id
    )

    if thumb_path is None:
        raise RuntimeError(f"Thumbnail generation returned None for file {file_id}")

    async with async_session() as db:
        result = await db.execute(select(FileModel).where(FileModel.id == file_id))
        file = result.scalar_one_or_none()
        if file is not None:
            file.thumbnail_path = thumb_path
            await db.commit()
            logger.info("job/thumbnail: generated thumbnail for file %s", file_id)
        else:
            logger.warning("job/thumbnail: file %s not found in DB, skipping DB update", file_id)


# ---------------------------------------------------------------------------
# search_index
# ---------------------------------------------------------------------------

async def _handle_search_index(payload: Dict[str, Any]) -> None:
    """
    Extract text content and update ``content_index`` for a single file.

    Expected payload keys:
        file_id      : str  – UUID of the file row
        storage_path : str  – Absolute path to the file on disk
        filename     : str  – Original filename (used for type detection)
        mime_type    : str | None
        file_type    : str  – Logical file type (pdf, text, image, …)
    """
    import asyncio
    from app.search_index import build_search_document
    from app.database import async_session
    from app.models import File as FileModel
    from sqlalchemy import select

    file_id: str = payload["file_id"]
    storage_path: str = payload["storage_path"]
    filename: str = payload["filename"]
    mime_type: str | None = payload.get("mime_type")
    file_type: str = payload.get("file_type", "file")

    content = await asyncio.to_thread(
        build_search_document, storage_path, filename, mime_type, file_type
    )

    async with async_session() as db:
        result = await db.execute(select(FileModel).where(FileModel.id == file_id))
        file = result.scalar_one_or_none()
        if file is not None:
            file.content_index = content or ""
            await db.commit()
            logger.info(
                "job/search_index: indexed file %s (%d chars)",
                file_id, len(content or ""),
            )
        else:
            logger.warning("job/search_index: file %s not found in DB", file_id)


# ---------------------------------------------------------------------------
# email
# ---------------------------------------------------------------------------

async def _handle_email(payload: Dict[str, Any]) -> None:
    """
    Send a transactional email via the configured email service.

    Expected payload keys:
        to      : str  – Recipient address
        subject : str
        html    : str  – HTML body
        text    : str | None  – Plain-text fallback
    """
    import asyncio
    from app.email_service import _send_email

    to: str = payload["to"]
    subject: str = payload["subject"]
    html_body: str = payload["html"]
    text_body: str = payload.get("text") or ""

    # _send_email uses blocking urllib; run in a thread to avoid blocking the event loop
    await asyncio.to_thread(_send_email, to, subject, text_body, html_body)
    logger.info("job/email: sent email to %s (subject=%r)", to, subject)


# ---------------------------------------------------------------------------
# trash_cleanup
# ---------------------------------------------------------------------------

async def _handle_trash_cleanup(payload: Dict[str, Any]) -> None:  # noqa: ARG001
    """Run the full trash auto-delete pass."""
    from app.main import cleanup_old_trash

    await cleanup_old_trash()
    logger.info("job/trash_cleanup: completed")


# ---------------------------------------------------------------------------
# log_cleanup
# ---------------------------------------------------------------------------

async def _handle_log_cleanup(payload: Dict[str, Any]) -> None:  # noqa: ARG001
    """Run the activity-log retention pass."""
    from app.main import cleanup_activity_logs

    await cleanup_activity_logs()
    logger.info("job/log_cleanup: completed")


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_all_handlers() -> None:
    """Register all job handlers.  Call once at startup."""
    register_handler("thumbnail", _handle_thumbnail)
    register_handler("search_index", _handle_search_index)
    register_handler("email", _handle_email)
    register_handler("trash_cleanup", _handle_trash_cleanup)
    register_handler("log_cleanup", _handle_log_cleanup)
    logger.info("job_queue: all handlers registered")
