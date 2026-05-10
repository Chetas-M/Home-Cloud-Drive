import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from starlette.requests import Request

os.environ.setdefault("SECRET_KEY", "0123456789abcdef0123456789abcdef")

from app.routers.files import bulk_action  # noqa: E402
from app.schemas import BulkActionRequest  # noqa: E402


def make_request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "scheme": "http",
            "path": "/api/files/bulk",
            "headers": [(b"host", b"testserver")],
            "server": ("testserver", 80),
        }
    )


class _FileResult:
    def __init__(self, files):
        self._files = files

    def scalars(self):
        return self

    def all(self):
        return self._files


class BulkActionEndpointTests(unittest.IsolatedAsyncioTestCase):
    def _make_db(self, files):
        db = SimpleNamespace()
        db.execute = AsyncMock(return_value=_FileResult(files))
        db.flush = AsyncMock()
        return db

    @patch("app.routers.files.trash_file", new_callable=AsyncMock)
    async def test_bulk_trash_delegates_to_recursive_trash_logic(self, trash_file_mock):
        file1 = SimpleNamespace(id="f1")
        file2 = SimpleNamespace(id="f2")
        db = self._make_db([file1, file2])
        user = SimpleNamespace(id="u1")

        result = await bulk_action(
            request=make_request(),
            body=BulkActionRequest(file_ids=["f1", "f2"], action="trash"),
            current_user=user,
            db=db,
        )

        self.assertEqual(result["succeeded"], ["f1", "f2"])
        self.assertEqual(result["failed"], [])
        self.assertEqual(trash_file_mock.await_count, 2)

    @patch("app.routers.files.update_file", new_callable=AsyncMock)
    async def test_bulk_move_allows_root_target_path(self, update_file_mock):
        file1 = SimpleNamespace(id="f1")
        db = self._make_db([file1])
        user = SimpleNamespace(id="u1")

        result = await bulk_action(
            request=make_request(),
            body=BulkActionRequest(file_ids=["f1"], action="move", target_path=[]),
            current_user=user,
            db=db,
        )

        self.assertEqual(result["succeeded"], ["f1"])
        self.assertEqual(result["failed"], [])
        called_update = update_file_mock.await_args.kwargs["update"]
        self.assertEqual(called_update.path, [])

    @patch("app.routers.files.copy_file", new_callable=AsyncMock)
    async def test_bulk_copy_reports_copy_failures(self, copy_file_mock):
        file1 = SimpleNamespace(id="f1")
        db = self._make_db([file1])
        user = SimpleNamespace(id="u1")
        copy_file_mock.side_effect = HTTPException(status_code=404, detail="File not found on disk")

        result = await bulk_action(
            request=make_request(),
            body=BulkActionRequest(file_ids=["f1"], action="copy"),
            current_user=user,
            db=db,
        )

        self.assertEqual(result["succeeded"], [])
        self.assertEqual(result["failed"][0]["id"], "f1")
        self.assertIn("File not found on disk", result["failed"][0]["error"])

    async def test_bulk_action_marks_unknown_file_ids_as_not_found(self):
        file1 = SimpleNamespace(id="f1")
        db = self._make_db([file1])
        user = SimpleNamespace(id="u1")

        result = await bulk_action(
            request=make_request(),
            body=BulkActionRequest(file_ids=["f1", "missing"], action="download"),
            current_user=user,
            db=db,
        )

        self.assertEqual(result["succeeded"], ["f1"])
        self.assertEqual(result["failed"], [{"id": "missing", "error": "Not found"}])


if __name__ == "__main__":
    unittest.main()
