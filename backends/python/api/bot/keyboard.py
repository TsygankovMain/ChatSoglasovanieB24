import json


def build_vote_keyboard(request_id: str) -> list:
    command_params = json.dumps({"request_id": str(request_id)}, ensure_ascii=False)
    return [
        {"TEXT": "✅ Одобрить", "COMMAND": "approve", "COMMAND_PARAMS": command_params},
        {"TEXT": "❌ Отклонить", "COMMAND": "reject", "COMMAND_PARAMS": command_params},
    ]


def empty_keyboard() -> list:
    return []
