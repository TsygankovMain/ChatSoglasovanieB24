"""The user id in iframe and webhook payloads is a claim; only the portal's answer is trusted."""

import json
import unittest
from unittest import mock

import tests.conftest  # noqa: F401 — Django bootstrap

from b24pysdk.error import BitrixValidationError
from django.test import RequestFactory

from approvals import views as approval_views
from main import views as main_views
from main.b24_auth import B24AuthContext, IdentityError, normalize_portal_domain


def _ctx(user_id=7):
    return B24AuthContext(
        b24_user_id=user_id,
        member_id="m1",
        domain_url="portal.bitrix24.ru",
        access_token="token",
    )


def _profile(result):
    return mock.patch("core.b24_entity.B24HttpClient.call", return_value=result)


class VerifyIdentityTests(unittest.TestCase):
    def test_user_id_and_admin_flag_come_from_the_portal(self):
        ctx = _ctx(user_id=999)
        with _profile({"ID": "7", "ADMIN": True}):
            ctx.verify_identity()
        self.assertEqual(ctx.b24_user_id, 7)
        self.assertTrue(ctx.is_b24_user_admin)

    def test_non_admin_stays_non_admin(self):
        ctx = _ctx()
        with _profile({"ID": "7", "ADMIN": False}):
            ctx.verify_identity()
        self.assertFalse(ctx.is_b24_user_admin)

    def test_token_of_another_user_is_rejected(self):
        with _profile({"ID": "7"}), self.assertRaises(IdentityError):
            _ctx().verify_identity(expected_user_id="8")

    def test_matching_expected_user_passes(self):
        with _profile({"ID": "7"}):
            _ctx().verify_identity(expected_user_id="7")

    def test_portal_error_is_an_identity_error(self):
        with mock.patch("core.b24_entity.B24HttpClient.call", side_effect=RuntimeError("expired_token")):
            with self.assertRaises(IdentityError):
                _ctx().verify_identity()

    def test_empty_profile_is_rejected(self):
        with _profile({}), self.assertRaises(IdentityError):
            _ctx().verify_identity()


class PortalDomainTests(unittest.TestCase):
    def test_scheme_and_slash_are_stripped(self):
        self.assertEqual(normalize_portal_domain("https://Portal.Bitrix24.ru/"), "portal.bitrix24.ru")

    def test_box_portal_with_port_is_allowed(self):
        self.assertEqual(normalize_portal_domain("b24.example.com:8443"), "b24.example.com:8443")

    def test_internal_targets_are_rejected(self):
        for bad in ("localhost", "127.0.0.1", "10.0.0.5:80", "portal.ru/path", "user@portal.ru", "", "a b.ru"):
            with self.subTest(domain=bad), self.assertRaises(BitrixValidationError):
                normalize_portal_domain(bad)


class FirstTouchAuthTests(unittest.TestCase):
    """POST /api/getToken with raw iframe data — the only place a JWT is minted."""

    def _post(self, body):
        request = RequestFactory().post(
            "/api/getToken", data=json.dumps(body), content_type="application/json",
        )
        return main_views.get_token(request)

    def _body(self, user_id="999"):
        return {"DOMAIN": "portal.bitrix24.ru", "AUTH_ID": "token", "member_id": "m1", "user_id": user_id}

    def test_jwt_carries_the_confirmed_user_not_the_claimed_one(self):
        with _profile({"ID": "7", "ADMIN": False}):
            response = self._post(self._body(user_id="999"))
        self.assertEqual(response.status_code, 200)
        token = json.loads(response.content)["token"]
        self.assertEqual(B24AuthContext.from_jwt_token(token).b24_user_id, 7)

    def test_rejected_token_gets_no_jwt(self):
        with mock.patch("core.b24_entity.B24HttpClient.call", side_effect=RuntimeError("invalid_token")):
            response = self._post(self._body())
        self.assertEqual(response.status_code, 401)


class VoteWebhookIdentityTests(unittest.TestCase):
    def _post(self, voter_id):
        body = {
            "event": "ONIMCOMMANDADD",
            "data": {
                "COMMAND": {"1": {
                    "BOT_ID": "5", "COMMAND": "approve", "MESSAGE_ID": "100",
                    "COMMAND_PARAMS": json.dumps({"request_id": "42"}),
                }},
                "USER": {"ID": voter_id},
            },
            "auth": {"access_token": "token", "domain": "portal.bitrix24.ru", "member_id": "m1"},
        }
        request = RequestFactory().post(
            "/api/vote/handle", data=json.dumps(body), content_type="application/json",
        )
        return approval_views.vote_handle(request)

    def test_vote_on_behalf_of_another_user_is_rejected(self):
        with _profile({"ID": "7"}), mock.patch.object(approval_views, "ApprovalService") as service_cls:
            response = self._post(voter_id="8")
        self.assertEqual(response.status_code, 401)
        service_cls.assert_not_called()

    def test_own_vote_reaches_the_service(self):
        with _profile({"ID": "7"}), mock.patch.object(approval_views, "ApprovalService") as service_cls:
            service_cls.return_value.handle_vote.return_value = {"status": "approved", "request_id": "42"}
            response = self._post(voter_id="7")
        self.assertEqual(response.status_code, 200)
        service_cls.return_value.handle_vote.assert_called_once_with(
            message_id="100", user_id="7", decision="approve", request_id="42",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
