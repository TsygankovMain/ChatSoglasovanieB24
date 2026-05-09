"""Stateless replacement for Bitrix24Account ORM model.

Holds OAuth credentials and portal identity for a single request.
No database persistence — created from JWT, OAuth placement data, or webhook auth payload.
Replaces both Bitrix24Account and ApplicationInstallation models.
"""

from datetime import timedelta

import jwt

from b24pysdk import AbstractBitrixToken, BitrixApp, BitrixToken, Client
from b24pysdk.bitrix_api.credentials import OAuthPlacementData
from b24pysdk.bitrix_api.events import PortalDomainChangedEvent, OAuthTokenRenewedEvent
from b24pysdk.error import BitrixAPIError, BitrixValidationError
from b24pysdk.utils.functional import Classproperty

from django.utils import timezone

from config import config


class B24AuthContext(AbstractBitrixToken):
    """Per-request OAuth context. Lives in memory only — no DB writes."""

    def __init__(
        self,
        *,
        b24_user_id: int,
        member_id: str,
        domain_url: str,
        access_token: str,
        refresh_token: str = "",
        expires: int = 0,
        expires_in: int = 0,
        application_token: str = "",
        application_version: int = 0,
        status: str = "",
        is_b24_user_admin: bool = False,
        current_scope=None,
    ):
        super().__init__()
        self.b24_user_id = int(b24_user_id or 0)
        self.member_id = str(member_id or "")
        self.domain_url = str(domain_url or "")
        self.access_token = str(access_token or "")
        self.refresh_token = str(refresh_token or "")
        self.expires = int(expires or 0)
        self.expires_in = int(expires_in or 0)
        self.application_token = str(application_token or "")
        self.application_version = int(application_version or 0)
        self.status = str(status or "")
        self.is_b24_user_admin = bool(is_b24_user_admin)
        self.current_scope = current_scope or []

        # Connect signals — handlers do not persist anything (stateless).
        try:
            self.portal_domain_changed_signal.connect(self._on_portal_domain_changed)
            self.oauth_token_renewed_signal.connect(self._on_oauth_token_renewed)
        except Exception:
            pass

    # ===== AbstractBitrixToken interface =====

    @property
    def domain(self) -> str:
        return self.domain_url

    @domain.setter
    def domain(self, domain: str):
        self.domain_url = str(domain or "")

    @property
    def auth_token(self) -> str:
        return self.access_token

    @auth_token.setter
    def auth_token(self, value: str):
        self.access_token = str(value or "")

    @Classproperty
    def bitrix_app(cls) -> BitrixApp:  # noqa: N805
        return BitrixApp(client_id=config.client_id, client_secret=config.client_secret)

    @property
    def client(self) -> Client:
        return Client(self)

    def _on_portal_domain_changed(self, _: PortalDomainChangedEvent):
        # No persistence: new domain reflected in self.domain_url for current request only.
        return

    def _on_oauth_token_renewed(self, event: OAuthTokenRenewedEvent):
        # b24pysdk rotated the token mid-request: keep new value in memory for the rest of this request.
        # Frontend receives a fresh access_token from the iframe SDK on its next call.
        try:
            self.expires = int(event.renewed_oauth_token.oauth_token.expires.timestamp())
        except Exception:
            self.expires = int(event.renewed_oauth_token.oauth_token.expires or 0)
        self.expires_in = int(event.renewed_oauth_token.oauth_token.expires_in or 0)

    # ===== Compatibility shim (drop-in replacement for Bitrix24Account.b24_user_id, .status, etc) =====

    @property
    def pk(self):
        # Some legacy code references .pk; we don't have a UUID, so return a deterministic identifier.
        return f"{self.member_id}:{self.b24_user_id}"

    # ===== Serialization to/from JWT-friendly dict =====

    def to_payload(self) -> dict:
        # NB: do NOT use "exp" key for OAuth expiry — that's the standard JWT
        # expiration claim and would collide in create_jwt_token.
        return {
            "uid": self.b24_user_id,
            "mid": self.member_id,
            "dom": self.domain_url,
            "tok": self.access_token,
            "rfr": self.refresh_token,
            "oxp": self.expires,
            "oxpi": self.expires_in,
            "atk": self.application_token,
            "av": self.application_version,
            "st": self.status,
            "adm": self.is_b24_user_admin,
            "sc": self.current_scope,
        }

    @classmethod
    def from_payload(cls, data: dict) -> "B24AuthContext":
        return cls(
            b24_user_id=data.get("uid", 0),
            member_id=data.get("mid", ""),
            domain_url=data.get("dom", ""),
            access_token=data.get("tok", ""),
            refresh_token=data.get("rfr", ""),
            expires=data.get("oxp", 0),
            expires_in=data.get("oxpi", 0),
            application_token=data.get("atk", ""),
            application_version=data.get("av", 0),
            status=data.get("st", ""),
            is_b24_user_admin=data.get("adm", False),
            current_scope=data.get("sc") or [],
        )

    # ===== JWT (HMAC-signed; payload in claims) =====
    # Note: JWT is short-lived (60 min default) and signed with config.jwt_secret.
    # For at-rest encryption add Fernet wrapping in Sprint 4.

    def create_jwt_token(self, minutes: int = 60) -> str:
        now_dt = timezone.now()
        payload = {
            **self.to_payload(),
            "iat": now_dt,
            "exp": now_dt + timedelta(minutes=minutes),
        }
        return jwt.encode(payload, config.jwt_secret, algorithm=config.jwt_algorithm)

    @classmethod
    def from_jwt_token(cls, jwt_token: str) -> "B24AuthContext":
        payload = jwt.decode(jwt_token, config.jwt_secret, algorithms=[config.jwt_algorithm])
        # Sanity: required keys
        for key in ("uid", "mid", "dom", "tok"):
            if key not in payload:
                raise BitrixValidationError(f"Invalid JWT token: missing claim '{key}'")
        return cls.from_payload(payload)

    # ===== Factory: from OAuth placement data (frontend install/auth flow) =====

    @classmethod
    def from_oauth_placement_data(cls, oauth_placement_data: "OAuthPlacementData") -> "B24AuthContext":
        try:
            bitrix_token = BitrixToken.from_oauth_placement_data(
                oauth_placement_data, bitrix_app=cls.bitrix_app
            )
            app_info = bitrix_token.get_app_info().result
        except BitrixAPIError as error:
            raise BitrixValidationError(error.message) from error

        return cls(
            b24_user_id=app_info.user_id,
            member_id=oauth_placement_data.member_id,
            domain_url=oauth_placement_data.domain,
            access_token=oauth_placement_data.oauth_token.access_token,
            refresh_token=oauth_placement_data.oauth_token.refresh_token,
            expires=int(oauth_placement_data.oauth_token.expires.timestamp()),
            application_version=app_info.install.version,
            status=oauth_placement_data.status,
        )

    # ===== Factory: from webhook auth payload (Bitrix24 -> our backend) =====

    @classmethod
    def from_webhook_auth(cls, auth: dict) -> "B24AuthContext":
        if not isinstance(auth, dict) or not auth.get("access_token"):
            raise BitrixValidationError("Webhook auth payload missing access_token")
        return cls(
            b24_user_id=auth.get("user_id", 0) or 0,
            member_id=auth.get("member_id", ""),
            domain_url=auth.get("domain", ""),
            access_token=auth.get("access_token", ""),
            refresh_token=auth.get("refresh_token", ""),
            expires=auth.get("expires", 0) or 0,
            expires_in=auth.get("expires_in", 0) or 0,
            application_token=auth.get("application_token", ""),
            status=auth.get("status", ""),
        )
