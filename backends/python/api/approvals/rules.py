import json


class ApprovalRulesError(Exception):
    pass


def _get_props(item: dict) -> dict:
    return item.get("PROPERTY_VALUES", item)


def validate_can_vote(request_item: dict, user_id: str) -> None:
    props = _get_props(request_item)

    status = props.get("STATUS", "")
    if status != "collecting":
        raise ApprovalRulesError("Голосование по этому запросу уже завершено.")

    if str(user_id) == str(props.get("INITIATOR_ID", "")):
        raise ApprovalRulesError("Инициатор не может голосовать по своему запросу.")

    try:
        approver_ids = [str(a) for a in json.loads(props.get("APPROVER_IDS", "[]"))]
    except (json.JSONDecodeError, TypeError):
        approver_ids = []

    if str(user_id) not in approver_ids:
        raise ApprovalRulesError("Вы не входите в список согласующих по этому запросу.")


def compute_new_status(request_item: dict, votes: list) -> str:
    props = _get_props(request_item)
    threshold_type = props.get("THRESHOLD_TYPE", "all")

    try:
        approver_ids = json.loads(props.get("APPROVER_IDS", "[]"))
    except (json.JSONDecodeError, TypeError):
        approver_ids = []

    total_approvers = len(approver_ids)

    # Last vote per user wins
    vote_by_user: dict[str, str] = {}
    for vote in votes:
        v_props = _get_props(vote)
        uid = str(v_props.get("USER_ID", ""))
        decision = str(v_props.get("DECISION", ""))
        if uid:
            vote_by_user[uid] = decision

    approve_count = sum(1 for d in vote_by_user.values() if d == "approve")
    reject_count = sum(1 for d in vote_by_user.values() if d == "reject")

    if reject_count > 0:
        return "rejected"

    if total_approvers == 0:
        return "collecting"

    if threshold_type == "all" and approve_count >= total_approvers:
        return "approved"

    if threshold_type == "majority" and approve_count > total_approvers / 2:
        return "approved"

    return "collecting"


def is_terminal(status: str) -> bool:
    return status in ("approved", "rejected", "cancelled")
