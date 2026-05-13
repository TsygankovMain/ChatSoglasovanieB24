from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
import logging
from pathlib import Path

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
ENTITY_EVENTS = "appr_events"
APPROVAL_COMMANDS = {
    "approve": {
        "title": "Согласовать",
        "params": "",
    },
    "reject": {
        "title": "Не согласовать",
        "params": "",
    },
}

logger = logging.getLogger("approval")


class ApprovalB24Client:
    def __init__(self, account):
        self.http = B24HttpClient(account)
        # Per-request cache for app.option.get — same option reads happen
        # multiple times per service call (BOT_ID, entities flag, command IDs).
        self._option_cache: dict[str, str] = {}

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
            logger.warning("[%s] keyboard object payload rejected, fallback to array payload", method)
            payload_array = dict(base_params)
            payload_array["KEYBOARD"] = buttons
            try:
                return self.http.call(method, payload_array)
            except RuntimeError as retry_exc:
                dialog_id = str(base_params.get("DIALOG_ID", ""))
                logger.error("[%s] keyboard fallback failed dialog_id=%s error=%s", method, dialog_id, str(retry_exc))
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
            "BOT_MESSAGE_MAP": "{}",
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
        if items:
            return items[0]

        # Fallback for requests where BOT_MESSAGE_ID stores JSON array of message ids.
        all_items = entity_item_get(self.http, ENTITY_REQUESTS, sort={"ID": "DESC"})
        for item in all_items:
            props = item.get("PROPERTY_VALUES", {})
            raw_value = props.get("BOT_MESSAGE_ID", "")
            ids: list[str] = []
            if isinstance(raw_value, str):
                raw_value = raw_value.strip()
                if raw_value:
                    try:
                        parsed = json.loads(raw_value)
                    except (json.JSONDecodeError, TypeError):
                        ids = [raw_value]
                    else:
                        if isinstance(parsed, list):
                            ids = [str(v).strip() for v in parsed if str(v).strip()]
                        elif parsed is not None:
                            parsed_str = str(parsed).strip()
                            if parsed_str:
                                ids = [parsed_str]
            elif isinstance(raw_value, list):
                ids = [str(v).strip() for v in raw_value if str(v).strip()]

            raw_map = props.get("BOT_MESSAGE_MAP", "")
            if isinstance(raw_map, str):
                raw_map = raw_map.strip()
                if raw_map:
                    try:
                        parsed_map = json.loads(raw_map)
                    except (json.JSONDecodeError, TypeError):
                        parsed_map = {}
                    if isinstance(parsed_map, dict):
                        ids.extend([
                            str(v).strip()
                            for v in parsed_map.values()
                            if str(v).strip()
                        ])

            if str(message_id) in ids:
                return item
        return None

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

    # ── Entity Storage: Events ──────────────────────────────────────────────

    def add_event(
        self,
        request_id: str,
        event_type: str,
        user_id: str = "",
        decision: str = "",
        status_before: str = "",
        status_after: str = "",
        message: str = "",
        meta: dict | None = None,
    ) -> str:
        item_name = f"evt-{request_id}-{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        return entity_item_add(self.http, ENTITY_EVENTS, {
            "REQUEST_ID": str(request_id),
            "TYPE": str(event_type),
            "USER_ID": str(user_id),
            "DECISION": str(decision),
            "STATUS_BEFORE": str(status_before),
            "STATUS_AFTER": str(status_after),
            "MESSAGE": str(message),
            "META": json.dumps(meta or {}, ensure_ascii=False),
            "CREATED_AT": datetime.now(timezone.utc).isoformat(),
        }, name=item_name)

    def get_events(self, request_id: str) -> list:
        return entity_item_get(
            self.http, ENTITY_EVENTS,
            filter={"PROPERTY_REQUEST_ID": str(request_id)},
            sort={"ID": "ASC"},
        )

    # ── Bot Platform 2.0 ───────────────────────────────────────────────────

    def publish_bot_message(self, bot_id: str, dialog_id: str, message: str, keyboard: list) -> str:
        logger.info(
            "[b24][imbot.message.add] bot_id=%s dialog_id=%s keyboard_buttons=%s",
            bot_id,
            dialog_id,
            len(keyboard or []),
        )
        result = self._call_with_keyboard("imbot.message.add", {
            "BOT_ID": bot_id,
            "DIALOG_ID": dialog_id,
            "MESSAGE": message,
        }, keyboard)
        message_id = ""
        if isinstance(result, dict):
            message_id = str(result.get("MESSAGE_ID", result.get("id", "")))
        else:
            message_id = str(result)
        logger.info(
            "[b24][imbot.message.add] result bot_id=%s dialog_id=%s message_id=%s",
            bot_id,
            dialog_id,
            message_id,
        )
        return message_id

    def update_bot_message(self, bot_id: str, message_id: str, message: str, keyboard: list | None = None) -> None:
        logger.info(
            "[b24][imbot.message.update] bot_id=%s message_id=%s keyboard_mode=%s",
            bot_id,
            message_id,
            "none" if keyboard is None else ("clear" if len(keyboard) == 0 else "buttons"),
        )
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

    def answer_command(self, command: str, message_id: str, message: str) -> None:
        self.http.call("imbot.command.answer", {
            "COMMAND": command,
            "MESSAGE_ID": message_id,
            "MESSAGE": message,
        })

    # ── App Options ────────────────────────────────────────────────────────

    def get_app_option(self, key: str) -> str:
        if key in self._option_cache:
            return self._option_cache[key]
        result = self.http.call("app.option.get", {"option": key})
        if isinstance(result, dict):
            value = result.get(key, "")
        else:
            value = str(result) if result else ""
        self._option_cache[key] = value
        return value

    def set_app_option(self, key: str, value: str) -> None:
        self.http.call("app.option.set", {"options": {key: value}})
        # Keep cache in sync.
        self._option_cache[key] = value

    # ── Install helpers ────────────────────────────────────────────────────

    def _load_bot_avatar_base64(self) -> str:
        """Load bot avatar from backend assets and return base64 payload."""
        avatar_path = Path(__file__).resolve().parent.parent / "assets" / "bot-avatar-200.png"
        try:
            raw = avatar_path.read_bytes()
        except OSError as exc:
            logger.warning("[b24][bot.avatar] file read failed path=%s reason=%s", avatar_path, exc)
            return ""
        return base64.b64encode(raw).decode("ascii")

    def _update_bot_avatar(self, bot_id: str, bot_name: str) -> None:
        """Set bot avatar after registration, with v2 -> legacy fallback."""
        avatar_b64 = self._load_bot_avatar_base64()
        if not avatar_b64:
            return

        try:
            numeric_bot_id = int(bot_id)
        except (TypeError, ValueError):
            logger.warning("[b24][bot.avatar] invalid bot_id=%s", bot_id)
            return

        try:
            self.http.call("imbot.v2.Bot.update", {
                "botId": numeric_bot_id,
                "fields": {
                    "properties": {
                        "name": bot_name,
                        "color": "GREEN",
                        "avatar": avatar_b64,
                    },
                },
            })
            logger.info("[b24][bot.avatar] updated via imbot.v2.Bot.update bot_id=%s", numeric_bot_id)
            return
        except Exception as exc:
            logger.warning("[b24][bot.avatar] v2 update failed bot_id=%s reason=%s", numeric_bot_id, exc)

        # Fallback for old portals where v2 methods are unavailable.
        try:
            self.http.call("imbot.update", {
                "BOT_ID": numeric_bot_id,
                "FIELDS": {
                    "PROPERTIES": {
                        "NAME": bot_name,
                        "LAST_NAME": "",
                        "COLOR": "GREEN",
                        "PERSONAL_PHOTO": ["bot-avatar-200.png", avatar_b64],
                    },
                },
            })
            logger.info("[b24][bot.avatar] updated via imbot.update bot_id=%s", numeric_bot_id)
        except Exception as exc:
            logger.warning("[b24][bot.avatar] legacy update failed bot_id=%s reason=%s", numeric_bot_id, exc)

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
        bot_id = ""
        if isinstance(result, dict):
            bot_id = str(result.get("BOT_ID", result.get("ID", "")))
        else:
            bot_id = str(result)

        if bot_id:
            self._update_bot_avatar(bot_id, bot_name)

        return bot_id

    def register_vote_command(self, bot_id: str, command: str, handler_url: str) -> str:
        command_config = APPROVAL_COMMANDS[command]
        result = self.http.call("imbot.command.register", {
            "BOT_ID": bot_id,
            "COMMAND": command,
            "EVENT_COMMAND_ADD": handler_url,
            "COMMON": "Y",
            "HIDDEN": "Y",
            "EXTRANET_SUPPORT": "N",
            "LANG": [
                {
                    "LANGUAGE_ID": "ru",
                    "TITLE": command_config["title"],
                    "PARAMS": command_config["params"],
                },
                {
                    "LANGUAGE_ID": "en",
                    "TITLE": command_config["title"],
                    "PARAMS": command_config["params"],
                },
            ],
        })
        if isinstance(result, dict):
            return str(result.get("COMMAND_ID", result.get("ID", "")))
        return str(result)

    def update_vote_command(self, command_id: str, command: str, handler_url: str) -> None:
        command_config = APPROVAL_COMMANDS[command]
        self.http.call("imbot.command.update", {
            "COMMAND_ID": command_id,
            "FIELDS": {
                "COMMAND": command,
                "EVENT_COMMAND_ADD": handler_url,
                "HIDDEN": "Y",
                "EXTRANET_SUPPORT": "N",
                "LANG": [
                    {
                        "LANGUAGE_ID": "ru",
                        "TITLE": command_config["title"],
                        "PARAMS": command_config["params"],
                    },
                    {
                        "LANGUAGE_ID": "en",
                        "TITLE": command_config["title"],
                        "PARAMS": command_config["params"],
                    },
                ],
            },
        })

    def ensure_vote_command(self, bot_id: str, command: str, handler_url: str, option_name: str) -> str:
        command_id = self.get_app_option(option_name)
        if command_id:
            try:
                self.update_vote_command(command_id, command, handler_url)
                return command_id
            except Exception:
                pass

        command_id = self.register_vote_command(bot_id, command, handler_url)
        if command_id:
            self.set_app_option(option_name, command_id)
        return command_id

    def bind_placement(
        self,
        placement: str,
        handler_url: str,
        title: str = "Согласование",
        options: dict | None = None,
    ) -> None:
        """Bind (re-bind) a placement handler.

        `options` is passed as-is to the OPTIONS field of placement.bind.
        When omitted, sensible defaults for IM_TEXTAREA are used.

        IM_CONTEXT_MENU only accepts context/role/extranet — do NOT pass
        iconName/color/width/height for that placement type.
        """
        # Rebind placement to keep options in sync after app updates.
        try:
            self.http.call("placement.unbind", {
                "PLACEMENT": placement,
            })
        except Exception as exc:
            # First-install path naturally has nothing to unbind — log at debug only.
            logger.debug("[b24][placement.unbind] skipped placement=%s reason=%s", placement, exc)

        if options is None:
            options = {
                "iconName": "fa-robot",
                "context": "ALL",
                "role": "USER",
                "extranet": "N",
                "color": "AZURE",
                "width": "400",
                "height": "300",
            }

        result = self.http.call("placement.bind", {
            "PLACEMENT": placement,
            "HANDLER": handler_url,
            "TITLE": title,
            "OPTIONS": options,
        })
        if result is False:
            raise RuntimeError(f"placement.bind returned false for {placement} — check placement type and OPTIONS")

    def create_entity_storages(self) -> None:
        entity_add(self.http, ENTITY_REQUESTS)
        entity_add(self.http, ENTITY_VOTES)
        entity_add(self.http, ENTITY_EVENTS)
        self._ensure_entity_properties(ENTITY_REQUESTS, {
            "INITIATOR_ID": ("Initiator ID", "S"),
            "COMMENT": ("Comment", "S"),
            "APPROVER_IDS": ("Approver IDs", "S"),
            "THRESHOLD_TYPE": ("Threshold Type", "S"),
            "STATUS": ("Status", "S"),
            "DIALOG_ID": ("Dialog ID", "S"),
            "BOT_MESSAGE_ID": ("Bot Message ID", "S"),
            "BOT_MESSAGE_MAP": ("Bot Message Map", "S"),
            "DISK_FOLDER_ID": ("Disk Folder ID", "S"),
            "FILE_IDS": ("File IDs", "S"),
            "FILE_NAMES": ("File Names", "S"),
            "CREATED_AT": ("Created At", "S"),
        })
        self._ensure_entity_properties(ENTITY_VOTES, {
            "REQUEST_ID": ("Request ID", "S"),
            "USER_ID": ("User ID", "S"),
            "DECISION": ("Decision", "S"),
            "COMMENT": ("Comment", "S"),
            "VOTED_AT": ("Voted At", "S"),
        })
        self._ensure_entity_properties(ENTITY_EVENTS, {
            "REQUEST_ID": ("Request ID", "S"),
            "TYPE": ("Type", "S"),
            "USER_ID": ("User ID", "S"),
            "DECISION": ("Decision", "S"),
            "STATUS_BEFORE": ("Status Before", "S"),
            "STATUS_AFTER": ("Status After", "S"),
            "MESSAGE": ("Message", "S"),
            "META": ("Meta", "S"),
            "CREATED_AT": ("Created At", "S"),
        })

    def _ensure_entity_properties(self, entity_code: str, schema: dict[str, tuple[str, str]]) -> None:
        try:
            existing = entity_item_property_get(self.http, entity_code)
        except Exception as exc:
            logger.debug("[b24][entity.item.property.get] failed entity=%s reason=%s", entity_code, exc)
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
            except Exception as exc:
                # Ignore concurrent creation or access races during install/init,
                # but surface them in logs to aid diagnosis if init silently fails.
                logger.debug(
                    "[b24][entity.item.property.add] skipped entity=%s code=%s reason=%s",
                    entity_code, code, exc,
                )

    def get_user_name(self, user_id: str) -> str:
        try:
            result = self.http.call("user.get", {"ID": user_id})
            if isinstance(result, list) and result:
                u = result[0]
                return f"{u.get('NAME', '')} {u.get('LAST_NAME', '')}".strip()
        except Exception as exc:
            logger.warning("[b24][user.get] failed user_id=%s reason=%s", user_id, exc)
        return f"Пользователь {user_id}"

    def get_user_names(self, user_ids: list[str]) -> dict[str, str]:
        """Resolve display names in a single batched API call when possible.

        Bitrix24 user.get accepts an array of IDs via FILTER[ID] — falls back to
        per-user calls only if batch resolution fails or returns nothing.
        """
        names: dict[str, str] = {}
        unique_ids = []
        seen = set()
        for raw in user_ids:
            uid = str(raw).strip()
            if not uid or uid in seen:
                continue
            seen.add(uid)
            unique_ids.append(uid)

        if not unique_ids:
            return names

        try:
            result = self.http.call("user.get", {"FILTER": {"ID": unique_ids}})
            if isinstance(result, list):
                for u in result:
                    if not isinstance(u, dict):
                        continue
                    uid = str(u.get("ID", "")).strip()
                    if not uid:
                        continue
                    full = f"{u.get('NAME', '')} {u.get('LAST_NAME', '')}".strip()
                    names[uid] = full or f"Пользователь {uid}"
        except Exception as exc:
            logger.warning("[b24][user.get batch] failed ids=%s reason=%s", unique_ids, exc)

        # Fallback for IDs missing in batch response (e.g. extranet/restricted users).
        for uid in unique_ids:
            if uid not in names:
                names[uid] = self.get_user_name(uid)
        return names
