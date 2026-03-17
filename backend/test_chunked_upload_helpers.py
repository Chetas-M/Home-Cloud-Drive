import asyncio
import os
import tempfile
import time
import unittest

from fastapi import HTTPException

from backend.app.routers.files import (
    cleanup_stale_uploads,
    get_temp_upload_size,
    load_upload_session_metadata,
    write_upload_session_metadata,
)

TEST_TMP_ROOT = os.path.join(os.path.dirname(__file__), ".codex-test-tmp")


class ChunkedUploadHelperTests(unittest.TestCase):
    def make_temp_dir(self):
        os.makedirs(TEST_TMP_ROOT, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT)

    def test_metadata_round_trip(self):
        with self.make_temp_dir() as temp_dir:
            metadata = {
                "filename": "report.pdf",
                "total_size": 1234,
                "path": ["docs"],
            }

            write_upload_session_metadata(temp_dir, metadata)

            self.assertEqual(load_upload_session_metadata(temp_dir), metadata)

    def test_missing_metadata_raises_not_found(self):
        with self.make_temp_dir() as temp_dir:
            with self.assertRaises(HTTPException) as context:
                load_upload_session_metadata(temp_dir)

            self.assertEqual(context.exception.status_code, 404)

    def test_temp_upload_size_excludes_selected_chunk(self):
        with self.make_temp_dir() as temp_dir:
            chunk_a = os.path.join(temp_dir, "chunk_0")
            chunk_b = os.path.join(temp_dir, "chunk_1")
            ignored = os.path.join(temp_dir, "notes.txt")

            with open(chunk_a, "wb") as file_obj:
                file_obj.write(b"a" * 3)
            with open(chunk_b, "wb") as file_obj:
                file_obj.write(b"b" * 5)
            with open(ignored, "wb") as file_obj:
                file_obj.write(b"ignored")

            self.assertEqual(get_temp_upload_size(temp_dir), 8)
            self.assertEqual(get_temp_upload_size(temp_dir, exclude_chunk="chunk_1"), 3)

    def test_cleanup_stale_uploads_removes_only_expired_directories(self):
        with self.make_temp_dir() as base_tmp_dir:
            stale_dir = os.path.join(base_tmp_dir, "stale")
            fresh_dir = os.path.join(base_tmp_dir, "fresh")
            os.makedirs(stale_dir, exist_ok=True)
            os.makedirs(fresh_dir, exist_ok=True)

            stale_timestamp = time.time() - 120
            os.utime(stale_dir, (stale_timestamp, stale_timestamp))

            asyncio.run(cleanup_stale_uploads(base_tmp_dir, ttl_seconds=60))

            self.assertFalse(os.path.exists(stale_dir))
            self.assertTrue(os.path.exists(fresh_dir))


if __name__ == "__main__":
    unittest.main()
