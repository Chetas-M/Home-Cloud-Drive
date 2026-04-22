import os
import unittest

os.environ.setdefault("SECRET_KEY", "0123456789abcdef0123456789abcdef")

from app.db_utils import prefix_like_pattern  # noqa: E402
from app.routers.files import get_serialized_path_prefixes as file_path_prefixes  # noqa: E402
from app.routers.folders import get_serialized_path_prefixes as folder_path_prefixes  # noqa: E402
from app.shared_access import path_prefixes_for_shared_root  # noqa: E402


class PathPrefixEscapeTests(unittest.TestCase):
    def test_prefix_like_pattern_escapes_sql_wildcards(self):
        self.assertEqual(prefix_like_pattern('["100%_done"'), '["100\\%\\_done"%')

    def test_file_router_prefixes_escape_literal_wildcards(self):
        prefixes = file_path_prefixes(["Reports", "100%_done"])
        self.assertTrue(any("\\%" in prefix and "\\_" in prefix for prefix in prefixes))

    def test_folder_router_prefixes_escape_literal_wildcards(self):
        prefixes = folder_path_prefixes(["Reports", "100%_done"])
        self.assertTrue(any("\\%" in prefix and "\\_" in prefix for prefix in prefixes))

    def test_shared_root_prefixes_escape_literal_wildcards(self):
        shared_root = type("SharedRoot", (), {"path": '["Reports"]', "name": "100%_done"})()
        _root_path, prefixes = path_prefixes_for_shared_root(shared_root)
        self.assertTrue(any("\\%" in prefix and "\\_" in prefix for prefix in prefixes))


if __name__ == "__main__":
    unittest.main()
