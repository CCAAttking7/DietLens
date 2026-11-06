"""Small Supabase Auth boundary for the HTTP API.

The browser only sends an access token. In Supabase mode the API asks the
project Auth service to validate that token and uses the returned subject as
the only accepted user_id. Demo mode keeps the local single-user workflow
available until a project has enabled Auth.
"""
from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .errors import ToolError


class SupabaseAuthenticator:
    def __init__(self, project_url: str, publishable_key: str, *, timeout: float = 5) -> None:
        self.project_url = project_url.rstrip("/")
        self.publishable_key = publishable_key
        self.timeout = timeout

    def user_id(self, access_token: str) -> str:
        if not access_token or not self.project_url or not self.publishable_key:
            raise ToolError("authentication_required")
        request = Request(
            f"{self.project_url}/auth/v1/user",
            headers={
                "apikey": self.publishable_key,
                "Authorization": f"Bearer {access_token}",
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read())
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ToolError("authentication_required") from exc
        identity = payload.get("id") if isinstance(payload, dict) else None
        if not isinstance(identity, str) or not identity.strip():
            raise ToolError("authentication_required")
        return identity
