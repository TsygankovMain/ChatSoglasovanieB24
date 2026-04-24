from typing import Any
import time

import requests


class B24HttpClient:
    def __init__(self, account):
        self.account = account
        self._base = f"https://{account.domain_url}/rest"

    def call(self, method: str, params: dict = None) -> Any:
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

                if "error" in body:
                    raise RuntimeError(f"B24 {method}: {body.get('error_description', body['error'])}")

                resp.raise_for_status()
                return body.get("result", {})
            except requests.RequestException as error:
                last_error = error
                if attempt < retries - 1:
                    time.sleep(delay)
                    delay *= 2
                    continue
                break

        raise RuntimeError(f"B24 {method}: network failure after {retries} attempts: {last_error}")


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


def entity_item_get(
    client: B24HttpClient,
    entity_name: str,
    filter: dict = None,
    sort: dict = None,
    start: int = 0,
) -> list:
    params: dict = {"ENTITY": entity_name, "START": start}
    if filter:
        params["FILTER"] = filter
    if sort:
        params["SORT"] = sort
    result = client.call("entity.item.get", params)
    if isinstance(result, dict):
        return result.get("items", [])
    if isinstance(result, list):
        return result
    return []


def entity_item_delete(client: B24HttpClient, entity_name: str, item_id: str) -> None:
    client.call("entity.item.delete", {
        "ENTITY": entity_name,
        "ID": item_id,
    })


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
