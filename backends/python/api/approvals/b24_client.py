import json
from datetime import datetime, timezone

from core.b24_entity import (
    B24HttpClient,
    entity_add,
    entity_item_add,
    entity_item_get,
    entity_item_property_add,
    entity_item_property_get,
    entity_item_update,
)

ENTITY_REQUESTS = "appr_requests"
ENTITY_VOTES = "approval_votes"


class ApprovalB24Client:
    def __init__(self, account):
        self.http = B24HttpClient(account)

    def _normalize_keyboard(self, keyboard: list | None) -> list:
        buttons: list[dict] = []
        for raw_button in keyboard or []:
            if not isinstance(raw_button, dict):
                continue

            text = str(raw_button.get("TEXT", "")).strip()
            if not text:
                continue

            button: dict[str, str] = {"TEXT": text}
            command = str(raw_button.get("COMMAND", "")).strip()
            action = str(raw_button.get("ACTION", "")).strip().upper()
            action_value = str(raw_button.get("ACTION_VALUE", "")).strip()
            link = str(raw_button.get("LINK", "")).strip()

            if command:
                button["COMMAND"] = command
                command_params = raw_button.get("COMMAND_PARAMS")
                if command_params is None:
                    button["COMMAND_PARAMS"] = "{}"
                elif isinstance(command_params, str):
                    button["COMMAND_PARAMS"] = command_params
                else:
                    button["COMMAND_PARAMS"] = json.dumps(command_params, ensure_ascii=False)
            elif action and action_value:
                button["ACTION"] = action
                button["ACTION_VALUE"] = action_value
            elif link:
                button["LINK"] = link
            else:
                continue

            buttons.append(button)

        return buttons

    def _call_with_keyboard(self, method: str, base_params: dict, keyboard: list | None, *, clear: bool = False):
        if clear:
            params = dict(base_params)
            params["KEYBOARD"] = "N"
            return self.http.call(method, params)

        buttons = self._normalize_keyboard(keyboard)
        if not buttons:
            return self.http.call(method, dict(base_params))

        payload_object = dict(base_params)
        payload_object["KEYBOARD"] = {"BUTTONS": buttons}

        try:
            return self.http.call(method, payload_object)
        except RuntimeError as exc:
            if "Incorrect keyboard params" not in str(exc):
                raise
            payload_array = dict(base_params)
            payload_array["KEYBOARD"] = buttons
            try:
                return self.http.call(method, payload_array)
            except RuntimeError as retry_exc:
                dialog_id = str(base_params.get("DIALOG_ID", ""))
                raise RuntimeError(f"{retry_exc} (dialog_id={dialog_id})") from retry_exc

    # ── Entity Storage: Requests ────────────────────────────────────────────

    def create_request_item(
        self,
        initiator_id: str,
        comment: str,
        approver_ids: list,
        threshold_type: str,
        dialog_id: str,
    ) -> str:
        item_name = f"req-{int(datetime.now(timezone.utc).timestamp())}-{initiator_id}"
        return entity_item_add(self.http, ENTITY_REQUESTS, {
            "INITIATOR_ID": str(initiator_id),
            "COMMENT": comment,
            "APPROVER_IDS": json.dumps(approver_ids),
            "THRESHOLD_TYPE": threshold_type,
            "STATUS": "collecting",
            "DIALOG_ID": str(dialog_id),
            "BOT_MESSAGE_ID": "",
            "DISK_FOLDER_ID": "",
            "FILE_IDS": "[]",
            "CREATED_AT": datetime.now(timezone.utc).isoformat(),
        }, name=item_name)

    def update_request_item(self, item_id: str, properties: dict) -> None:
        entity_item_update(self.http, ENTITY_REQUESTS, item_id, properties)

    def get_request_by_id(self, item_id: str) -> dict | None:
        items = entity_item_get(self.http, ENTITY_REQUESTS, filter={"ID": item_id})
        return items[0] if items else None

    def get_request_by_message_id(self, message_id: str) -> dict | None:
        items = entity_item_get(
            self.http, ENTITY_REQUESTS,
            filter={"PROPERTY_BOT_MESSAGE_ID": str(message_id)},
        )
        return items[0] if items else None

    def get_requests_by_initiator(self, initiator_id: str) -> list:
        return entity_item_get(
            self.http, ENTITY_REQUESTS,
            filter={"PROPERTY_INITIATOR_ID": str(initiator_id)},
            sort={"ID": "DESC"},
        )

    def get_requests_as_approver(self, user_id: str) -> list:
        all_items = entity_item_get(self.http, ENTITY_REQUESTS, sort={"ID": "DESC"})
        result = []
        for item in all_items:
            props = item.get("PROPERTY_VALUES", {})
            try:
                ids = [str(a) for a in json.loads(props.get("APPROVER_IDS", "[]"))]
            except (json.JSONDecodeError, TypeError):
                ids = []
            if str(user_id) in ids:
                result.append(item)
        return result

    # ── Entity Storage: Votes ───────────────────────────────────────────────

    def add_vote(self, request_id: str, user_id: str, decision: str, comment: str = "") -> str:
        item_name = f"vote-{request_id}-{user_id}"
        return entity_item_add(self.http, ENTITY_VOTES, {
            "REQUEST_ID": str(request_id),
            "USER_ID": str(user_id),
            "DECISION": decision,
            "COMMENT": comment,
            "VOTED_AT": datetime.now(timezone.utc).isoformat(),
        }, name=item_name)

    def update_vote(self, vote_id: str, decision: str, comment: str = "") -> None:
        entity_item_update(self.http, ENTITY_VOTES, vote_id, {
            "DECISION": decision,
            "COMMENT": comment,
            "VOTED_AT": datetime.now(timezone.utc).isoformat(),
        })

    def get_votes(self, request_id: str) -> list:
        return entity_item_get(
            self.http, ENTITY_VOTES,
            filter={"PROPERTY_REQUEST_ID": str(request_id)},
        )

    def find_vote(self, request_id: str, user_id: str) -> dict | None:
        items = entity_item_get(self.http, ENTITY_VOTES, filter={
            "PROPERTY_REQUEST_ID": str(request_id),
            "PROPERTY_USER_ID": str(user_id),
        })
        return items[0] if items else None

    # ── Bot Platform 2.0 ───────────────────────────────────────────────────

    def publish_bot_message(self, bot_id: str, dialog_id: str, message: str, keyboard: list) -> str:
        result = self._call_with_keyboard("imbot.message.add", {
            "BOT_ID": bot_id,
            "DIALOG_ID": dialog_id,
            "MESSAGE": message,
        }, keyboard)
        if isinstance(result, dict):
            return str(result.get("MESSAGE_ID", result.get("id", "")))
        return str(result)

    def update_bot_message(self, bot_id: str, message_id: str, message: str, keyboard: list = None) -> None:
        params = {
            "BOT_ID": bot_id,
            "MESSAGE_ID": message_id,
            "MESSAGE": message,
        }
        if keyboard is None:
            self.http.call("imbot.message.update", params)
            return

        clear = len(keyboard) == 0
        self._call_with_keyboard("imbot.message.update", params, keyboard, clear=clear)

    # ── App Options ────────────────────────────────────────────────────────

    def get_app_option(self, key: str) -> str:
        result = self.http.call("app.option.get", {"option": key})
        if isinstance(result, dict):
            return result.get(key, "")
        return str(result) if result else ""

    def set_app_option(self, key: str, value: str) -> None:
        self.http.call("app.option.set", {"options": {key: value}})

    # ── Install helpers ────────────────────────────────────────────────────

    def register_bot(self, bot_name: str, webhook_url: str) -> str:
        result = self.http.call("imbot.register", {
            "CODE": "approval_bot",
            "TYPE": "B",
            "EVENT_MESSAGE_ADD": webhook_url,
            "EVENT_WELCOME_MESSAGE": webhook_url,
            "EVENT_BOT_DELETE": webhook_url,
            "PROPERTIES": {
                "NAME": bot_name,
                "LAST_NAME": "",
                "COLOR": "GREEN",
            },
        })
        if isinstance(result, dict):
            return str(result.get("BOT_ID", result.get("ID", "")))
        return str(result)

    def bind_placement(self, placement: str, handler_url: str, title: str = "Согласование") -> None:
        # Rebind placement to keep options in sync after app updates.
        try:
            self.http.call("placement.unbind", {
                "PLACEMENT": placement,
            })
        except Exception:
            pass

        self.http.call("placement.bind", {
            "PLACEMENT": placement,
            "HANDLER": handler_url,
            "TITLE": title,
            "OPTIONS": {
                "iconName": "Approval",
                "context": "ALL",
                "role": "USER",
                "extranet": "N",
                "color": "LIGHT_BLUE",
                "width": 400,
                "height": 300,
            },
        })

    def create_entity_storages(self) -> None:
        entity_add(self.http, ENTITY_REQUESTS)
        entity_add(self.http, ENTITY_VOTES)
        self._ensure_entity_properties(ENTITY_REQUESTS, {
            "INITIATOR_ID": ("Initiator ID", "S"),
            "COMMENT": ("Comment", "S"),
            "APPROVER_IDS": ("Approver IDs", "S"),
            "THRESHOLD_TYPE": ("Threshold Type", "S"),
            "STATUS": ("Status", "S"),
            "DIALOG_ID": ("Dialog ID", "S"),
            "BOT_MESSAGE_ID": ("Bot Message ID", "S"),
            "DISK_FOLDER_ID": ("Disk Folder ID", "S"),
            "FILE_IDS": ("File IDs", "S"),
            "CREATED_AT": ("Created At", "S"),
        })
        self._ensure_entity_properties(ENTITY_VOTES, {
            "REQUEST_ID": ("Request ID", "S"),
            "USER_ID": ("User ID", "S"),
            "DECISION": ("Decision", "S"),
            "COMMENT": ("Comment", "S"),
            "VOTED_AT": ("Voted At", "S"),
        })

    def _ensure_entity_properties(self, entity_code: str, schema: dict[str, tuple[str, str]]) -> None:
        try:
            existing = entity_item_property_get(self.http, entity_code)
        except Exception:
            existing = []

        existing_codes = {
            str(item.get("PROPERTY") or item.get("property") or "").upper()
            for item in existing if isinstance(item, dict)
        }

        for code, (name, field_type) in schema.items():
            if code.upper() in existing_codes:
                continue
            try:
                entity_item_property_add(self.http, entity_code, code, name, field_type)
            except Exception:
                # Ignore concurrent creation or access races during install/init.
                pass

    def get_user_name(self, user_id: str) -> str:
        try:
            result = self.http.call("user.get", {"ID": user_id})
            if isinstance(result, list) and result:
                u = result[0]
                return f"{u.get('NAME', '')} {u.get('LAST_NAME', '')}".strip()
        except Exception:
            pass
        return f"Пользователь {user_id}"
