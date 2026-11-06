import json

import pytest

from dietlens_mvp.auth import SupabaseAuthenticator
from dietlens_mvp.errors import ToolError


def test_supabase_authenticator_returns_subject(monkeypatch):
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return None
        def read(self): return json.dumps({"id": "auth-user"}).encode()

    def fake_urlopen(request, timeout):
        assert request.get_header("Authorization") == "Bearer access-token"
        assert request.get_header("Apikey") == "publishable"
        assert timeout == 5
        return Response()

    monkeypatch.setattr("dietlens_mvp.auth.urlopen", fake_urlopen)
    assert SupabaseAuthenticator("https://example.supabase.co", "publishable").user_id("access-token") == "auth-user"


def test_supabase_authenticator_rejects_missing_or_invalid_identity(monkeypatch):
    with pytest.raises(ToolError, match="authentication_required"):
        SupabaseAuthenticator("", "").user_id("")

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return None
        def read(self): return b"{}"

    monkeypatch.setattr("dietlens_mvp.auth.urlopen", lambda *args, **kwargs: Response())
    with pytest.raises(ToolError, match="authentication_required"):
        SupabaseAuthenticator("https://example.supabase.co", "publishable").user_id("bad")
