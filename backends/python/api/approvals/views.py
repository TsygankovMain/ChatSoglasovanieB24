from http import HTTPStatus
import json
import logging
import re

from django.http import JsonResponse
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from b24pysdk.error import BitrixAPIError, BitrixValidationError

from main.b24_auth import B24AuthContext
from main.utils import AuthorizedRequest
from main.utils.decorators import auth_required, log_errors
from main.utils.decorators.collect_request_data import collect_request_data

from .serializers import validate_cancel_form, validate_create_form, validate_uploaded_files
from .services import ApprovalService
from . import rules

__all__ = [
    "approval_create",
    "approval_list",
    "approval_detail",
    "approval_cancel",
    "vote_handle",
]

logger = logging.getLogger("approval")


def _get_trace_id(request) -> str:
    headers = getattr(request, "headers", None)
    if headers:
        trace_id = headers.get("X-Approval-Trace-Id", "")
        if trace_id:
            return str(trace_id)
    return str(request.META.get("HTTP_X_APPROVAL_TRACE_ID", "")).strip()


def _first_event_command(data: dict) -> dict:
    command_data = data.get("COMMAND", {})
    if not isinstance(command_data, dict):
        return {}

    for value in command_data.values():
        if isinstance(value, dict):
            return value
    return {}


def _inflate_bracket_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {}

    inflated: dict = {}

    for raw_key, value in payload.items():
        key = str(raw_key)
        if "[" not in key:
            inflated[key] = value
            continue

        parts = re.findall(r"[^\[\]]+", key)
        if not parts:
            logger.warning("Skipping malformed bracket key in webhook payload: %r", key)
            continue

        current = inflated
        for part in parts[:-1]:
            existing = current.get(part)
            if not isinstance(existing, dict):
                existing = {}
                current[part] = existing
            current = existing

        current[parts[-1]] = value

    return inflated


def _parse_command_params(raw_params) -> dict:
    if isinstance(raw_params, dict):
        return raw_params
    if not isinstance(raw_params, str) or not raw_params.strip():
        return {}
    try:
        parsed = json.loads(raw_params)
    except (json.JSONDecodeError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _extract_vote_payload(payload: dict) -> dict:
    payload = _inflate_bracket_payload(payload)

    if payload.get("event") == "ONIMCOMMANDADD":
        data = payload.get("data", {})
        data = data if isinstance(data, dict) else {}
        command_item = _first_event_command(data)
        params = data.get("PARAMS", {})
        params = params if isinstance(params, dict) else {}
        user = data.get("USER", {})
        user = user if isinstance(user, dict) else {}

        command_params = _parse_command_params(command_item.get("COMMAND_PARAMS", ""))
        if not command_params:
            command_params = _parse_command_params(params.get("COMMAND_PARAMS", ""))
        return {
            "is_event": True,
            "bot_id": str(command_item.get("BOT_ID", "")),
            "user_id": str(user.get("ID") or params.get("FROM_USER_ID") or ""),
            "message_id": str(command_item.get("MESSAGE_ID") or params.get("MESSAGE_ID") or ""),
            "command": str(command_item.get("COMMAND") or params.get("COMMAND", "")).lower(),
            "request_id": str(command_params.get("request_id", "")),
            "auth": payload.get("auth", {}) if isinstance(payload.get("auth"), dict) else {},
        }

    return {
        "is_event": False,
        "bot_id": str(payload.get("BOT_ID", "")),
        "user_id": str(payload.get("USER_ID", "")),
        "message_id": str(payload.get("MESSAGE_ID", "")),
        "command": str(payload.get("COMMAND", "")).lower(),
        "request_id": str(_parse_command_params(payload.get("COMMAND_PARAMS", "")).get("request_id", "")),
        "auth": payload.get("auth", {}) if isinstance(payload.get("auth"), dict) else {},
    }


def _resolve_account(auth: dict) -> B24AuthContext:
    """Stateless: build per-request auth context from the webhook payload itself.

    Bitrix24 sends a fresh OAuth bundle in `auth` on every imbot event
    (see ONIMCOMMANDADD spec), so we never need to look anything up.
    """
    return B24AuthContext.from_webhook_auth(auth or {})


def _answer_vote_command(service: ApprovalService, command: str, message_id: str, message: str) -> None:
    if not command or not message_id:
        return
    try:
        service.b24.answer_command(command, message_id, message)
    except Exception as exc:  # noqa: BLE001 — diagnostic best-effort
        logger.warning(
            "answer_command failed (non-fatal): command=%s message_id=%s err=%s",
            command,
            message_id,
            exc,
        )


@xframe_options_exempt
@csrf_exempt
@log_errors("approval_create")
@auth_required
def approval_create(request: AuthorizedRequest):
    if request.method not in ("POST", "OPTIONS"):
        return JsonResponse({"error": "Method not allowed"}, status=HTTPStatus.METHOD_NOT_ALLOWED)

    form, error = validate_create_form(request.data)
    if error:
        return error

    trace_id = _get_trace_id(request) or "create-no-trace"
    uploaded_files = list(request.FILES.values()) if request.FILES else None
    file_error = validate_uploaded_files(uploaded_files)
    if file_error is not None:
        return file_error
    logger.info(
        "[create][%s] start user_id=%s dialog_id=%s approvers=%s files=%s threshold=%s comment_len=%s",
        trace_id,
        str(request.bitrix24_account.b24_user_id),
        form["dialog_id"],
        len(form["approver_ids"]),
        len(uploaded_files or []),
        form["threshold_type"],
        len(form["comment"]),
    )

    service = ApprovalService(request.bitrix24_account)
    try:
        result = service.create(
            initiator_id=str(request.bitrix24_account.b24_user_id),
            comment=form["comment"],
            approver_ids=form["approver_ids"],
            threshold_type=form["threshold_type"],
            dialog_id=form["dialog_id"],
            uploaded_files=uploaded_files,
        )
        logger.info(
            "[create][%s] success request_id=%s status=%s bot_dialog_ids_count=%s bot_message_ids_count=%s bot_issue=%s",
            trace_id,
            result.get("id", ""),
            result.get("status", ""),
            len(result.get("bot_dialog_ids", []) or []),
            len(result.get("bot_message_ids", []) or []),
            result.get("bot_issue", ""),
        )
    except RuntimeError as exc:
        logger.warning("[create][%s] failed: %s", trace_id, str(exc))
        return JsonResponse({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
    return JsonResponse(result, status=HTTPStatus.CREATED)


@xframe_options_exempt
@require_GET
@log_errors("approval_list")
@auth_required
def approval_list(request: AuthorizedRequest):
    role = request.data.get("role", "initiator")
    if role not in ("initiator", "approver"):
        return JsonResponse({"error": "role must be 'initiator' or 'approver'"}, status=HTTPStatus.BAD_REQUEST)

    service = ApprovalService(request.bitrix24_account)
    items = service.list_requests(str(request.bitrix24_account.b24_user_id), role)
    return JsonResponse({"items": items})


@xframe_options_exempt
@require_GET
@log_errors("approval_detail")
@auth_required
def approval_detail(request: AuthorizedRequest, request_id: str):
    service = ApprovalService(request.bitrix24_account)
    data = service.get_request(request_id)
    if not data:
        return JsonResponse({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    # SEC-P1-2: only the initiator and the approvers may read the request.
    user_id = str(request.bitrix24_account.b24_user_id)
    is_admin = bool(getattr(request.bitrix24_account, "is_b24_user_admin", False))
    initiator_id = str(data.get("initiator_id", ""))
    approver_ids = {str(a) for a in data.get("approver_ids", [])}
    if not is_admin and user_id != initiator_id and user_id not in approver_ids:
        return JsonResponse({"error": "Forbidden"}, status=HTTPStatus.FORBIDDEN)

    return JsonResponse(data)


@xframe_options_exempt
@csrf_exempt
@require_POST
@log_errors("approval_cancel")
@auth_required
def approval_cancel(request: AuthorizedRequest):
    request_id, error = validate_cancel_form(request.data)
    if error:
        return error

    service = ApprovalService(request.bitrix24_account)
    try:
        result = service.cancel(request_id, str(request.bitrix24_account.b24_user_id))
    except PermissionError as exc:
        return JsonResponse({"error": str(exc)}, status=HTTPStatus.FORBIDDEN)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
    return JsonResponse(result)


@xframe_options_exempt
@csrf_exempt
@collect_request_data
@log_errors("vote_handle")
def vote_handle(request):
    if request.method not in ("POST",):
        return JsonResponse({"error": "Method not allowed"}, status=HTTPStatus.METHOD_NOT_ALLOWED)

    vote_payload = _extract_vote_payload(request.data)
    bot_id = vote_payload["bot_id"]
    user_id = vote_payload["user_id"]
    message_id = vote_payload["message_id"]
    command = vote_payload["command"]
    request_id = vote_payload["request_id"]
    trace_id = f"vote-{message_id or 'no-msg'}-{user_id or 'no-user'}"

    logger.info(
        "[vote][%s] incoming event=%s command=%s bot_id=%s user_id=%s message_id=%s request_id=%s domain=%s member_id=%s",
        trace_id,
        "ONIMCOMMANDADD" if vote_payload["is_event"] else "legacy",
        command,
        bot_id,
        user_id,
        message_id,
        request_id,
        vote_payload["auth"].get("domain", ""),
        vote_payload["auth"].get("member_id", ""),
    )
    if isinstance(request.data, dict):
        logger.info("[vote][%s] payload_keys=%s", trace_id, ",".join(sorted(request.data.keys())))

    if command not in ("approve", "reject"):
        logger.info("[vote][%s] ignored unknown command=%s", trace_id, command)
        return JsonResponse({"ok": True})

    if not user_id or (not message_id and not request_id):
        logger.warning("[vote][%s] missing required vote fields", trace_id)
        return JsonResponse({"ok": False, "error": "Missing required vote fields"})

    try:
        account = _resolve_account(vote_payload["auth"])
    except BitrixValidationError as exc:
        logger.warning("[vote][%s] missing auth in webhook payload: %s", trace_id, exc)
        return JsonResponse({"error": "Webhook auth payload missing"}, status=HTTPStatus.BAD_REQUEST)

    # SEC-P2-1: implicit signature check — ApprovalService.__init__ performs an
    # authenticated B24 API call. A forged webhook payload with a fake
    # access_token will fail here and we return 401 instead of processing.
    try:
        service = ApprovalService(account)
    except BitrixAPIError as exc:
        logger.warning("[vote][%s] webhook auth rejected by Bitrix24: %s", trace_id, exc)
        return JsonResponse({"error": "Webhook auth rejected by Bitrix24"}, status=HTTPStatus.UNAUTHORIZED)
    try:
        result = service.handle_vote(
            message_id=message_id,
            user_id=user_id,
            decision=command,
            request_id=request_id,
        )
    except rules.ApprovalRulesError as exc:
        logger.warning("[vote][%s] rejected by rules: %s", trace_id, str(exc))
        _answer_vote_command(service, command, message_id, str(exc))
        return JsonResponse({"ok": False, "error": str(exc)})
    except ValueError as exc:
        logger.warning("[vote][%s] invalid request: %s", trace_id, str(exc))
        _answer_vote_command(service, command, message_id, str(exc))
        return JsonResponse({"ok": False, "error": str(exc)})

    if result.get("ignored"):
        _answer_vote_command(service, command, message_id, "Запрос уже завершен.")
    else:
        decision_text = "согласовано" if command == "approve" else "не согласовано"
        _answer_vote_command(service, command, message_id, f"Ваш голос учтен: {decision_text}.")

    logger.info(
        "[vote][%s] success request_id=%s status=%s ignored=%s",
        trace_id,
        result.get("request_id", ""),
        result.get("status", ""),
        result.get("ignored", False),
    )
    return JsonResponse({"ok": True, **result})
