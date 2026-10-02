"""Unit tests for the voting rules — the part of the app users argue about."""

import json
import unittest

import tests.conftest  # noqa: F401 — Django bootstrap

from approvals import rules


def _request(approvers, threshold="all", status="collecting", initiator="1"):
    return {"PROPERTY_VALUES": {
        "INITIATOR_ID": initiator,
        "APPROVER_IDS": json.dumps([str(a) for a in approvers]),
        "THRESHOLD_TYPE": threshold,
        "STATUS": status,
    }}


def _votes(**decisions):
    return [
        {"PROPERTY_VALUES": {"USER_ID": uid.lstrip("u"), "DECISION": decision}}
        for uid, decision in decisions.items()
    ]


class UnanimousRuleTests(unittest.TestCase):
    def test_collecting_until_everyone_voted(self):
        status = rules.compute_new_status(_request([2, 3, 4]), _votes(u2="approve", u3="approve"))
        self.assertEqual(status, "collecting")

    def test_approved_when_everyone_approved(self):
        status = rules.compute_new_status(_request([2, 3]), _votes(u2="approve", u3="approve"))
        self.assertEqual(status, "approved")

    def test_single_reject_ends_the_request(self):
        status = rules.compute_new_status(_request([2, 3, 4]), _votes(u2="approve", u3="reject"))
        self.assertEqual(status, "rejected")


class MajorityRuleTests(unittest.TestCase):
    def test_approved_once_more_than_half_approved(self):
        status = rules.compute_new_status(_request([2, 3, 4], "majority"), _votes(u2="approve", u3="approve"))
        self.assertEqual(status, "approved")

    def test_single_reject_does_not_end_the_request(self):
        status = rules.compute_new_status(_request([2, 3, 4], "majority"), _votes(u2="reject"))
        self.assertEqual(status, "collecting")

    def test_reject_then_majority_still_approves(self):
        status = rules.compute_new_status(
            _request([2, 3, 4], "majority"),
            _votes(u2="reject", u3="approve", u4="approve"),
        )
        self.assertEqual(status, "approved")

    def test_rejected_when_majority_is_out_of_reach(self):
        status = rules.compute_new_status(_request([2, 3, 4], "majority"), _votes(u2="reject", u3="reject"))
        self.assertEqual(status, "rejected")

    def test_even_split_is_rejected(self):
        # 4 approvers need 3 approvals; two rejects leave only two possible.
        status = rules.compute_new_status(_request([2, 3, 4, 5], "majority"), _votes(u2="reject", u3="reject"))
        self.assertEqual(status, "rejected")

    def test_two_approvers_need_both(self):
        self.assertEqual(
            rules.compute_new_status(_request([2, 3], "majority"), _votes(u2="approve")),
            "collecting",
        )
        self.assertEqual(
            rules.compute_new_status(_request([2, 3], "majority"), _votes(u2="reject")),
            "rejected",
        )


class EdgeCaseTests(unittest.TestCase):
    def test_no_approvers_never_resolves(self):
        self.assertEqual(rules.compute_new_status(_request([]), []), "collecting")

    def test_last_vote_of_a_user_wins(self):
        votes = _votes(u2="reject") + _votes(u2="approve")
        self.assertEqual(rules.compute_new_status(_request([2]), votes), "approved")


class ValidateCanVoteTests(unittest.TestCase):
    def test_approver_may_vote(self):
        rules.validate_can_vote(_request([2, 3]), "2")

    def test_initiator_may_not_vote(self):
        with self.assertRaises(rules.ApprovalRulesError):
            rules.validate_can_vote(_request([2, 3], initiator="1"), "1")

    def test_outsider_may_not_vote(self):
        with self.assertRaises(rules.ApprovalRulesError):
            rules.validate_can_vote(_request([2, 3]), "9")

    def test_finished_request_is_closed_for_votes(self):
        with self.assertRaises(rules.ApprovalRulesError):
            rules.validate_can_vote(_request([2], status="approved"), "2")


class ValidateApproversTests(unittest.TestCase):
    def test_accepts_up_to_the_limit(self):
        rules.validate_approvers("1", [str(i) for i in range(2, 2 + rules.MAX_APPROVERS)])

    def test_rejects_more_than_the_limit(self):
        with self.assertRaises(rules.ApprovalRulesError):
            rules.validate_approvers("1", [str(i) for i in range(2, 3 + rules.MAX_APPROVERS)])

    def test_rejects_empty_list(self):
        with self.assertRaises(rules.ApprovalRulesError):
            rules.validate_approvers("1", [])

    def test_rejects_initiator_among_approvers(self):
        with self.assertRaises(rules.ApprovalRulesError):
            rules.validate_approvers("1", ["2", "1"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
