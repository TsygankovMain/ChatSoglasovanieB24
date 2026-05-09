"""Unit tests for B24AuthContext (stateless replacement for Bitrix24Account)."""

import unittest

import tests.conftest  # noqa: F401 — Django bootstrap

from b24pysdk.error import BitrixValidationError

from main.b24_auth import B24AuthContext


class B24AuthContextJwtRoundtripTests(unittest.TestCase):
    def setUp(self):
        self.ctx = B24AuthContext(
            b24_user_id=42,
            member_id="abc123",
            domain_url="https://test.bitrix24.ru",
            access_token="atok",
            refresh_token="rtok",
            expires=1_700_000_000,
            expires_in=3600,
            status="L",
            is_b24_user_admin=True,
        )

    def test_jwt_roundtrip_preserves_identity(self):
        """A JWT-encoded context decodes back to the same OAuth payload."""
        token = self.ctx.create_jwt_token(minutes=10)
        restored = B24AuthContext.from_jwt_token(token)
        self.assertEqual(restored.b24_user_id, 42)
        self.assertEqual(restored.member_id, "abc123")
        self.assertEqual(restored.domain_url, "https://test.bitrix24.ru")
        self.assertEqual(restored.access_token, "atok")
        self.assertEqual(restored.refresh_token, "rtok")
        self.assertEqual(restored.expires, 1_700_000_000)
        self.assertTrue(restored.is_b24_user_admin)

    def test_jwt_missing_claim_raises(self):
        """Tokens missing required OAuth claims must be rejected."""
        import jwt as pyjwt
        from config import config

        # Forged token: no `tok`, `dom`, `mid`, `uid`.
        bad = pyjwt.encode({"foo": "bar"}, config.jwt_secret, algorithm=config.jwt_algorithm)
        with self.assertRaises(BitrixValidationError):
            B24AuthContext.from_jwt_token(bad)


class B24AuthContextWebhookFactoryTests(unittest.TestCase):
    def test_from_webhook_auth_happy_path(self):
        ctx = B24AuthContext.from_webhook_auth({
            "access_token": "tok",
            "domain": "https://x.bitrix24.ru",
            "member_id": "m",
            "user_id": 7,
            "expires_in": 3600,
            "application_token": "app-tok",
        })
        self.assertEqual(ctx.access_token, "tok")
        self.assertEqual(ctx.b24_user_id, 7)
        self.assertEqual(ctx.member_id, "m")
        self.assertEqual(ctx.application_token, "app-tok")

    def test_from_webhook_auth_missing_access_token_raises(self):
        with self.assertRaises(BitrixValidationError):
            B24AuthContext.from_webhook_auth({"domain": "x", "member_id": "m"})

    def test_from_webhook_auth_rejects_non_dict(self):
        with self.assertRaises(BitrixValidationError):
            B24AuthContext.from_webhook_auth(None)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
