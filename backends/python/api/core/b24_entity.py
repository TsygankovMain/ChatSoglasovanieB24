from typing import Any, Iterator
import time
from urllib.parse import urlencode

import requests

# Bitrix24 returns list methods in pages of this size and caps `batch` at the same number.
PAGE_SIZE = 50
BATCH_LIMIT = 50


class B24HttpClient:
    def __init__(self, account):
        self.account = account
        self._base = f"https://{account.domain_url}/rest"

    def call(self, method: str, params: dict = None) -> Any:
        return self.call_raw(method, params).get("result", {})

    def call_raw(self, method: str, params: dict = None) -> dict:
        """Return the whole response body — list methods keep `next` and `total` beside `result`."""
        url = f"{self._base}/{method}"
        payload = dict(params or {})
        query = {"auth": self.account.access_token}
        retries = 4
        delay = 0.5
        last_error: requests.RequestException | None = None

        for attempt in range(retries):
            try:
                resp = requests.post(url, params=query, json=payload, timeout=30)
                try:
                    body = resp.json()
                except Exception:
                    resp.raise_for_status()
                    return {}

                if not isinstance(body, dict):
                    return {}

                if "error" in body:
                    raise RuntimeError(f"B24 {method}: {body.get('error_description', body['error'])}")

                resp.raise_for_status()
                return body
            except requests.RequestException as error:
                last_error = error
                if attempt < retries - 1:
                    time.sleep(delay)
                    delay *= 2
                    continue
                break

        raise RuntimeError(f"B24 {method}: network failure after {retries} attempts: {last_error}")

    def batch(self, commands: dict[str, tuple[str, dict]]) -> dict[str, Any]:
        """Run up to BATCH_LIMIT calls per HTTP request; failed commands are absent from the result."""
        results: dict[str, Any] = {}
        keys = list(commands)
        for offset in range(0, len(keys), BATCH_LIMIT):
            chunk = keys[offset:offset + BATCH_LIMIT]
            cmd = {
                key: f"{commands[key][0]}?{urlencode(_flatten_params(commands[key][1]))}"
                for key in chunk
            }
            answer = self.call("batch", {"halt": 0, "cmd": cmd})
            chunk_results = answer.get("result", {}) if isinstance(answer, dict) else {}
            if isinstance(chunk_results, dict):
                results.update(chunk_results)
        return results


def _flatten_params(params: dict, prefix: str = "") -> list[tuple[str, str]]:
    """PHP-style query pairs: {"FILTER": {"ID": 1}} -> FILTER[ID]=1."""
    pairs: list[tuple[str, str]] = []
    for key, value in params.items():
        name = f"{prefix}[{key}]" if prefix else str(key)
        if isinstance(value, dict):
            pairs.extend(_flatten_params(value, name))
        elif isinstance(value, (list, tuple)):
            pairs.extend(_flatten_params(dict(enumerate(value)), name))
        else:
            pairs.append((name, str(value)))
    return pairs


def entity_add(client: B24HttpClient, entity_name: str, access: dict = None) -> None:
    try:
        client.call("entity.add", {
            "ENTITY": entity_name,
            "NAME": entity_name,
            "ACCESS": access or {"AU": "X"},
        })
    except Exception:
        pass  # Already exists or access rights issue


def entity_item_add(client: B24HttpClient, entity_name: str, property_values: dict, name: str = "") -> str:
    safe_name = name.strip() if isinstance(name, str) else ""
    if not safe_name:
        safe_name = f"{entity_name}-{int(time.time() * 1000)}"

    result = client.call("entity.item.add", {
        "ENTITY": entity_name,
        "NAME": safe_name,
        "ACTIVE": "Y",
        "PROPERTY_VALUES": property_values,
    })
    if isinstance(result, dict):
        return str(result.get("ID", ""))
    return str(result)


def entity_item_update(client: B24HttpClient, entity_name: str, item_id: str, property_values: dict) -> None:
    client.call("entity.item.update", {
        "ENTITY": entity_name,
        "ID": item_id,
        "PROPERTY_VALUES": property_values,
    })


def _items_of(result: Any) -> list:
    if isinstance(result, dict):
        return result.get("items", [])
    if isinstance(result, list):
        return result
    return []


def entity_item_get(
    client: B24HttpClient,
    entity_name: str,
    filter: dict = None,
    sort: dict = None,
) -> list:
    """All items matching the filter, not just the first page."""
    return list(entity_item_iter(client, entity_name, filter=filter, sort=sort))


def entity_item_iter(
    client: B24HttpClient,
    entity_name: str,
    filter: dict = None,
    sort: dict = None,
    max_items: int = 0,
) -> Iterator[dict]:
    """Walk entity.item.get page by page; stops early once the caller stops consuming."""
    start = 0
    yielded = 0
    while True:
        params: dict = {"ENTITY": entity_name, "start": start}
        if filter:
            params["FILTER"] = filter
        if sort:
            params["SORT"] = sort
        body = client.call_raw("entity.item.get", params)
        for item in _items_of(body.get("result", [])):
            yield item
            yielded += 1
            if max_items and yielded >= max_items:
                return
        next_start = body.get("next")
        if not isinstance(next_start, int) or next_start <= start:
            return
        start = next_start


def entity_item_property_get(client: B24HttpClient, entity_name: str) -> list:
    result = client.call("entity.item.property.get", {"ENTITY": entity_name})
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        items = result.get("items")
        return items if isinstance(items, list) else []
    return []


def entity_item_property_add(
    client: B24HttpClient,
    entity_name: str,
    property_code: str,
    name: str,
    field_type: str = "S",
) -> None:
    client.call("entity.item.property.add", {
        "ENTITY": entity_name,
        "PROPERTY": property_code,
        "NAME": name,
        "TYPE": field_type,
    })
