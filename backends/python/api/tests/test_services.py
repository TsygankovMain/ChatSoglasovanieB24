"""Service scenarios against an in-memory stand-in for the portal."""

import json
import unittest
from unittest import mock

import tests.conftest  # noqa: F401 — Django bootstrap

from approvals import rules, services


class FakeB24:
    """Keeps requests, votes and bot messages in memory with the client's interface."""

    def __init__(self, account=None):
        self.http = object()
        self.options = {"BOT_ID": "5", "approval_entities_v1": "1"}
        self.requests: dict[str, dict] = {}
        self.votes: list[dict] = []
        self.events: list[dict] = []
        self.messages: dict[str, dict] = {}
        self.rest_calls: list[str] = []

    # options
    def get_app_option(self, key):
        return self.options.get(key, "")

    def set_app_option(self, key, value):
        self.options[key] = value

    def create_entity_storages(self):
        self.rest_calls.append("create_entity_storages")

    # requests
    def create_request_item(self, initiator_id, comment, approver_ids, threshold_type, dialog_id):
        item_id = str(len(self.requests) + 1)
        self.requests[item_id] = {"ID": item_id, "PROPERTY_VALUES": {
            "INITIATOR_ID": str(initiator_id),
            "COMMENT": comment,
            "APPROVER_IDS": json.dumps(approver_ids),
            "THRESHOLD_TYPE": threshold_type,
            "STATUS": "collecting",
            "DIALOG_ID": dialog_id,
            "BOT_MESSAGE_ID": "",
            "BOT_MESSAGE_MAP": "{}",
            "CREATED_AT": "2026-10-02T10:00:00+00:00",
        }}
        return item_id

    def update_request_item(self, item_id, properties):
        self.requests[item_id]["PROPERTY_VALUES"].update(properties)

    def get_request_by_id(self, item_id):
        return self.requests.get(str(item_id))

    def get_request_by_message_id(self, message_id):
        return None

    def _newest_first(self):
        return sorted(self.requests.values(), key=lambda item: -int(item["ID"]))

    def get_requests_by_initiator(self, initiator_id, offset=0, limit=0):
        self.rest_calls.append("requests")
        items = [i for i in self._newest_first() if i["PROPERTY_VALUES"]["INITIATOR_ID"] == str(initiator_id)]
        return items[offset:offset + limit], len(items) > offset + limit

    def get_requests_as_approver(self, user_id, offset=0, limit=0):
        self.rest_calls.append("requests")
        items = [
            i for i in self._newest_first()
            if str(user_id) in json.loads(i["PROPERTY_VALUES"]["APPROVER_IDS"])
        ]
        return items[offset:offset + limit], len(items) > offset + limit

    # votes
    def add_vote(self, request_id, user_id, decision, comment=""):
        vote_id = str(len(self.votes) + 1)
        self.votes.append({"ID": vote_id, "PROPERTY_VALUES": {
            "REQUEST_ID": str(request_id), "USER_ID": str(user_id), "DECISION": decision, "COMMENT": comment,
        }})
        return vote_id

    def get_votes(self, request_id):
        return [v for v in self.votes if v["PROPERTY_VALUES"]["REQUEST_ID"] == str(request_id)]

    def get_votes_for_requests(self, request_ids):
        self.rest_calls.append("votes_batch")
        return {str(rid): self.get_votes(rid) for rid in request_ids}

    def find_vote(self, request_id, user_id):
        for vote in self.get_votes(request_id):
            if vote["PROPERTY_VALUES"]["USER_ID"] == str(user_id):
                return vote
        return None

    # events
    def add_event(self, **fields):
        self.events.append(fields)
        return str(len(self.events))

    def get_events(self, request_id):
        self.rest_calls.append("events")
        return []

    # bot
    def publish_bot_message(self, bot_id, dialog_id, message, keyboard):
        message_id = str(100 + len(self.messages))
        self.messages[message_id] = {"dialog_id": str(dialog_id), "text": message, "keyboard": keyboard}
        return message_id

    def update_bot_message(self, bot_id, message_id, message, keyboard=None):
        self.messages[message_id].update(text=message, keyboard=keyboard)

    def get_user_names(self, user_ids):
        self.rest_calls.append("users")
        return {str(uid): f"Имя {uid}" for uid in user_ids}


class ServiceTestCase(unittest.TestCase):
    def setUp(self):
        patches = [
            mock.patch.object(services, "ApprovalB24Client", FakeB24),
            mock.patch.object(services, "DiskService", mock.Mock()),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.service = services.ApprovalService(account=None)
        self.b24: FakeB24 = self.service.b24
        self.service._disk.get_folder_files.return_value = []

    def create(self, approvers=("2", "3"), threshold="all", initiator="1"):
        return self.service.create(
            initiator_id=initiator,
            comment="Договор",
            approver_ids=list(approvers),
            threshold_type=threshold,
            dialog_id="chat10",
        )

    def status(self, request_id):
        return self.b24.requests[request_id]["PROPERTY_VALUES"]["STATUS"]

    def messages_to(self, user_id):
        return [m for m in self.b24.messages.values() if m["dialog_id"] == str(user_id)]


class CreateTests(ServiceTestCase):
    def test_every_approver_gets_a_message_with_buttons(self):
        result = self.create(approvers=("2", "3"))
        self.assertEqual(result["status"], "collecting")
        self.assertEqual(result["bot_issue"], "")
        for approver in ("2", "3"):
            (message,) = self.messages_to(approver)
            self.assertEqual([b["COMMAND"] for b in message["keyboard"]], ["approve", "reject"])

    def test_duplicate_approvers_are_collapsed(self):
        self.create(approvers=("2", "2", "3"))
        self.assertEqual(json.loads(self.b24.requests["1"]["PROPERTY_VALUES"]["APPROVER_IDS"]), ["2", "3"])

    def test_initiator_among_approvers_is_refused_before_any_write(self):
        with self.assertRaises(rules.ApprovalRulesError):
            self.create(approvers=("1", "2"))
        self.assertEqual(self.b24.requests, {})
        self.service._disk.create_folder.assert_not_called()

    def test_too_many_approvers_are_refused(self):
        with self.assertRaises(rules.ApprovalRulesError):
            self.create(approvers=[str(i) for i in range(2, 13)])

    def test_missing_bot_is_reported(self):
        self.b24.options["BOT_ID"] = ""
        self.assertTrue(self.create()["bot_issue"])


class VoteTests(ServiceTestCase):
    def test_unanimous_request_is_approved_after_the_last_vote(self):
        request_id = self.create()["id"]
        self.service.handle_vote("", "2", "approve", request_id=request_id)
        self.assertEqual(self.status(request_id), "collecting")
        self.service.handle_vote("", "3", "approve", request_id=request_id)
        self.assertEqual(self.status(request_id), "approved")

    def test_majority_survives_one_reject(self):
        request_id = self.create(approvers=("2", "3", "4"), threshold="majority")["id"]
        self.service.handle_vote("", "2", "reject", request_id=request_id)
        self.assertEqual(self.status(request_id), "collecting")
        self.service.handle_vote("", "3", "approve", request_id=request_id)
        self.service.handle_vote("", "4", "approve", request_id=request_id)
        self.assertEqual(self.status(request_id), "approved")

    def test_second_vote_of_the_same_user_is_refused(self):
        request_id = self.create()["id"]
        self.service.handle_vote("", "2", "approve", request_id=request_id)
        with self.assertRaises(rules.ApprovalRulesError):
            self.service.handle_vote("", "2", "reject", request_id=request_id)
        self.assertEqual(len(self.b24.votes), 1)

    def test_outsider_cannot_vote(self):
        request_id = self.create()["id"]
        with self.assertRaises(rules.ApprovalRulesError):
            self.service.handle_vote("", "9", "approve", request_id=request_id)

    def test_vote_on_a_finished_request_is_ignored(self):
        request_id = self.create(approvers=("2",))["id"]
        self.service.handle_vote("", "2", "approve", request_id=request_id)
        result = self.service.handle_vote("", "2", "approve", request_id=request_id)
        self.assertTrue(result["ignored"])

    def test_buttons_disappear_for_the_voter_and_stay_for_the_rest(self):
        request_id = self.create()["id"]
        self.service.handle_vote("", "2", "approve", request_id=request_id)
        self.assertEqual(self.messages_to("2")[0]["keyboard"], [])
        self.assertEqual(len(self.messages_to("3")[0]["keyboard"]), 2)

    def test_buttons_disappear_for_everyone_when_the_request_ends(self):
        request_id = self.create()["id"]
        self.service.handle_vote("", "2", "reject", request_id=request_id)
        self.assertEqual(self.status(request_id), "rejected")
        self.assertEqual(self.messages_to("3")[0]["keyboard"], [])

    def test_initiator_is_told_about_the_vote(self):
        request_id = self.create()["id"]
        self.service.handle_vote("", "2", "approve", request_id=request_id)
        (notice,) = self.messages_to("1")
        self.assertIn("Имя 2", notice["text"])

    def test_unknown_request_is_an_error(self):
        with self.assertRaises(ValueError):
            self.service.handle_vote("", "2", "approve", request_id="404")


class CancelTests(ServiceTestCase):
    def test_initiator_cancels_and_buttons_disappear(self):
        request_id = self.create()["id"]
        self.assertEqual(self.service.cancel(request_id, "1")["status"], "cancelled")
        self.assertEqual(self.status(request_id), "cancelled")
        self.assertEqual(self.messages_to("2")[0]["keyboard"], [])

    def test_only_the_initiator_may_cancel(self):
        request_id = self.create()["id"]
        with self.assertRaises(PermissionError):
            self.service.cancel(request_id, "2")

    def test_finished_request_cannot_be_cancelled(self):
        request_id = self.create(approvers=("2",))["id"]
        self.service.handle_vote("", "2", "approve", request_id=request_id)
        with self.assertRaises(ValueError):
            self.service.cancel(request_id, "1")


class ListTests(ServiceTestCase):
    def test_page_is_built_with_a_fixed_number_of_portal_calls(self):
        for _ in range(5):
            self.create()
        self.b24.rest_calls.clear()

        items, has_more = self.service.list_requests("1", "initiator", offset=0, limit=3)

        self.assertEqual([item["id"] for item in items], ["5", "4", "3"])
        self.assertTrue(has_more)
        # One call each for requests, votes and names — not one set per request.
        self.assertEqual(self.b24.rest_calls, ["requests", "votes_batch", "users"])

    def test_last_page_has_no_more(self):
        for _ in range(5):
            self.create()
        items, has_more = self.service.list_requests("1", "initiator", offset=3, limit=3)
        self.assertEqual([item["id"] for item in items], ["2", "1"])
        self.assertFalse(has_more)

    def test_votes_and_names_are_attached(self):
        request_id = self.create()["id"]
        self.service.handle_vote("", "2", "approve", request_id=request_id)
        (item,), _ = self.service.list_requests("3", "approver", offset=0, limit=20)
        self.assertEqual(item["initiator_name"], "Имя 1")
        self.assertEqual(item["approver_names"], {"2": "Имя 2", "3": "Имя 3"})
        self.assertEqual(item["votes"][0]["user_name"], "Имя 2")

    def test_approver_sees_only_requests_addressed_to_them(self):
        self.create(approvers=("2",))
        self.create(approvers=("3",))
        items, _ = self.service.list_requests("3", "approver", offset=0, limit=20)
        self.assertEqual([item["id"] for item in items], ["2"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
