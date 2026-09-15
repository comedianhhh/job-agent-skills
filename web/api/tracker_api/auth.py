"""Bearer-token auth for the whole API.

One shared secret, `TRACKER_TOKEN`, checked with a constant-time compare. It is deliberately not a
user system: the tracker is single-user and the token is the thing that stops "docker compose up"
on a VPS from exposing your pipeline to the internet. When the variable is unset the API runs
open and logs a warning (local development).
"""

from __future__ import annotations

import hmac
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

log = logging.getLogger("tracker_api.auth")

PUBLIC_PATHS = {"/api/health", "/docs", "/openapi.json", "/redoc"}


def token_matches(header: str | None, expected: str) -> bool:
    if not header:
        return False
    scheme, _, value = header.partition(" ")
    if scheme.lower() != "bearer" or not value:
        return False
    return hmac.compare_digest(value.strip().encode(), expected.encode())


class BearerAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, token: str | None):
        super().__init__(app)
        self.token = token or None
        if not self.token:
            log.warning("TRACKER_TOKEN is not set — the API is running without authentication")

    async def dispatch(self, request: Request, call_next):
        if (
            self.token
            and request.method != "OPTIONS"
            and request.url.path not in PUBLIC_PATHS
            and not token_matches(request.headers.get("authorization"), self.token)
        ):
            return JSONResponse(
                {"detail": "missing or invalid bearer token"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
        return await call_next(request)
