"""Unit tests for vote-payload parsing helpers.

These are pure helpers — no Bitrix API calls — so they're cheap to cover and
catch regressions in webhook handling, which is the most attack-surface-rich
part of the backend.
"""

import unittest

import tests.conftest  # noqa: F401 — Django bootstrap

from approvals.views import (
    _extract_vote_payload,
    _inflate_bracket_payload,
    _parse_command_params,
)


class InflateBracketPayloadTests(unittest.TestCase):
    def test_simple_keys_pass_through(self):
        out = _inflate_bracket_payload({"a": "1", "b": "2"})
        self.assertEqual(out, {"a": "1", "b": "2"})

    def test_bracket_keys_are_inflated(self):
        out = _inflate_bracket_payload({
            "data[USER][ID]": "42",
            "data[USER][NAME]": "John",
            "auth[member_id]": "m1",
        })
        self.assertEqual(out["data"]["USER"]["ID"], "42")
        self.assertEqual(out["data"]["USER"]["NAME"], "John")
        self.assertEqual(out["auth"]["member_id"], "m1")


class ExtractVotePayloadTests(unittest.TestCase):
    def test_legacy_keyboard_button_payload(self):
        result = _extract_vote_payload({
            "BOT_ID": "1",
            "USER_ID": "42",
            "MESSAGE_ID": "999",
            "COMMAND": "approve",
            "COMMAND_PARAMS": '{"request_id": "req-1"}',
            "auth": {"member_id": "m", "domain": "d"},
        })
        self.assertFalse(result["is_event"])
        self.assertEqual(result["bot_id"], "1")
        self.assertEqual(result["user_id"], "42")
        self.assertEqual(result["command"], "approve")
        self.assertEqual(result["request_id"], "req-1")

    def test_onimcommandadd_event_payload(self):
        result = _extract_vote_payload({
            "event": "ONIMCOMMANDADD",
            "data": {
                "COMMAND": {
                    "0": {
                        "BOT_ID": "11",
                        "MESSAGE_ID": "555",
                        "COMMAND": "REJECT",
                        "COMMAND_PARAMS": '{"request_id": "req-2"}',
                    }
                },
                "USER": {"ID": "77"},
            },
            "auth": {"member_id": "m", "domain": "d"},
        })
        self.assertTrue(result["is_event"])
        self.assertEqual(result["bot_id"], "11")
        self.assertEqual(result["user_id"], "77")
        self.assertEqual(result["command"], "reject")
        self.assertEqual(result["request_id"], "req-2")

    def test_command_params_invalid_json_yields_empty_dict(self):
        self.assertEqual(_parse_command_params("not-json"), {})
        self.assertEqual(_parse_command_params(""), {})
        self.assertEqual(_parse_command_params(None), {})


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
