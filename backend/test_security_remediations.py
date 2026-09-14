"""
Automated tests verifying security remediations across all audit findings:
- SEC-01: SECRET_KEY validator and entropy checks
- SEC-02: File preview HTML blocking and CSP sandbox headers
- SEC-03/05: Client IP extraction and reverse proxy header handling
- SEC-04: Permanent file deletion restricted to file owners only
- SEC-06: Static asset security headers preserved in Nginx config
- SEC-07: Admin user update pre-flight uniqueness checks
- SEC-08: PDF preview iframe sandboxing in frontend
- SEC-10: Atomic storage quota reservations
"""
import io
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.responses import StreamingResponse

os.environ.setdefault("SECRET_KEY", "754426674edd36b27857f6a348161a0f9efb0b975a90e29855ad8b4309503cde")

from app.config import Settings
from app.limiter import get_real_client_ip
from app.routers.files import preview_file, delete_file_permanently, reserve_storage_quota
from app.routers.admin import update_user
from app.schemas import AdminUserUpdate
from app.models import User, File as FileModel


def make_request(headers: dict[str, str] = None, client_host: str = "127.0.0.1") -> Request:
    header_tuples = []
    if headers:
        for k, v in headers.items():
            header_tuples.append((k.lower().encode("latin-1"), v.encode("latin-1")))
    scope = {
        "type": "http",
        "method": "GET",
        "scheme": "http",
        "path": "/test",
        "headers": header_tuples,
        "client": (client_host, 12345),
    }
    return Request(scope)


class SecurityAuditRemediationTests(unittest.IsolatedAsyncioTestCase):

    # --- SEC-01: SECRET_KEY Validator ---
    def test_sec01_validate_secret_key_rejects_placeholders(self):
        # Default placeholder in uppercase
        with self.assertRaises(ValueError):
            Settings.validate_secret_key("CHANGE_THIS_TO_A_64_CHARACTER_HEX_STRING_HERE_PLEASE_0000000000000")

        # Lowercase placeholder
        with self.assertRaises(ValueError):
            Settings.validate_secret_key("change_this_to_a_64_character_hex_string_here_please_0000000000000")

        # Low entropy repetition
        with self.assertRaises(ValueError):
            Settings.validate_secret_key("a" * 64)

        with self.assertRaises(ValueError):
            Settings.validate_secret_key("0101010101010101010101010101010101010101010101010101010101010101")

        # Valid high-entropy key accepted
        valid_key = "754426674edd36b27857f6a348161a0f9efb0b975a90e29855ad8b4309503cde"
        self.assertEqual(Settings.validate_secret_key(valid_key), valid_key)

    # --- SEC-02: Stored XSS Prevention in File Preview ---
    async def test_sec02_preview_blocks_html_and_xml(self):
        blocked_exts = ["test.html", "index.htm", "doc.xhtml", "data.xml", "page.shtml"]
        dummy_user = SimpleNamespace(id="user-1", username="alice")

        for filename in blocked_exts:
            file_obj = SimpleNamespace(
                id="f1",
                name=filename,
                mime_type="text/html",
                storage_path="some/path.html",
                is_trashed=False,
                owner_id="user-1",
            )
            dummy_ctx = SimpleNamespace(is_owner=True, shared_root=None)

            with patch("app.routers.files.get_file_access_context", new=AsyncMock(return_value=(file_obj, dummy_ctx))):
                with self.assertRaises(HTTPException) as ctx:
                    await preview_file(
                        request=make_request(),
                        file_id="f1",
                        current_user=dummy_user,
                        db=AsyncMock(),
                    )
                self.assertEqual(ctx.exception.status_code, 400)
                self.assertIn("HTML and XML files cannot be previewed inline", ctx.exception.detail)

    async def test_sec02_preview_includes_csp_sandbox_header(self):
        dummy_user = SimpleNamespace(id="user-1", username="alice")
        from app.config import get_settings
        storage_dir = os.path.realpath(get_settings().storage_path)
        os.makedirs(storage_dir, exist_ok=True)
        test_file_path = os.path.join(storage_dir, "_test_preview_sample.txt")
        with open(test_file_path, "w") as f:
            f.write("safe text content")

        try:
            file_obj = SimpleNamespace(
                id="f1",
                name="sample.txt",
                type="text",
                mime_type="text/plain",
                storage_path=test_file_path,
                is_trashed=False,
                owner_id="user-1",
            )
            dummy_ctx = SimpleNamespace(is_owner=True, shared_root=None)

            with patch("app.routers.files.get_file_access_context", new=AsyncMock(return_value=(file_obj, dummy_ctx))):
                response = await preview_file(
                    request=make_request(),
                    file_id="f1",
                    current_user=dummy_user,
                    db=AsyncMock(),
                )
                self.assertIsInstance(response, StreamingResponse)
                self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")
                self.assertEqual(response.headers.get("Content-Security-Policy"), "default-src 'none'; sandbox")
        finally:
            if os.path.exists(test_file_path):
                os.remove(test_file_path)

    # --- SEC-03 & SEC-05: Reverse Proxy IP Resolution ---
    def test_sec03_get_real_client_ip_priorities(self):
        # 1. When proxy headers are untrusted, always return client.host
        with patch("app.limiter.get_settings", return_value=SimpleNamespace(trust_proxy_headers=False)):
            req = make_request(
                headers={"X-Real-IP": "203.0.113.10", "X-Forwarded-For": "198.51.100.5"},
                client_host="10.0.0.1"
            )
            self.assertEqual(get_real_client_ip(req), "10.0.0.1")

        # 2. When proxy headers are trusted, X-Real-IP takes precedence
        with patch("app.limiter.get_settings", return_value=SimpleNamespace(trust_proxy_headers=True)):
            req = make_request(
                headers={"X-Real-IP": "203.0.113.10", "X-Forwarded-For": "198.51.100.5"},
                client_host="127.0.0.1"
            )
            self.assertEqual(get_real_client_ip(req), "203.0.113.10")

        # 3. When only X-Forwarded-For is present, use leftmost client IP
        with patch("app.limiter.get_settings", return_value=SimpleNamespace(trust_proxy_headers=True)):
            req = make_request(
                headers={"X-Forwarded-For": "198.51.100.5, 172.20.0.2"},
                client_host="127.0.0.1"
            )
            self.assertEqual(get_real_client_ip(req), "198.51.100.5")

        # 4. Port numbers are stripped correctly
        with patch("app.limiter.get_settings", return_value=SimpleNamespace(trust_proxy_headers=True)):
            req = make_request(
                headers={"X-Real-IP": "203.0.113.10:443"},
                client_host="127.0.0.1"
            )
            self.assertEqual(get_real_client_ip(req), "203.0.113.10")

    # --- SEC-04: Permanent Deletion Authorization ---
    async def test_sec04_permanent_delete_rejects_non_owner(self):
        file_obj = SimpleNamespace(
            id="f1",
            name="shared_file.txt",
            owner_id="owner-uuid",
            is_trashed=True,
            storage_path=None,
            thumbnail_path=None,
            size=100,
        )
        non_owner_ctx = SimpleNamespace(
            is_owner=False,
            owner_id="owner-uuid",
            role="editor",
        )
        non_owner_user = SimpleNamespace(id="non-owner-uuid", username="bob")

        with patch("app.routers.files.get_file_access_context", new=AsyncMock(return_value=(file_obj, non_owner_ctx))):
            with self.assertRaises(HTTPException) as ctx:
                await delete_file_permanently(
                    request=make_request(),
                    file_id="f1",
                    current_user=non_owner_user,
                    db=AsyncMock(),
                )
            self.assertEqual(ctx.exception.status_code, 403)
            self.assertIn("Only the file owner can permanently delete files", ctx.exception.detail)

    # --- SEC-06: Nginx Static Asset Headers ---
    def test_sec06_nginx_config_contains_security_headers_in_static_block(self):
        nginx_path = os.path.join(os.path.dirname(__file__), "..", "nginx.conf")
        with open(nginx_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Locate static asset block
        self.assertIn("location ~* \\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$", content)
        static_block = content.split("location ~* \\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$")[1].split("}")[0]

        # Verify Cache-Control AND security headers exist in the block
        self.assertIn('add_header Cache-Control "public, immutable";', static_block)
        self.assertIn('add_header X-Frame-Options "SAMEORIGIN" always;', static_block)
        self.assertIn('add_header X-Content-Type-Options "nosniff" always;', static_block)
        self.assertIn('add_header Content-Security-Policy', static_block)
        self.assertIn('add_header Permissions-Policy', static_block)

    # --- SEC-07: Admin User Conflict Checks ---
    async def test_sec07_admin_update_rejects_duplicate_username_and_email(self):
        admin_user = SimpleNamespace(id="admin-id", is_admin=True)
        target_user = SimpleNamespace(
            id="target-id",
            username="target_user",
            email="target@example.com",
            storage_quota=1000,
            storage_used=100,
            is_admin=False,
            created_at=None,
        )
        conflicting_user = SimpleNamespace(id="conflict-id", username="taken_name", email="taken@example.com")

        mock_db = AsyncMock()
        mock_result = SimpleNamespace(scalar_one_or_none=lambda: target_user)
        mock_db.execute.return_value = mock_result

        # Duplicate username check
        with patch("app.routers.admin.get_user_by_username", new=AsyncMock(return_value=conflicting_user)):
            with self.assertRaises(HTTPException) as ctx:
                await update_user(
                    request=make_request(),
                    user_id="target-id",
                    update=AdminUserUpdate(username="taken_name"),
                    admin=admin_user,
                    db=mock_db,
                )
            self.assertEqual(ctx.exception.status_code, 400)
            self.assertEqual(ctx.exception.detail, "Username already taken")

        # Duplicate email check
        with patch("app.routers.admin.get_user_by_username", new=AsyncMock(return_value=None)):
            with patch("app.routers.admin.get_user_by_email", new=AsyncMock(return_value=conflicting_user)):
                with self.assertRaises(HTTPException) as ctx:
                    await update_user(
                        request=make_request(),
                        user_id="target-id",
                        update=AdminUserUpdate(email="taken@example.com"),
                        admin=admin_user,
                        db=mock_db,
                    )
                self.assertEqual(ctx.exception.status_code, 400)
                self.assertEqual(ctx.exception.detail, "Email already registered")

    # --- SEC-08: PDF Preview Sandbox ---
    def test_sec08_file_preview_modal_contains_sandbox(self):
        modal_path = os.path.join(os.path.dirname(__file__), "..", "src", "components", "FilePreviewModal.jsx")
        with open(modal_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn('sandbox="allow-scripts"', content)

    # --- SEC-10: Atomic Storage Quota Reservation ---
    async def test_sec10_reserve_storage_quota_atomic_behavior(self):
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
        from sqlalchemy.orm import DeclarativeBase
        from app.database import Base

        eng = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_maker = async_sessionmaker(eng, class_=AsyncSession)
        async with session_maker() as session:
            # 1. User with 100-byte quota, currently 40 bytes used
            user_limited = User(
                id="u_limited",
                email="u1@example.com",
                username="u1",
                password_hash="hash",
                storage_quota=100,
                storage_used=40,
            )
            # 2. User with unlimited quota (storage_quota = 0)
            user_unlimited = User(
                id="u_unlimited",
                email="u2@example.com",
                username="u2",
                password_hash="hash",
                storage_quota=0,
                storage_used=5000,
            )
            session.add_all([user_limited, user_unlimited])
            await session.commit()

        async with session_maker() as session:
            # Adding 50 bytes should succeed (40 + 50 = 90 <= 100)
            success = await reserve_storage_quota(session, "u_limited", 50)
            self.assertTrue(success)
            await session.commit()

        async with session_maker() as session:
            # Adding another 20 bytes should fail (90 + 20 = 110 > 100)
            fail = await reserve_storage_quota(session, "u_limited", 20)
            self.assertFalse(fail)

            # Unlimited user can reserve 10,000 bytes without error
            unlimited_success = await reserve_storage_quota(session, "u_unlimited", 10000)
            self.assertTrue(unlimited_success)
            await session.commit()

        async with session_maker() as session:
            u1 = await session.get(User, "u_limited")
            u2 = await session.get(User, "u_unlimited")
            self.assertEqual(u1.storage_used, 90)
            self.assertEqual(u2.storage_used, 15000)


if __name__ == "__main__":
    unittest.main()
