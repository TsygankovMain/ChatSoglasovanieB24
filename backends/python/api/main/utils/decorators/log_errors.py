import logging
from functools import wraps
from http import HTTPStatus

from django.http import JsonResponse

logger = logging.getLogger(__name__)


def log_errors(message: str):
    def inner(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                response = func(*args, **kwargs)
            except Exception as exc:
                logger.exception("%s failed: %s", message, str(exc))
                # RuntimeError carries a Bitrix24 REST message the user can act on;
                # anything else is an internal fault whose text stays in the log.
                text = str(exc) if isinstance(exc, RuntimeError) else "Internal server error"
                return JsonResponse({"error": text}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            else:
                return response
        return wrapper
    return inner
