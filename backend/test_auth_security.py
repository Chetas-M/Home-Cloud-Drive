import os
import unittest

os.environ.setdefault("SECRET_KEY", "0123456789abcdef0123456789abcdef")

from app.auth import (  # noqa: E402
    build_password_reset_fingerprint,
    create_password_reset_token,
    verify_password_reset_token,
)


class PasswordResetTokenTests(unittest.TestCase):
    def test_password_reset_token_is_bound_to_current_password_hash(self):
        token = create_password_reset_token("user-123", "hash-one")

        payload = verify_password_reset_token(token)

        self.assertEqual(payload["user_id"], "user-123")
        self.assertEqual(
            payload["password_fingerprint"],
            build_password_reset_fingerprint("hash-one"),
        )
        self.assertNotEqual(
            payload["password_fingerprint"],
            build_password_reset_fingerprint("hash-two"),
        )


if __name__ == "__main__":
    unittest.main()
