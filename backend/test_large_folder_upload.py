import unittest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from app.main import app

class TestLargeFolderUploadRateLimits(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from app.routers.auth import get_current_user
        from app.models import User
        
        self.mock_user = User(
            id="test-user-id", 
            username="testuser", 
            email="test@test.com",
            storage_quota=0,
            storage_used=0
        )
        
        async def override_get_current_user():
            return self.mock_user
            
        from app.database import get_db
        from unittest.mock import AsyncMock, MagicMock
        
        async def override_get_db():
            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_db.execute.return_value = mock_result
            
            async def mock_refresh(instance):
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc)
                if not getattr(instance, 'id', None):
                    instance.id = "mock-folder-id"
                if getattr(instance, 'is_starred', None) is None:
                    instance.is_starred = False
                if getattr(instance, 'is_trashed', None) is None:
                    instance.is_trashed = False
                if getattr(instance, 'created_at', None) is None:
                    instance.created_at = now
                if getattr(instance, 'updated_at', None) is None:
                    instance.updated_at = now

            mock_db.add = MagicMock()
            mock_db.refresh = mock_refresh
            yield mock_db
            
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_db] = override_get_db
        
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
        
    async def asyncTearDown(self):
        app.dependency_overrides.clear()
        await self.client.aclose()

    async def test_folder_creation_rate_limit(self):
        """Test POST /api/folders rate limit (100/minute) and Retry-After header"""
        headers = {"Authorization": "Bearer fake-token"}
        
        for i in range(100):
            await self.client.post("/api/folders", json={"name": f"test_{i}", "parent_path": []}, headers=headers)
            
        resp = await self.client.post("/api/folders", json={"name": "test_101", "parent_path": []}, headers=headers)
        self.assertEqual(resp.status_code, 429)

    async def test_upload_init_rate_limit(self):
        """Test POST /api/files/upload/init rate limit (20/minute) and Retry-After header"""
        headers = {"Authorization": "Bearer fake-token"}
        
        for i in range(20):
            await self.client.post("/api/files/upload/init", json={
                "filename": f"test_{i}.txt",
                "total_size": 100,
                "chunk_size": 100,
                "path": []
            }, headers=headers)
            
        resp = await self.client.post("/api/files/upload/init", json={
            "filename": "test_21.txt",
            "total_size": 100,
            "chunk_size": 100,
            "path": []
        }, headers=headers)
        self.assertEqual(resp.status_code, 429)
        self.assertIn("Retry-After", resp.headers)

if __name__ == '__main__':
    unittest.main()
