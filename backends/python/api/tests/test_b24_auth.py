"""Unit tests for B24AuthContext (stateless replacement for Bitrix24Account)."""

import unittest

import tests.conftest  # noqa: F401 — Django bootstrap

from b24pysdk.error import BitrixValidationError
from b24pysdk.bitrix_api.credentials import OAuthPlacementData

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


class B24AuthContextMarketplaceFactoryTests(unittest.TestCase):
    def test_from_raw_oauth_data_accepts_minimal_iframe_payload(self):
        ctx = B24AuthContext.from_raw_oauth_data({
            "DOMAIN": "portal.bitrix24.ru",
            "AUTH_ID": "access-token",
            "member_id": "member-1",
        })

        self.assertEqual(ctx.access_token, "access-token")
        self.assertEqual(ctx.domain_url, "portal.bitrix24.ru")
        self.assertEqual(ctx.member_id, "member-1")
        self.assertEqual(ctx.expires_in, 3600)

    def test_from_raw_oauth_data_accepts_nested_marketplace_auth_payload(self):
        ctx = B24AuthContext.from_raw_oauth_data({
            "auth": {
                "access_token": "access-token",
                "refresh_token": "refresh-token",
                "domain": "https://portal.bitrix24.ru",
                "member_id": "member-1",
                "user_id": "321",
                "expires_in": "1800",
                "scope": "im,placement",
            }
        })

        self.assertEqual(ctx.access_token, "access-token")
        self.assertEqual(ctx.refresh_token, "refresh-token")
        self.assertEqual(ctx.domain_url, "portal.bitrix24.ru")
        self.assertEqual(ctx.b24_user_id, 321)
        self.assertEqual(ctx.expires_in, 1800)
        self.assertIn("placement", ctx.current_scope)

    def test_from_oauth_placement_data_does_not_require_app_secret(self):
        raw = {
            "DOMAIN": "portal.bitrix24.ru",
            "PROTOCOL": "1",
            "LANG": "ru",
            "APP_SID": "sid",
            "AUTH_ID": "access-token",
            "AUTH_EXPIRES": "3600",
            "REFRESH_ID": "refresh-token",
            "member_id": "member-1",
            "status": "F",
            "user_id": "123",
            "appVersion": "7",
            "SCOPE": "im,imbot,entity,disk,placement,user_basic",
        }

        placement_data = OAuthPlacementData.from_dict(raw)
        ctx = B24AuthContext.from_oauth_placement_data(placement_data, raw)

        self.assertEqual(ctx.access_token, "access-token")
        self.assertEqual(ctx.refresh_token, "refresh-token")
        self.assertEqual(ctx.domain_url, "portal.bitrix24.ru")
        self.assertEqual(ctx.member_id, "member-1")
        self.assertEqual(ctx.b24_user_id, 123)
        self.assertEqual(ctx.application_version, 7)
        self.assertIn("placement", ctx.current_scope)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
