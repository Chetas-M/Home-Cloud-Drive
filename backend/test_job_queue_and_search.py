"""
Tests for the background job queue and rich search indexing.
"""
import asyncio
import os
import tempfile
import pytest
import sys

# Ensure the backend app is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))


# ---------------------------------------------------------------------------
# Job Queue Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_job_queue_basic_enqueue_and_run():
    """A registered handler is called when a job is enqueued."""
    from app.job_queue import BackgroundJobQueue, register_handler, JobStatus

    results = []

    async def fake_handler(payload):
        results.append(payload["value"])

    register_handler("_test_basic", fake_handler)

    q = BackgroundJobQueue(concurrency=1)
    await q.start()
    job_id = await q.enqueue("_test_basic", {"value": 42}, max_attempts=1)

    # Give the worker time to process
    await asyncio.sleep(0.3)
    await q.shutdown(timeout=2.0)

    assert 42 in results
    status = await q.get_status(job_id)
    assert status is not None
    assert status["status"] == JobStatus.DONE


@pytest.mark.asyncio
async def test_job_queue_retry_on_failure():
    """A failing handler is retried up to max_attempts times."""
    from app.job_queue import BackgroundJobQueue, register_handler, JobStatus, JOB_RETRY_POLICY

    attempts = []

    async def flaky_handler(payload):
        attempts.append(1)
        raise RuntimeError("deliberate failure")

    register_handler("_test_retry", flaky_handler)
    # Override retry policy: no back-off delay for tests
    JOB_RETRY_POLICY["_test_retry"] = []

    q = BackgroundJobQueue(concurrency=1)
    await q.start()
    job_id = await q.enqueue("_test_retry", {}, max_attempts=3)

    # Wait long enough for all retries
    await asyncio.sleep(0.8)
    await q.shutdown(timeout=2.0)

    assert len(attempts) == 3
    status = await q.get_status(job_id)
    assert status["status"] == JobStatus.FAILED


@pytest.mark.asyncio
async def test_job_queue_stats():
    """Stats reflect enqueued/completed job counts."""
    from app.job_queue import BackgroundJobQueue, register_handler

    async def noop_handler(payload):
        pass

    register_handler("_test_stats", noop_handler)

    q = BackgroundJobQueue(concurrency=1)
    await q.start()
    await q.enqueue("_test_stats", {}, max_attempts=1)
    await asyncio.sleep(0.3)
    await q.shutdown(timeout=2.0)

    stats = q.stats()
    assert "by_status" in stats
    assert "failures_by_type" in stats
    assert "successes_by_type" in stats


# ---------------------------------------------------------------------------
# Rich Search Indexing Tests
# ---------------------------------------------------------------------------

def _write_temp_file(suffix: str, content: bytes) -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as fh:
        fh.write(content)
    return path


def test_plain_text_extraction():
    """Plain text files are indexed correctly."""
    from app.search_index import build_search_document

    path = _write_temp_file(".txt", b"Hello world this is a test document")
    try:
        result = build_search_document(path, "test.txt", "text/plain", "text")
        assert result is not None
        assert "Hello world" in result
    finally:
        os.unlink(path)


def test_unknown_binary_returns_none():
    """Binary blobs with no extractor return None."""
    from app.search_index import build_search_document

    path = _write_temp_file(".bin", b"\x00\x01\x02\x03\xff\xfe")
    try:
        result = build_search_document(path, "data.bin", "application/octet-stream", "file")
        # Should be None or empty — never crash
        assert result is None or isinstance(result, str)
    finally:
        os.unlink(path)


def test_missing_file_returns_none():
    """A non-existent file path returns None without raising."""
    from app.search_index import build_search_document

    result = build_search_document("/nonexistent/path/file.txt", "file.txt", "text/plain", "text")
    assert result is None


def test_pdf_extraction_graceful_when_no_library():
    """PDF extraction returns None (not an exception) when pypdf/pdfminer is absent."""
    from app.search_index import _extract_pdf
    import unittest.mock as mock

    # Simulate no PDF libraries being installed
    with mock.patch.dict("sys.modules", {"pdfminer": None, "pdfminer.high_level": None, "pypdf": None}):
        path = _write_temp_file(".pdf", b"%PDF-1.4 fake content")
        try:
            result = _extract_pdf(path)
            # Should return None gracefully (not raise ImportError)
            assert result is None or isinstance(result, str)
        finally:
            os.unlink(path)


def test_should_extract_text_routing():
    """should_extract_text correctly identifies indexable file types."""
    from app.search_index import should_extract_text

    assert should_extract_text("readme.md", "text/markdown", "text") is True
    assert should_extract_text("report.pdf", "application/pdf", "pdf") is True
    assert should_extract_text("data.xlsx", "application/vnd.openxmlformats", "file") is True
    assert should_extract_text("photo.jpg", "image/jpeg", "image") is True
    assert should_extract_text("video.mp4", "video/mp4", "video") is False


def test_build_match_context_content_snippet(tmp_path):
    """build_match_context returns a snippet around the matched query."""
    from app.search_index import build_match_context
    from app.models import File as FileModel

    # Build a minimal File-like object using a dataclass workaround
    class FakeFile:
        name = "document.txt"
        type = "text"
        mime_type = "text/plain"
        content_index = (
            "This is a long piece of text that contains the word elephant "
            "somewhere in the middle of the content for testing purposes."
        )

    file = FakeFile()
    ctx = build_match_context(file, "elephant", ["docs"])
    assert ctx is not None
    assert "elephant" in ctx.lower() or "…" in ctx


def test_build_match_context_name_match():
    """build_match_context matches on filename when content is empty."""
    from app.search_index import build_match_context

    class FakeFile:
        name = "quarterly_report.docx"
        type = "file"
        mime_type = None
        content_index = ""

    file = FakeFile()
    ctx = build_match_context(file, "quarterly", [])
    assert ctx is not None
    assert "quarterly" in ctx.lower()


def test_normalize_whitespace():
    """normalize_whitespace collapses tabs and newlines."""
    from app.search_index import normalize_whitespace

    result = normalize_whitespace("  hello\n\t world  ")
    assert result == "hello world"
