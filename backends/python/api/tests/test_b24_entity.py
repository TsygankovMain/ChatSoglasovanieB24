"""Paging and batching over Bitrix24 REST — the layer that used to stop at the first 50 items."""

import unittest

import tests.conftest  # noqa: F401 — Django bootstrap

from core.b24_entity import B24HttpClient, _flatten_params, entity_item_get, entity_item_iter


class _PagedClient:
    """Serves `total` items in pages of 50 the way entity.item.get does."""

    def __init__(self, total, honour_start=True):
        self.total = total
        self.honour_start = honour_start
        self.calls = []

    def call_raw(self, method, params=None):
        start = params.get("start", 0) if self.honour_start else 0
        self.calls.append(start)
        items = [{"ID": str(i)} for i in range(start, min(start + 50, self.total))]
        body = {"result": items, "total": self.total}
        if start + 50 < self.total:
            body["next"] = start + 50
        return body


class EntityPagingTests(unittest.TestCase):
    def test_reads_every_page(self):
        client = _PagedClient(120)
        items = entity_item_get(client, "appr_requests")
        self.assertEqual(len(items), 120)
        self.assertEqual(client.calls, [0, 50, 100])

    def test_single_page_makes_one_call(self):
        client = _PagedClient(7)
        self.assertEqual(len(entity_item_get(client, "appr_requests")), 7)
        self.assertEqual(client.calls, [0])

    def test_max_items_stops_paging_early(self):
        client = _PagedClient(500)
        items = list(entity_item_iter(client, "appr_requests", max_items=60))
        self.assertEqual(len(items), 60)
        self.assertEqual(client.calls, [0, 50])

    def test_portal_ignoring_start_does_not_loop_forever(self):
        client = _PagedClient(120, honour_start=False)
        items = entity_item_get(client, "appr_requests")
        self.assertEqual(len(items), 100)
        self.assertEqual(len(client.calls), 2)

    def test_dict_shaped_result_is_supported(self):
        class Client:
            def call_raw(self, method, params=None):
                return {"result": {"items": [{"ID": "1"}]}}

        self.assertEqual(entity_item_get(Client(), "appr_requests"), [{"ID": "1"}])


class BatchTests(unittest.TestCase):
    def test_nested_params_are_flattened_php_style(self):
        pairs = _flatten_params({"ENTITY": "approval_votes", "FILTER": {"PROPERTY_REQUEST_ID": "12"}})
        self.assertEqual(pairs, [("ENTITY", "approval_votes"), ("FILTER[PROPERTY_REQUEST_ID]", "12")])

    def test_lists_are_indexed(self):
        self.assertEqual(_flatten_params({"ID": [5, 6]}), [("ID[0]", "5"), ("ID[1]", "6")])

    def test_commands_are_split_into_chunks_of_fifty(self):
        class Account:
            domain_url = "portal.bitrix24.ru"
            access_token = "token"

        client = B24HttpClient(Account())
        sent = []

        def fake_call(method, params=None):
            sent.append(params["cmd"])
            return {"result": {key: [key] for key in params["cmd"]}}

        client.call = fake_call
        results = client.batch({str(i): ("entity.item.get", {"ENTITY": "e"}) for i in range(120)})
        self.assertEqual([len(chunk) for chunk in sent], [50, 50, 20])
        self.assertEqual(len(results), 120)
        self.assertEqual(sent[0]["0"], "entity.item.get?ENTITY=e")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
