from __future__ import annotations

import json
from http import HTTPStatus

from django.http import JsonResponse

from .rules import MAX_APPROVERS, MAX_COMMENT_LENGTH


def validate_create_form(data: dict) -> tuple[dict | None, JsonResponse | None]:
    comment = (data.get("comment") or "").strip()
    if not comment:
        return None, JsonResponse({"error": "comment is required"}, status=HTTPStatus.BAD_REQUEST)
    if len(comment) > MAX_COMMENT_LENGTH:
        return None, JsonResponse(
            {"error": f"comment is too long: max {MAX_COMMENT_LENGTH} characters"},
            status=HTTPStatus.BAD_REQUEST,
        )

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

    if not isinstance(approver_ids, list):
        return None, JsonResponse({"error": "approver_ids must be a JSON array"}, status=HTTPStatus.BAD_REQUEST)
    approver_ids = list(dict.fromkeys(str(a).strip() for a in approver_ids if str(a).strip()))
    if not approver_ids:
        return None, JsonResponse({"error": "at least one approver is required"}, status=HTTPStatus.BAD_REQUEST)
    if not all(a.isdigit() for a in approver_ids):
        return None, JsonResponse({"error": "approver_ids must contain user ids"}, status=HTTPStatus.BAD_REQUEST)
    if len(approver_ids) > MAX_APPROVERS:
        return None, JsonResponse(
            {"error": f"Too many approvers: max {MAX_APPROVERS} per request"},
            status=HTTPStatus.BAD_REQUEST,
        )

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
        "approver_ids": approver_ids,
        "threshold_type": threshold_type,
        "dialog_id": dialog_id,
    }, None


DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 50


def parse_page_params(data: dict) -> tuple[int, int]:
    """(offset, limit) from the query string; anything malformed falls back to the first page."""
    def to_int(value, fallback: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    offset = max(to_int(data.get("offset"), 0), 0)
    limit = to_int(data.get("limit"), DEFAULT_PAGE_SIZE)
    if limit <= 0:
        limit = DEFAULT_PAGE_SIZE
    return offset, min(limit, MAX_PAGE_SIZE)


def validate_cancel_form(data: dict) -> tuple[str | None, JsonResponse | None]:
    request_id = (data.get("request_id") or "").strip()
    if not request_id:
        return None, JsonResponse({"error": "request_id is required"}, status=HTTPStatus.BAD_REQUEST)
    return request_id, None


# ===== File upload validation (B24-7 / SEC-P2-2) =====

# 25 MiB per file — Bitrix24 Disk default upload limit is 50 MiB on most tariffs,
# we keep ours conservative to avoid 413s mid-upload and to limit blast radius
# from a single malicious upload.
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024
MAX_FILES_PER_REQUEST = 10

# Whitelist by extension. Keep narrow: anything we cannot preview safely
# in the chat shouldn't make it onto the portal disk via this endpoint.
ALLOWED_FILE_EXTENSIONS = {
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
    "txt", "csv", "rtf", "odt", "ods",
    "png", "jpg", "jpeg", "gif", "webp", "heic",
    "zip", "rar", "7z",
}

# Defense-in-depth: explicit deny-list of obviously dangerous extensions.
# A file matching any of these is rejected even if extracted from a content-type
# spoof.
DENIED_FILE_EXTENSIONS = {
    "exe", "bat", "cmd", "com", "msi", "scr", "ps1", "sh",
    "vbs", "js", "jse", "vbe", "wsf", "wsh",
    "dll", "so", "dylib", "jar", "apk", "ipa",
    "py", "pyc", "rb", "pl", "php", "phtml",
}


def _file_extension(name: str) -> str:
    name = (name or "").rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    if "." not in name:
        return ""
    return name.rsplit(".", 1)[-1].lower().strip()


def validate_uploaded_files(files: list | None) -> JsonResponse | None:
    """Return a JsonResponse if any uploaded file violates limits, else None."""
    if not files:
        return None
    if len(files) > MAX_FILES_PER_REQUEST:
        return JsonResponse(
            {"error": f"Too many files: max {MAX_FILES_PER_REQUEST} per request"},
            status=HTTPStatus.BAD_REQUEST,
        )
    for file_obj in files:
        size = getattr(file_obj, "size", None) or 0
        name = getattr(file_obj, "name", "") or ""
        if size <= 0:
            return JsonResponse({"error": f"Empty file: {name!r}"}, status=HTTPStatus.BAD_REQUEST)
        if size > MAX_FILE_SIZE_BYTES:
            return JsonResponse(
                {
                    "error": (
                        f"File too large: {name!r} is "
                        f"{size // (1024 * 1024)} MiB, max "
                        f"{MAX_FILE_SIZE_BYTES // (1024 * 1024)} MiB"
                    )
                },
                status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            )
        ext = _file_extension(name)
        if ext in DENIED_FILE_EXTENSIONS:
            return JsonResponse(
                {"error": f"File type not allowed: .{ext}"},
                status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            )
        if ALLOWED_FILE_EXTENSIONS and ext not in ALLOWED_FILE_EXTENSIONS:
            return JsonResponse(
                {"error": f"File type not allowed: .{ext or '<none>'}"},
                status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            )
    return None
