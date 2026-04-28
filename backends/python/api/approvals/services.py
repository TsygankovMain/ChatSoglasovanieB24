from __future__ import annotations

import json
from datetime import datetime, timezone
import logging

from bot.keyboard import build_vote_keyboard, empty_keyboard
from bot.messages import build_approval_message
from disk.service import DiskService

from .b24_client import ApprovalB24Client
from . import rules

logger = logging.getLogger("approval")


def _parse_json_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return [raw]
        if isinstance(parsed, list):
            return [str(v).strip() for v in parsed if str(v).strip()]
        if parsed is None:
            return []
        parsed_str = str(parsed).strip()
        return [parsed_str] if parsed_str else []
    if value is None:
        return []
    parsed_str = str(value).strip()
    return [parsed_str] if parsed_str else []


def _parse_json_dict(value: object) -> dict[str, str]:
    if isinstance(value, dict):
        return {str(k).strip(): str(v).strip() for k, v in value.items() if str(k).strip() and str(v).strip()}
    if not isinstance(value, str):
        return {}
    raw = value.strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {str(k).strip(): str(v).strip() for k, v in parsed.items() if str(k).strip() and str(v).strip()}


def _format_request(item: dict) -> dict:
    props = item.get("PROPERTY_VALUES", {})
    try:
        approver_ids = json.loads(props.get("APPROVER_IDS", "[]"))
    except (json.JSONDecodeError, TypeError):
        approver_ids = []
    try:
        file_ids = json.loads(props.get("FILE_IDS", "[]"))
    except (json.JSONDecodeError, TypeError):
        file_ids = []
    bot_message_ids = _parse_json_list(props.get("BOT_MESSAGE_ID", ""))
    bot_message_map = _parse_json_dict(props.get("BOT_MESSAGE_MAP", ""))
    return {
        "id": str(item.get("ID", "")),
        "initiator_id": str(props.get("INITIATOR_ID", "")),
        "comment": props.get("COMMENT", ""),
        "approver_ids": [str(v) for v in approver_ids],
        "threshold_type": props.get("THRESHOLD_TYPE", ""),
        "status": props.get("STATUS", ""),
        "dialog_id": props.get("DIALOG_ID", ""),
        "bot_message_id": bot_message_ids[0] if bot_message_ids else "",
        "bot_message_ids": bot_message_ids,
        "bot_message_map": bot_message_map,
        "disk_folder_id": props.get("DISK_FOLDER_ID", ""),
        "file_ids": [str(v) for v in file_ids],
        "created_at": props.get("CREATED_AT", ""),
    }


def _format_vote(vote: dict) -> dict:
    props = vote.get("PROPERTY_VALUES", {})
    return {
        "id": str(vote.get("ID", "")),
        "user_id": str(props.get("USER_ID", "")),
        "decision": str(props.get("DECISION", "")),
        "comment": props.get("COMMENT", ""),
        "voted_at": props.get("VOTED_AT", ""),
    }


def _format_event(item: dict) -> dict:
    props = item.get("PROPERTY_VALUES", {})
    raw_meta = props.get("META", "")
    meta: dict = {}
    if isinstance(raw_meta, str) and raw_meta.strip():
        try:
            parsed = json.loads(raw_meta)
            if isinstance(parsed, dict):
                meta = parsed
        except (json.JSONDecodeError, TypeError):
            meta = {}

    return {
        "id": str(item.get("ID", "")),
        "request_id": str(props.get("REQUEST_ID", "")),
        "type": str(props.get("TYPE", "")),
        "user_id": str(props.get("USER_ID", "")),
        "decision": str(props.get("DECISION", "")),
        "status_before": str(props.get("STATUS_BEFORE", "")),
        "status_after": str(props.get("STATUS_AFTER", "")),
        "message": str(props.get("MESSAGE", "")),
        "meta": meta,
        "created_at": props.get("CREATED_AT", ""),
    }


_ENTITIES_FLAG_OPTION = "approval_entities_v1"


class ApprovalService:
    def __init__(self, account):
        self.b24 = ApprovalB24Client(account)
        self._disk = DiskService(self.b24.http)
        self._bot_id_cache: str | None = None
        # Idempotent create to avoid "Entity not found" on first calls after install.
        # Marker via app.option to skip costly per-request entity.add+property.* calls.
        try:
            initialized = self.b24.get_app_option(_ENTITIES_FLAG_OPTION) == "1"
        except Exception:
            initialized = False
        if not initialized:
            self.b24.create_entity_storages()
            try:
                self.b24.set_app_option(_ENTITIES_FLAG_OPTION, "1")
            except Exception:
                logger.warning("[service] failed to persist entities-initialized flag")

    def _get_bot_id(self) -> str:
        # Cached per-request: same value used in create/handle_vote/cancel.
        if self._bot_id_cache is None:
            self._bot_id_cache = self.b24.get_app_option("BOT_ID")
        return self._bot_id_cache

    def _dedupe_user_ids(self, user_ids: list) -> list[str]:
        cleaned = [str(user_id).strip() for user_id in user_ids if str(user_id).strip()]
        return list(dict.fromkeys(cleaned))

    def _record_event(
        self,
        request_id: str,
        event_type: str,
        *,
        user_id: str = "",
        decision: str = "",
        status_before: str = "",
        status_after: str = "",
        message: str = "",
        meta: dict | None = None,
    ) -> None:
        try:
            self.b24.add_event(
                request_id=request_id,
                event_type=event_type,
                user_id=user_id,
                decision=decision,
                status_before=status_before,
                status_after=status_after,
                message=message,
                meta=meta or {},
            )
        except Exception:
            logger.exception("[service][event] failed request_id=%s type=%s", request_id, event_type)

    def _build_user_names(self, request_data: dict, votes: list[dict], events: list[dict]) -> dict[str, str]:
        user_ids = set()
        user_ids.add(str(request_data.get("initiator_id", "")))
        user_ids.update([str(v) for v in request_data.get("approver_ids", [])])
        user_ids.update([str(v.get("user_id", "")) for v in votes])
        user_ids.update([str(e.get("user_id", "")) for e in events])
        return self.b24.get_user_names([uid for uid in user_ids if uid])

    def _compose_request_payload(self, item: dict) -> dict:
        request_data = _format_request(item)
        request_id = request_data["id"]

        votes = [_format_vote(vote) for vote in self.b24.get_votes(request_id)]
        events = [_format_event(event) for event in self.b24.get_events(request_id)]
        user_names = self._build_user_names(request_data, votes, events)

        for vote in votes:
            vote["user_name"] = user_names.get(vote["user_id"], f"Пользователь {vote['user_id']}")
        for event in events:
            uid = event["user_id"]
            event["user_name"] = user_names.get(uid, f"Пользователь {uid}") if uid else ""

        request_data["initiator_name"] = user_names.get(
            request_data["initiator_id"],
            f"Пользователь {request_data['initiator_id']}",
        )
        request_data["approver_names"] = {
            uid: user_names.get(uid, f"Пользователь {uid}")
            for uid in request_data["approver_ids"]
        }
        request_data["votes"] = votes
        request_data["events"] = events
        return request_data

    def _build_bot_message_targets(self, request_data: dict) -> tuple[list[str], dict[str, str]]:
        message_ids = list(dict.fromkeys([
            *request_data.get("bot_message_ids", []),
            *[mid for mid in request_data.get("bot_message_map", {}).values() if mid],
        ]))
        message_map = {str(uid): str(mid) for uid, mid in request_data.get("bot_message_map", {}).items() if mid}
        return message_ids, message_map

    def create(
        self,
        initiator_id: str,
        comment: str,
        approver_ids: list,
        threshold_type: str,
        dialog_id: str,
        uploaded_files: list | None = None,
    ) -> dict:
        # 1. Create disk folder and upload files (if any)
        disk_folder_id = ""
        file_ids: list[str] = []
        file_names: list[str] = []

        if uploaded_files:
            ts = int(datetime.now(timezone.utc).timestamp())
            # DiskService.create_folder already places this name inside the
            # 'Согласования' root folder — don't duplicate the prefix here.
            folder_name = f"{ts}-{initiator_id}"
            disk_folder_id = self._disk.create_folder(folder_name)

            for file_obj in uploaded_files:
                file_bytes = file_obj.read()
                result = self._disk.upload_file(disk_folder_id, file_obj.name, file_bytes)
                fid = str(result.get("ID", ""))
                if fid:
                    file_ids.append(fid)
                    file_names.append(file_obj.name)

        # Entity storages are ensured in __init__ via app.option flag — no need to recreate.

        deduped_approvers = [uid for uid in self._dedupe_user_ids(approver_ids) if uid != str(initiator_id)]
        if not deduped_approvers:
            raise RuntimeError("Инициатор не может быть единственным согласующим. Выберите другого сотрудника.")

        # 2. Save request to Entity Storage
        request_id = self.b24.create_request_item(
            initiator_id=initiator_id,
            comment=comment,
            approver_ids=deduped_approvers,
            threshold_type=threshold_type,
            dialog_id=dialog_id,
        )

        self._record_event(
            request_id,
            "created",
            user_id=str(initiator_id),
            status_after="collecting",
            message="Запрос создан",
            meta={"dialog_id": dialog_id},
        )

        if disk_folder_id or file_ids:
            self.b24.update_request_item(request_id, {
                "DISK_FOLDER_ID": disk_folder_id,
                "FILE_IDS": json.dumps(file_ids),
            })

        # 3. Publish bot messages to each approver
        bot_id = self._get_bot_id()
        bot_message_ids: list[str] = []
        bot_message_map: dict[str, str] = {}
        bot_issue = ""

        if bot_id:
            logger.info(
                "[service][create] publish start request_id=%s bot_id=%s source_dialog_id=%s recipients=%s",
                request_id,
                bot_id,
                dialog_id,
                ",".join(deduped_approvers),
            )
            user_names = self.b24.get_user_names([str(initiator_id), *deduped_approvers])
            initiator_name = user_names.get(str(initiator_id), f"Пользователь {initiator_id}")
            message_text = build_approval_message(
                request_id=request_id,
                comment=comment,
                initiator_name=initiator_name,
                file_names=file_names,
                threshold_type=threshold_type,
                votes=[],
                approver_ids=deduped_approvers,
                user_names=user_names,
                status="collecting",
                last_action_text="Запрос отправлен согласующим",
            )

            failed_details: list[str] = []
            for approver_id in deduped_approvers:
                try:
                    message_id = self.b24.publish_bot_message(
                        bot_id=bot_id,
                        dialog_id=approver_id,
                        message=message_text,
                        keyboard=build_vote_keyboard(request_id),
                    )
                    if message_id:
                        bot_message_ids.append(message_id)
                        bot_message_map[approver_id] = message_id
                        self._record_event(
                            request_id,
                            "notify_approver",
                            user_id=approver_id,
                            message="Запрос отправлен согласующему",
                            meta={"message_id": message_id},
                        )
                    else:
                        failed_details.append(f"{approver_id}: empty MESSAGE_ID")
                except Exception as exc:
                    failed_details.append(f"{approver_id}: {exc}")
                    self._record_event(
                        request_id,
                        "notify_approver_failed",
                        user_id=approver_id,
                        message="Не удалось отправить запрос согласующему",
                        meta={"error": str(exc)},
                    )
                    logger.exception(
                        "[service][create] publish failed request_id=%s bot_id=%s target_dialog_id=%s",
                        request_id,
                        bot_id,
                        approver_id,
                    )

            if bot_message_ids:
                self.b24.update_request_item(request_id, {
                    "BOT_MESSAGE_ID": json.dumps(bot_message_ids, ensure_ascii=False),
                    "BOT_MESSAGE_MAP": json.dumps(bot_message_map, ensure_ascii=False),
                })
                logger.info(
                    "[service][create] publish success request_id=%s bot_messages_count=%s",
                    request_id,
                    len(bot_message_ids),
                )

            if not deduped_approvers:
                bot_issue = "Approver recipients are empty"
            elif failed_details:
                bot_issue = "Failed recipients: " + "; ".join(failed_details)
                logger.warning("[service][create] partial publish request_id=%s issue=%s", request_id, bot_issue)
            elif not bot_message_ids:
                bot_issue = "Bot messages were not created and MESSAGE_ID values are empty"
                logger.warning("[service][create] publish empty result request_id=%s bot_id=%s", request_id, bot_id)
        else:
            bot_issue = "BOT_ID option is empty"
            logger.warning("[service][create] bot publish skipped request_id=%s: %s", request_id, bot_issue)

        return {
            "id": request_id,
            "status": "collecting",
            "bot_message_id": bot_message_ids[0] if bot_message_ids else "",
            "bot_message_ids": bot_message_ids,
            "bot_issue": bot_issue,
            "bot_dialog_id": deduped_approvers[0] if deduped_approvers else "",
            "bot_dialog_ids": deduped_approvers,
        }

    def list_requests(self, user_id: str, role: str) -> list:
        if role == "initiator":
            items = self.b24.get_requests_by_initiator(user_id)
        else:
            items = self.b24.get_requests_as_approver(user_id)
        return [self._compose_request_payload(item) for item in items]

    def get_request(self, request_id: str) -> dict | None:
        item = self.b24.get_request_by_id(request_id)
        if not item:
            return None
        return self._compose_request_payload(item)

    def _notify_initiator_vote(
        self,
        request_data: dict,
        *,
        voter_id: str,
        decision: str,
        status: str,
        user_names: dict[str, str],
        bot_id: str,
    ) -> tuple[str, str]:
        initiator_id = str(request_data.get("initiator_id", ""))
        if not initiator_id or not bot_id:
            return "", ""

        voter_name = user_names.get(voter_id, f"Пользователь {voter_id}")
        decision_text = "согласовал" if decision == "approve" else "отклонил"
        status_label = {
            "collecting": "ожидает решения",
            "approved": "одобрено",
            "rejected": "отклонено",
            "cancelled": "отменено",
        }.get(status, status)
        text = (
            f"По запросу #{request_data['id']} получен голос.\n"
            f"{voter_name} {decision_text} запрос.\n"
            f"Текущий статус: {status_label}."
        )
        message_id = self.b24.publish_bot_message(
            bot_id=bot_id,
            dialog_id=initiator_id,
            message=text,
            keyboard=empty_keyboard(),
        )
        return initiator_id, message_id

    def handle_vote(
        self,
        message_id: str,
        user_id: str,
        decision: str,
        vote_comment: str = "",
        request_id: str = "",
    ) -> dict:
        request_item = self.b24.get_request_by_id(request_id) if request_id else None
        if not request_item and message_id:
            request_item = self.b24.get_request_by_message_id(message_id)
        if not request_item:
            lookup = f"request_id={request_id}" if request_id else f"message_id={message_id}"
            raise ValueError(f"Request not found for {lookup}")

        request_data = _format_request(request_item)
        request_id = request_data["id"]
        status_before = request_data["status"]

        # Business rule: ignore votes on non-active requests
        if rules.is_terminal(status_before):
            return {"ignored": True, "request_id": request_id, "status": status_before}

        rules.validate_can_vote(request_item, user_id)

        # Upsert vote (with simple race-protection: re-check after insert)
        existing_vote = self.b24.find_vote(request_id, user_id)
        if existing_vote:
            raise rules.ApprovalRulesError("Вы уже проголосовали по этому запросу. Изменение решения недоступно.")
        new_vote_id = self.b24.add_vote(request_id, user_id, decision, vote_comment)
        # Race-protection: if a duplicate vote slipped in concurrently, keep the earliest.
        try:
            same_user_votes = [
                v for v in self.b24.get_votes(request_id)
                if str(v.get("PROPERTY_VALUES", {}).get("USER_ID", "")) == str(user_id)
            ]
            if len(same_user_votes) > 1:
                # Sort by ID ascending — keep first, drop the rest including possibly our own.
                same_user_votes.sort(key=lambda v: int(str(v.get("ID", "0")) or "0"))
                kept_id = str(same_user_votes[0].get("ID", ""))
                if str(new_vote_id) != kept_id:
                    logger.warning(
                        "[service][vote] duplicate detected request_id=%s user_id=%s kept=%s new=%s",
                        request_id, user_id, kept_id, new_vote_id,
                    )
                    raise rules.ApprovalRulesError(
                        "Голос уже был учтён. Повторная отправка отклонена."
                    )
        except rules.ApprovalRulesError:
            raise
        except Exception:
            logger.exception("[service][vote] race-check failed request_id=%s", request_id)

        all_votes_raw = self.b24.get_votes(request_id)
        new_status = rules.compute_new_status(request_item, all_votes_raw)
        self.b24.update_request_item(request_id, {"STATUS": new_status})

        self._record_event(
            request_id,
            "vote",
            user_id=str(user_id),
            decision=decision,
            status_before=status_before,
            status_after=new_status,
            message="Одобрил запрос" if decision == "approve" else "Отклонил запрос",
        )
        if new_status != status_before:
            self._record_event(
                request_id,
                "status_changed",
                user_id=str(user_id),
                decision=decision,
                status_before=status_before,
                status_after=new_status,
                message=f"Статус изменен на {new_status}",
            )

        # Update bot messages in approvers dialogs
        bot_id = self._get_bot_id()
        all_votes = [_format_vote(v) for v in all_votes_raw]
        user_names = self.b24.get_user_names([
            request_data["initiator_id"],
            *request_data["approver_ids"],
            *[vote["user_id"] for vote in all_votes],
            str(user_id),
        ])

        bot_message_ids, _ = self._build_bot_message_targets(request_data)
        if bot_id and bot_message_ids:
            voter_name = user_names.get(str(user_id), f"Пользователь {user_id}")
            decision_text = "одобрил" if decision == "approve" else "отклонил"
            message_text = build_approval_message(
                request_id=request_id,
                comment=request_data["comment"],
                initiator_name=user_names.get(
                    request_data["initiator_id"],
                    f"Пользователь {request_data['initiator_id']}",
                ),
                file_names=request_data.get("file_ids", []),
                threshold_type=request_data["threshold_type"],
                votes=all_votes_raw,
                approver_ids=request_data["approver_ids"],
                user_names=user_names,
                status=new_status,
                last_action_text=f"{voter_name} {decision_text} запрос",
            )
            _, bot_message_map = self._build_bot_message_targets(request_data)
            owner_by_message_id = {
                str(mid): str(uid)
                for uid, mid in bot_message_map.items()
                if str(mid).strip()
            }

            for bot_message_id in bot_message_ids:
                if rules.is_terminal(new_status):
                    keyboard = empty_keyboard()
                elif owner_by_message_id.get(str(bot_message_id)) == str(user_id):
                    # Lock buttons for the user who already voted.
                    keyboard = empty_keyboard()
                else:
                    keyboard = build_vote_keyboard(request_id)
                self.b24.update_bot_message(bot_id, bot_message_id, message_text, keyboard)
            logger.info(
                "[service][vote] messages updated request_id=%s bot_messages_count=%s status=%s",
                request_id,
                len(bot_message_ids),
                new_status,
            )
        else:
            logger.warning(
                "[service][vote] skip message update request_id=%s bot_id=%s bot_messages_count=%s",
                request_id,
                bot_id,
                len(bot_message_ids),
            )

        # Notify initiator on every vote
        try:
            notify_target, notify_message_id = self._notify_initiator_vote(
                request_data,
                voter_id=str(user_id),
                decision=decision,
                status=new_status,
                user_names=user_names,
                bot_id=bot_id,
            )
            if notify_target and notify_message_id:
                self._record_event(
                    request_id,
                    "notify_initiator",
                    user_id=notify_target,
                    decision=decision,
                    status_before=status_before,
                    status_after=new_status,
                    message="Инициатор уведомлен о голосе",
                    meta={"message_id": notify_message_id},
                )
        except Exception as exc:
            self._record_event(
                request_id,
                "notify_initiator_failed",
                user_id=request_data["initiator_id"],
                decision=decision,
                status_before=status_before,
                status_after=new_status,
                message="Не удалось уведомить инициатора",
                meta={"error": str(exc)},
            )
            logger.exception("[service][vote] notify initiator failed request_id=%s", request_id)

        return {"status": new_status, "request_id": request_id}

    def cancel(self, request_id: str, user_id: str) -> dict:
        item = self.b24.get_request_by_id(request_id)
        if not item:
            raise ValueError("Request not found")

        request_data = _format_request(item)
        if str(request_data["initiator_id"]) != str(user_id):
            raise PermissionError("Only the initiator can cancel a request")

        if rules.is_terminal(request_data["status"]):
            raise ValueError("Request is already in a terminal state")

        status_before = request_data["status"]
        self.b24.update_request_item(request_id, {"STATUS": "cancelled"})
        self._record_event(
            request_id,
            "cancelled",
            user_id=str(user_id),
            status_before=status_before,
            status_after="cancelled",
            message="Запрос отменен инициатором",
        )

        # Remove keyboard from bot messages
        bot_id = self._get_bot_id()
        bot_message_ids, _ = self._build_bot_message_targets(request_data)

        if bot_id and bot_message_ids:
            votes = self.b24.get_votes(request_id)
            user_names = self.b24.get_user_names([
                request_data["initiator_id"],
                *request_data["approver_ids"],
            ])
            message_text = build_approval_message(
                request_id=request_id,
                comment=request_data["comment"],
                initiator_name=user_names.get(
                    request_data["initiator_id"],
                    f"Пользователь {request_data['initiator_id']}",
                ),
                file_names=request_data.get("file_ids", []),
                threshold_type=request_data["threshold_type"],
                votes=votes,
                approver_ids=request_data["approver_ids"],
                user_names=user_names,
                status="cancelled",
                last_action_text="Запрос отменен инициатором",
            )
            for bot_message_id in bot_message_ids:
                self.b24.update_bot_message(bot_id, bot_message_id, message_text, empty_keyboard())

        return {"id": request_id, "status": "cancelled"}
