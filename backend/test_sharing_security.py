import os
import unittest
from unittest.mock import AsyncMock, Mock

from fastapi import HTTPException
from pydantic import ValidationError

os.environ.setdefault("SECRET_KEY", "0123456789abcdef0123456789abcdef")

from app.models import ShareLink  # noqa: E402
from app.routers.sharing import reserve_share_download_slot  # noqa: E402
from app.schemas import ShareLinkCreate  # noqa: E402


class ShareLinkSchemaTests(unittest.TestCase):
    def test_rejects_unknown_permission(self):
        with self.assertRaises(ValidationError):
            ShareLinkCreate(file_id="file-1", permission="edit")

    def test_rejects_non_positive_max_downloads(self):
        with self.assertRaises(ValidationError):
            ShareLinkCreate(file_id="file-1", permission="download", max_downloads=0)


class ShareDownloadSlotTests(unittest.IsolatedAsyncioTestCase):
    async def test_raises_when_no_capped_download_slots_remain(self):
        db = AsyncMock()
        db.execute = AsyncMock(return_value=Mock(rowcount=0))
        db.flush = AsyncMock()
        link = ShareLink(id="link-1", max_downloads=1)

        with self.assertRaises(HTTPException) as ctx:
            await reserve_share_download_slot(db, link)

        self.assertEqual(ctx.exception.status_code, 410)
        db.flush.assert_not_awaited()

    async def test_unlimited_links_increment_without_cap_check(self):
        db = AsyncMock()
        db.execute = AsyncMock(return_value=Mock(rowcount=1))
        db.flush = AsyncMock()
        link = ShareLink(id="link-1", max_downloads=None)

        await reserve_share_download_slot(db, link)

        db.flush.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
