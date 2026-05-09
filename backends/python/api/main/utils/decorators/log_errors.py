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
                return JsonResponse({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            else:
                return response
        return wrapper
    return inner
