import json
from http import HTTPStatus

from django.http import JsonResponse


def validate_create_form(data: dict) -> tuple[dict | None, JsonResponse | None]:
    comment = (data.get("comment") or "").strip()
    if not comment:
        return None, JsonResponse({"error": "comment is required"}, status=HTTPStatus.BAD_REQUEST)

    raw_approvers = data.get("approver_ids", "")
    if isinstance(raw_approvers, list):
        approver_ids = raw_approvers
    elif isinstance(raw_approvers, str):
        try:
            approver_ids = json.loads(raw_approvers)
        except (json.JSONDecodeError, ValueError):
            return None, JsonResponse({"error": "approver_ids must be a JSON array"}, status=HTTPStatus.BAD_REQUEST)
    else:
        return None, JsonResponse({"error": "approver_ids is required"}, status=HTTPStatus.BAD_REQUEST)

    if not approver_ids:
        return None, JsonResponse({"error": "at least one approver is required"}, status=HTTPStatus.BAD_REQUEST)

    threshold_type = (data.get("threshold_type") or "").strip()
    if threshold_type not in ("all", "majority"):
        return None, JsonResponse(
            {"error": "threshold_type must be 'all' or 'majority'"},
            status=HTTPStatus.BAD_REQUEST,
        )

    dialog_id = (data.get("dialog_id") or "").strip()
    if not dialog_id:
        return None, JsonResponse({"error": "dialog_id is required"}, status=HTTPStatus.BAD_REQUEST)

    return {
        "comment": comment,
        "approver_ids": [str(a) for a in approver_ids],
        "threshold_type": threshold_type,
        "dialog_id": dialog_id,
    }, None


def validate_cancel_form(data: dict) -> tuple[str | None, JsonResponse | None]:
    request_id = (data.get("request_id") or "").strip()
    if not request_id:
        return None, JsonResponse({"error": "request_id is required"}, status=HTTPStatus.BAD_REQUEST)
    return request_id, None
