"""Transport layer for the UPS REST API: OAuth tokens and request dispatch."""

import base64
import logging
from uuid import uuid4

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

TOKEN_CACHE_KEY = "ups:oauth:access_token"
TOKEN_PATH = "/security/v1/oauth/token"
REQUEST_TIMEOUT = 30

# Expire our copy ahead of UPS so a token cannot die mid-request.
TOKEN_EXPIRY_SKEW_SECONDS = 300


class UPSError(Exception):
    def __init__(self, message, status_code=None, errors=None):
        super().__init__(message)
        self.status_code = status_code
        self.errors = errors or []


class UPSNotConfigured(UPSError):
    pass


def is_sandbox() -> bool:
    return "onlinetools" not in settings.UPS_BASE_URL


def _credentials():
    client_id = settings.UPS_CLIENT_ID
    client_secret = settings.UPS_CLIENT_SECRET
    if not client_id or not client_secret:
        raise UPSNotConfigured("UPS_CLIENT_ID and UPS_CLIENT_SECRET are not set")
    # Basic auth base64-encodes these as ASCII. A stray Unicode lookalike from a
    # copy/paste fails deep inside the request, so reject it with a clear message.
    if not client_id.isascii() or not client_secret.isascii():
        raise UPSNotConfigured(
            "UPS credentials contain non-ASCII characters; re-copy them from the UPS portal"
        )
    return client_id, client_secret


def _error_text(response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text[:300]
    errors = (body.get("response") or {}).get("errors") or body.get("errors") or []
    if errors:
        return "; ".join(f"{e.get('code', '?')}: {e.get('message', '?')}" for e in errors)
    return str(body)[:300]


def get_access_token(force_refresh: bool = False) -> str:
    if not force_refresh:
        cached = cache.get(TOKEN_CACHE_KEY)
        if cached:
            return cached

    client_id, client_secret = _credentials()
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    try:
        response = requests.post(
            f"{settings.UPS_BASE_URL}{TOKEN_PATH}",
            data={"grant_type": "client_credentials"},
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {basic}",
            },
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise UPSError(f"UPS token request failed: {exc}") from exc

    if response.status_code != 200:
        raise UPSError(
            f"UPS rejected the credentials: {_error_text(response)}",
            status_code=response.status_code,
        )

    payload = response.json()
    token = payload.get("access_token")
    if not token:
        raise UPSError("UPS token response contained no access_token")

    expires_in = int(payload.get("expires_in", 14399))
    cache.set(TOKEN_CACHE_KEY, token, max(expires_in - TOKEN_EXPIRY_SKEW_SECONDS, 60))
    return token


def ups_request(method: str, path: str, json_body=None, params=None):
    """Call a UPS endpoint with a bearer token, refreshing once on a stale token."""
    url = f"{settings.UPS_BASE_URL}{path}"

    for attempt in (1, 2):
        token = get_access_token(force_refresh=attempt == 2)
        try:
            response = requests.request(
                method,
                url,
                json=json_body,
                params=params,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "transId": uuid4().hex,
                    "transactionSrc": settings.UPS_TRANSACTION_SRC,
                },
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as exc:
            raise UPSError(f"UPS request to {path} failed: {exc}") from exc

        # A cached token can be revoked server-side before it expires.
        if response.status_code == 401 and attempt == 1:
            cache.delete(TOKEN_CACHE_KEY)
            continue

        if response.status_code >= 400:
            raise UPSError(
                f"UPS {path} returned {response.status_code}: {_error_text(response)}",
                status_code=response.status_code,
            )

        try:
            return response.json()
        except ValueError as exc:
            raise UPSError(f"UPS {path} returned a non-JSON body") from exc
