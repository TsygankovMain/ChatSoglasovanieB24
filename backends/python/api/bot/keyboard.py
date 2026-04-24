def build_vote_keyboard() -> list:
    return [
        {"TEXT": "✅ Одобрить", "COMMAND": "approve", "COMMAND_PARAMS": "{}"},
        {"TEXT": "❌ Отклонить", "COMMAND": "reject", "COMMAND_PARAMS": "{}"},
    ]


def empty_keyboard() -> list:
    return []
