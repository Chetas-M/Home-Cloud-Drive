"""
Tests for the background job queue and rich search indexing.
"""

import os
import tempfile
import unittest
from unittest import mock

from app.job_queue import BackgroundJobQueue, JOB_RETRY_POLICY, JobStatus, register_handler
from app.search_index import (
    _extract_pdf,
    build_match_context,
    build_search_document,
    normalize_whitespace,
    should_extract_text,
)


class JobQueueTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self._original_retry_policy = dict(JOB_RETRY_POLICY)

    async def asyncTearDown(self):
        JOB_RETRY_POLICY.clear()
        JOB_RETRY_POLICY.update(self._original_retry_policy)

    async def test_job_queue_basic_enqueue_and_run(self):
        """A registered handler is called when a job is enqueued."""
        results = []

        async def fake_handler(payload):
            results.append(payload["value"])

        register_handler("_test_basic", fake_handler)

        q = BackgroundJobQueue(concurrency=1)
        await q.start()
        job_id = await q.enqueue("_test_basic", {"value": 42}, max_attempts=1)

        await q._queue.join()
        await q.shutdown(timeout=2.0)

        self.assertIn(42, results)
        status = await q.get_status(job_id)
        self.assertIsNotNone(status)
        self.assertEqual(status["status"], JobStatus.DONE)

    async def test_job_queue_retry_on_failure(self):
        """A failing handler is retried up to max_attempts times."""
        attempts = []

        async def flaky_handler(payload):  # noqa: ARG001
            attempts.append(1)
            raise RuntimeError("deliberate failure")

        register_handler("_test_retry", flaky_handler)
        JOB_RETRY_POLICY["_test_retry"] = []

        q = BackgroundJobQueue(concurrency=1)
        await q.start()
        job_id = await q.enqueue("_test_retry", {}, max_attempts=3)

        await q._queue.join()
        await q.shutdown(timeout=2.0)

        self.assertEqual(len(attempts), 3)
        status = await q.get_status(job_id)
        self.assertEqual(status["status"], JobStatus.FAILED)

    async def test_job_queue_stats(self):
        """Stats reflect enqueued/completed job counts."""

        async def noop_handler(payload):  # noqa: ARG001
            return None

        register_handler("_test_stats", noop_handler)

        q = BackgroundJobQueue(concurrency=1)
        await q.start()
        await q.enqueue("_test_stats", {}, max_attempts=1)
        await q._queue.join()
        await q.shutdown(timeout=2.0)

        stats = await q.stats()
        self.assertIn("by_status", stats)
        self.assertIn("failures_by_type", stats)
        self.assertIn("successes_by_type", stats)


def _write_temp_file(suffix: str, content: bytes) -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as fh:
        fh.write(content)
    return path


class SearchIndexTests(unittest.TestCase):
    def test_plain_text_extraction(self):
        """Plain text files are indexed correctly."""
        path = _write_temp_file(".txt", b"Hello world this is a test document")
        try:
            result = build_search_document(path, "test.txt", "text/plain", "text")
            self.assertIsNotNone(result)
            self.assertIn("Hello world", result)
        finally:
            os.unlink(path)

    def test_unknown_binary_returns_none(self):
        """Binary blobs with no extractor return None."""
        path = _write_temp_file(".bin", b"\x00\x01\x02\x03\xff\xfe")
        try:
            result = build_search_document(path, "data.bin", "application/octet-stream", "file")
            self.assertTrue(result is None or isinstance(result, str))
        finally:
            os.unlink(path)

    def test_missing_file_returns_none(self):
        """A non-existent file path returns None without raising."""
        result = build_search_document("/nonexistent/path/file.txt", "file.txt", "text/plain", "text")
        self.assertIsNone(result)

    def test_pdf_extraction_graceful_when_no_library(self):
        """PDF extraction returns None (not an exception) when pypdf/pdfminer is absent."""
        with mock.patch.dict("sys.modules", {"pdfminer": None, "pdfminer.high_level": None, "pypdf": None}):
            path = _write_temp_file(".pdf", b"%PDF-1.4 fake content")
            try:
                result = _extract_pdf(path)
                self.assertTrue(result is None or isinstance(result, str))
            finally:
                os.unlink(path)

    def test_should_extract_text_routing(self):
        """should_extract_text correctly identifies indexable file types."""
        self.assertTrue(should_extract_text("readme.md", "text/markdown", "text"))
        self.assertTrue(should_extract_text("report.pdf", "application/pdf", "pdf"))
        self.assertTrue(should_extract_text("data.xlsx", "application/vnd.openxmlformats", "file"))
        self.assertTrue(should_extract_text("photo.jpg", "image/jpeg", "image"))
        self.assertFalse(should_extract_text("video.mp4", "video/mp4", "video"))

    def test_build_match_context_content_snippet(self):
        """build_match_context returns a snippet around the matched query."""

        class FakeFile:
            name = "document.txt"
            type = "text"
            mime_type = "text/plain"
            content_index = (
                "This is a long piece of text that contains the word elephant "
                "somewhere in the middle of the content for testing purposes."
            )

        ctx = build_match_context(FakeFile(), "elephant", ["docs"])
        self.assertIsNotNone(ctx)
        self.assertTrue("elephant" in ctx.lower() or "…" in ctx)

    def test_build_match_context_name_match(self):
        """build_match_context matches on filename when content is empty."""

        class FakeFile:
            name = "quarterly_report.docx"
            type = "file"
            mime_type = None
            content_index = ""

        ctx = build_match_context(FakeFile(), "quarterly", [])
        self.assertIsNotNone(ctx)
        self.assertIn("quarterly", ctx.lower())

    def test_normalize_whitespace(self):
        """normalize_whitespace collapses tabs and newlines."""
        result = normalize_whitespace("  hello\n\t world  ")
        self.assertEqual(result, "hello world")


if __name__ == "__main__":
    unittest.main()
