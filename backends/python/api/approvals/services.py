import json
from datetime import datetime, timezone

from bot.keyboard import build_vote_keyboard, empty_keyboard
from bot.messages import build_approval_message
from disk.service import DiskService
from core.b24_entity import B24HttpClient

from .b24_client import ApprovalB24Client
from . import rules


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
    return {
        "id": str(item.get("ID", "")),
        "initiator_id": props.get("INITIATOR_ID"),
        "comment": props.get("COMMENT"),
        "approver_ids": approver_ids,
        "threshold_type": props.get("THRESHOLD_TYPE"),
        "status": props.get("STATUS"),
        "dialog_id": props.get("DIALOG_ID"),
        "bot_message_id": props.get("BOT_MESSAGE_ID"),
        "disk_folder_id": props.get("DISK_FOLDER_ID"),
        "file_ids": file_ids,
        "created_at": props.get("CREATED_AT"),
    }


def _format_vote(vote: dict) -> dict:
    props = vote.get("PROPERTY_VALUES", {})
    return {
        "id": str(vote.get("ID", "")),
        "user_id": props.get("USER_ID"),
        "decision": props.get("DECISION"),
        "comment": props.get("COMMENT", ""),
        "voted_at": props.get("VOTED_AT"),
    }


class ApprovalService:
    def __init__(self, account):
        self.b24 = ApprovalB24Client(account)
        self._disk = DiskService(self.b24.http)
        # Idempotent create to avoid "Entity not found" on first calls after install.
        self.b24.create_entity_storages()

    def _get_bot_id(self) -> str:
        return self.b24.get_app_option("BOT_ID")

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
            folder_name = f"Согласования/{ts}-{initiator_id}"
            disk_folder_id = self._disk.create_folder(folder_name)

            for file_obj in uploaded_files:
                file_bytes = file_obj.read()
                result = self._disk.upload_file(disk_folder_id, file_obj.name, file_bytes)
                fid = str(result.get("ID", ""))
                if fid:
                    file_ids.append(fid)
                    file_names.append(file_obj.name)

        # Ensure Entity storages exist even if install flow was skipped.
        self.b24.create_entity_storages()

        # 2. Save request to Entity Storage
        request_id = self.b24.create_request_item(
            initiator_id=initiator_id,
            comment=comment,
            approver_ids=approver_ids,
            threshold_type=threshold_type,
            dialog_id=dialog_id,
        )

        if disk_folder_id or file_ids:
            self.b24.update_request_item(request_id, {
                "DISK_FOLDER_ID": disk_folder_id,
                "FILE_IDS": json.dumps(file_ids),
            })

        # 3. Publish bot message
        bot_id = self._get_bot_id()
        bot_message_id = ""

        if bot_id:
            initiator_name = self.b24.get_user_name(str(initiator_id))
            message_text = build_approval_message(
                request_id=request_id,
                comment=comment,
                initiator_name=initiator_name,
                file_names=file_names,
                threshold_type=threshold_type,
                votes=[],
                approver_ids=approver_ids,
                status="collecting",
            )
            bot_message_id = self.b24.publish_bot_message(
                bot_id=bot_id,
                dialog_id=dialog_id,
                message=message_text,
                keyboard=build_vote_keyboard(),
            )
            if bot_message_id:
                self.b24.update_request_item(request_id, {"BOT_MESSAGE_ID": bot_message_id})

        return {"id": request_id, "status": "collecting", "bot_message_id": bot_message_id}

    def list_requests(self, user_id: str, role: str) -> list:
        if role == "initiator":
            items = self.b24.get_requests_by_initiator(user_id)
        else:
            items = self.b24.get_requests_as_approver(user_id)
        return [_format_request(item) for item in items]

    def get_request(self, request_id: str) -> dict | None:
        item = self.b24.get_request_by_id(request_id)
        if not item:
            return None
        votes = self.b24.get_votes(request_id)
        return {
            "request": _format_request(item),
            "votes": [_format_vote(v) for v in votes],
        }

    def handle_vote(self, message_id: str, user_id: str, decision: str, vote_comment: str = "") -> dict:
        request_item = self.b24.get_request_by_message_id(message_id)
        if not request_item:
            raise ValueError(f"Request not found for message_id={message_id}")

        request_id = str(request_item.get("ID", ""))
        props = request_item.get("PROPERTY_VALUES", {})

        # Business rule: ignore votes on non-active requests
        if rules.is_terminal(props.get("STATUS", "")):
            return {"ignored": True}

        rules.validate_can_vote(request_item, user_id)

        # Upsert vote
        existing_vote = self.b24.find_vote(request_id, user_id)
        if existing_vote:
            vote_id = str(existing_vote.get("ID", ""))
            self.b24.update_vote(vote_id, decision, vote_comment)
        else:
            self.b24.add_vote(request_id, user_id, decision, vote_comment)

        # Recalculate status
        all_votes = self.b24.get_votes(request_id)
        new_status = rules.compute_new_status(request_item, all_votes)

        self.b24.update_request_item(request_id, {"STATUS": new_status})

        # Update bot message
        bot_id = self._get_bot_id()
        bot_message_id = props.get("BOT_MESSAGE_ID", "")

        if bot_id and bot_message_id:
            try:
                approver_ids = json.loads(props.get("APPROVER_IDS", "[]"))
            except (json.JSONDecodeError, TypeError):
                approver_ids = []

            initiator_name = self.b24.get_user_name(str(props.get("INITIATOR_ID", "")))
            try:
                file_ids = json.loads(props.get("FILE_IDS", "[]"))
            except (json.JSONDecodeError, TypeError):
                file_ids = []

            message_text = build_approval_message(
                request_id=request_id,
                comment=props.get("COMMENT", ""),
                initiator_name=initiator_name,
                file_names=file_ids,  # Using IDs as placeholder names
                threshold_type=props.get("THRESHOLD_TYPE", "all"),
                votes=all_votes,
                approver_ids=approver_ids,
                status=new_status,
            )
            keyboard = empty_keyboard() if rules.is_terminal(new_status) else build_vote_keyboard()
            self.b24.update_bot_message(bot_id, bot_message_id, message_text, keyboard)

        return {"status": new_status, "request_id": request_id}

    def cancel(self, request_id: str, user_id: str) -> dict:
        item = self.b24.get_request_by_id(request_id)
        if not item:
            raise ValueError("Request not found")

        props = item.get("PROPERTY_VALUES", {})

        if str(props.get("INITIATOR_ID", "")) != str(user_id):
            raise PermissionError("Only the initiator can cancel a request")

        if rules.is_terminal(props.get("STATUS", "")):
            raise ValueError("Request is already in a terminal state")

        self.b24.update_request_item(request_id, {"STATUS": "cancelled"})

        # Remove keyboard from bot message
        bot_id = self._get_bot_id()
        bot_message_id = props.get("BOT_MESSAGE_ID", "")

        if bot_id and bot_message_id:
            try:
                approver_ids = json.loads(props.get("APPROVER_IDS", "[]"))
            except (json.JSONDecodeError, TypeError):
                approver_ids = []

            votes = self.b24.get_votes(request_id)
            initiator_name = self.b24.get_user_name(str(props.get("INITIATOR_ID", "")))
            message_text = build_approval_message(
                request_id=request_id,
                comment=props.get("COMMENT", ""),
                initiator_name=initiator_name,
                file_names=[],
                threshold_type=props.get("THRESHOLD_TYPE", "all"),
                votes=votes,
                approver_ids=approver_ids,
                status="cancelled",
            )
            self.b24.update_bot_message(bot_id, bot_message_id, message_text, empty_keyboard())

        return {"id": request_id, "status": "cancelled"}
