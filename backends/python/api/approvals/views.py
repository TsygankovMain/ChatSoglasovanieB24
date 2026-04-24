from http import HTTPStatus

from django.http import JsonResponse
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from main.utils import AuthorizedRequest
from main.utils.decorators import auth_required, log_errors
from main.utils.decorators.collect_request_data import collect_request_data

from .serializers import validate_cancel_form, validate_create_form
from .services import ApprovalService
from . import rules

__all__ = [
    "approval_create",
    "approval_list",
    "approval_detail",
    "approval_cancel",
    "vote_handle",
]


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

    uploaded_files = list(request.FILES.values()) if request.FILES else None

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
    except RuntimeError as exc:
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

    bot_id = str(request.data.get("BOT_ID", ""))
    user_id = str(request.data.get("USER_ID", ""))
    message_id = str(request.data.get("MESSAGE_ID", ""))
    command = str(request.data.get("COMMAND", "")).lower()

    if not all([bot_id, user_id, message_id, command]):
        return JsonResponse({"error": "Missing required webhook fields"}, status=HTTPStatus.BAD_REQUEST)

    if command not in ("approve", "reject"):
        return JsonResponse({"ok": True})

    # Resolve account by bot_id stored in app options
    from main.models import Bitrix24Account
    # Use most recently active account that has this bot registered
    # In production: add proper lookup; for MVP use first active account
    try:
        account = Bitrix24Account.objects.filter(
            is_master_account=True,
        ).latest("updated_at_utc")
    except Bitrix24Account.DoesNotExist:
        account = Bitrix24Account.objects.latest("updated_at_utc")

    service = ApprovalService(account)
    try:
        result = service.handle_vote(message_id, user_id, command)
    except rules.ApprovalRulesError as exc:
        return JsonResponse({"error": str(exc)}, status=HTTPStatus.FORBIDDEN)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=HTTPStatus.NOT_FOUND)

    return JsonResponse(result)
