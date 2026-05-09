from typing import TYPE_CHECKING

from django.http import HttpRequest

if TYPE_CHECKING:
    from ..b24_auth import B24AuthContext


class AuthorizedRequest(HttpRequest):
    bitrix24_account: "B24AuthContext"
    data: dict
