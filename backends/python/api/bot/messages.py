from __future__ import annotations

import json


_THRESHOLD_LABELS = {
    "all": "Единогласно",
    "majority": "Большинство",
}

_STATUS_LABELS = {
    "collecting": "⏳ Ожидает решения",
    "approved": "✅ Одобрено",
    "rejected": "❌ Отклонено",
    "cancelled": "🚫 Отменено",
}


def _format_files_text(files: list[dict]) -> str:
    """Render file list as Bitrix24 BBCode links.

    Each dict may have: {name, url}.  If url is present, wraps in [URL=...].
    Falls back to plain name when url is absent.
    """
    if not files:
        return "нет"
    parts = []
    for f in files:
        name = str(f.get("name", "файл")).strip() or "файл"
        url = str(f.get("url", "")).strip()
        if url:
            parts.append(f"[URL={url}]{name}[/URL]")
        else:
            parts.append(name)
    return ", ".join(parts)


def build_approval_message(
    request_id: str,
    comment: str,
    initiator_name: str,
    file_names: list[str],  # kept for backward compat — ignored when files= is given
    threshold_type: str,
    votes: list,
    approver_ids: list,
    user_names: dict[str, str] | None = None,
    status: str = "collecting",
    last_action_text: str = "",
    files: list[dict] | None = None,  # [{name, url}] — preferred over file_names
) -> str:
    user_names = user_names or {}
    threshold_label = _THRESHOLD_LABELS.get(threshold_type, threshold_type)
    if files is not None:
        files_text = _format_files_text(files)
    elif file_names:
        files_text = ", ".join(file_names)
    else:
        files_text = "нет"

    vote_by_user: dict[str, str] = {}
    for vote in votes:
        props = vote.get("PROPERTY_VALUES", vote)
        uid = str(props.get("USER_ID", ""))
        decision = str(props.get("DECISION", ""))
        if uid:
            vote_by_user[uid] = decision

    approve_count = sum(1 for d in vote_by_user.values() if d == "approve")
    reject_count = sum(1 for d in vote_by_user.values() if d == "reject")
    total = len(approver_ids)

    voted_ids = set(vote_by_user.keys())
    pending_ids = [str(a) for a in approver_ids if str(a) not in voted_ids]
    pending_text = ", ".join(user_names.get(uid, f"Пользователь {uid}") for uid in pending_ids) if pending_ids else "—"
    approved_ids = [uid for uid, decision in vote_by_user.items() if decision == "approve"]
    rejected_ids = [uid for uid, decision in vote_by_user.items() if decision == "reject"]
    approved_text = ", ".join(user_names.get(uid, f"Пользователь {uid}") for uid in approved_ids) if approved_ids else "—"
    rejected_text = ", ".join(user_names.get(uid, f"Пользователь {uid}") for uid in rejected_ids) if rejected_ids else "—"

    status_label = _STATUS_LABELS.get(status, status)

    lines = [
        f"[B]📋 Запрос на согласование #{request_id}[/B]",
        "",
        comment,
        "",
        f"👤 Инициатор: {initiator_name}",
        f"📎 Файлы: {files_text}",
        f"⚙️ Правило: {threshold_label}",
        f"📊 Статус: {status_label}",
        "",
        f"Голоса: ✓ {approve_count} / ✗ {reject_count} из {total}",
        f"✅ Одобрили: {approved_text}",
        f"❌ Отклонили: {rejected_text}",
        f"Ожидает: {pending_text}",
    ]
    if last_action_text:
        lines.extend(["", f"🕒 Последнее действие: {last_action_text}"])
    return "\n".join(lines)
