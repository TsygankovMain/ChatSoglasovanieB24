"""Stateless auth_required decorator.

Resolves the per-request B24AuthContext from either:
  1. JWT in Authorization: Bearer <token> header (frontend, after /api/get_token)
  2. OAuth placement data in request body (frontend, on first install/launch)

No database lookup. Auth context is held in-memory for the duration of the request.
"""

from functools import wraps
from http import HTTPStatus
from typing import cast

import jwt

from django.http import JsonResponse, HttpRequest

from b24pysdk.error import BitrixValidationError
from b24pysdk.utils.types import JSONDict

from ...b24_auth import B24AuthContext
from .collect_request_data import collect_request_data


def auth_required(view_func):
    @wraps(view_func)
    @collect_request_data
    def wrapped(request: HttpRequest, *args, **kwargs):
        auth = request.headers.get("Authorization")

        if isinstance(auth, str) and auth.lower().startswith("bearer "):
            jwt_token = auth[len("bearer "):]

            try:
                request.bitrix24_account = B24AuthContext.from_jwt_token(jwt_token)

            except jwt.ExpiredSignatureError:
                return JsonResponse({"error": "JWT token has expired"}, status=HTTPStatus.UNAUTHORIZED)

            except jwt.InvalidTokenError:
                return JsonResponse({"error": "Invalid JWT token"}, status=HTTPStatus.UNAUTHORIZED)

            except BitrixValidationError as error:
                return JsonResponse({"error": str(error)}, status=HTTPStatus.BAD_REQUEST)

        else:
            # First-touch flow: frontend posts raw OAuth placement data, no JWT yet.
            try:
                request.bitrix24_account = B24AuthContext.from_raw_oauth_data(
                    cast(JSONDict, request.data),
                )

            except BitrixValidationError as error:
                return JsonResponse({"error": str(error)}, status=HTTPStatus.BAD_REQUEST)

        return view_func(request, *args, **kwargs)

    return wrapped
