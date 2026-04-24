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


def build_approval_message(
    request_id: str,
    comment: str,
    initiator_name: str,
    file_names: list[str],
    threshold_type: str,
    votes: list,
    approver_ids: list,
    status: str = "collecting",
) -> str:
    threshold_label = _THRESHOLD_LABELS.get(threshold_type, threshold_type)
    files_text = ", ".join(file_names) if file_names else "нет"

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
    pending_text = ", ".join(f"[USER={uid}]" for uid in pending_ids) if pending_ids else "—"

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
        f"Ожидает: {pending_text}",
    ]
    return "\n".join(lines)
