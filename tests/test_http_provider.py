import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.error import URLError

import pytest

from dietlens_mvp import DietLensAgent, Harness, SQLiteStore
from dietlens_mvp.config import Settings
from dietlens_mvp.errors import ToolError
from dietlens_mvp.http_provider import OpenAICompatibleProvider
from dietlens_mvp.model_provider import INTENT_SCHEMA, parse_intent
from dietlens_mvp.models import Execution, TaskState


INTENT = {"intent": "micro_action", "entities": {"meal": "午餐", "options": ["米饭", "面条"]},
          "missing_fields": [], "candidate_tool": "", "user_message": "已提取午餐和两个选项，请核对。", "confidence": 0.9}


@pytest.fixture
def server():
    class Handler(BaseHTTPRequestHandler):
        requests = []
        status = 200
        payload = {"choices": [{"message": {"content": json.dumps(INTENT)}, "finish_reason": "stop"}],
                   "usage": {"prompt_tokens": 40, "completion_tokens": 20}}
        def do_POST(self):
            type(self).requests.append({"path": self.path, "auth": self.headers.get("Authorization"),
                                       "body": json.loads(self.rfile.read(int(self.headers["Content-Length"])))})
            self.send_response(type(self).status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Location", "http://127.0.0.1:1/stolen")
            self.end_headers()
            self.wfile.write(json.dumps(type(self).payload).encode())
        def log_message(self, *args):
            pass
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{srv.server_port}/v1", Handler
    srv.shutdown()
    srv.server_close()
    thread.join()


def provider(url, **kwargs):
    return OpenAICompatibleProvider(api_key="test-only-secret", base_url=url, model="test-model", **kwargs)


def test_compatible_transport_sends_schema_and_records_usage(server):
    url, handler = server
    response = provider(url).complete([{"role": "user", "content": "午餐可选米饭或面条"}], [], INTENT_SCHEMA)
    assert parse_intent(response) == INTENT
    assert (response.input_tokens, response.output_tokens) == (40, 20)
    request = handler.requests[0]
    assert request["path"] == "/v1/chat/completions"
    assert request["auth"] == "Bearer test-only-secret"
    assert request["body"]["response_format"] == {"type": "json_object"}
    assert "test-only-secret" not in json.dumps(request["body"])
    assert "tools" not in request["body"]


@pytest.mark.parametrize("status,code", [(401,"model_authentication_failed"), (403,"model_access_denied"),
                                        (429,"model_rate_limited"), (503,"model_http_failed"), (307,"model_http_failed")])
def test_error_is_sanitized_without_redirect_or_retry(server, status, code):
    url, handler = server
    handler.status = status
    handler.payload = {"error": "test-only-secret"}
    with pytest.raises(ToolError) as caught:
        provider(url).complete([], [], INTENT_SCHEMA)
    assert caught.value.code == code
    assert "test-only-secret" not in str(caught.value)
    assert len(handler.requests) == 1


def test_json_mode_can_be_omitted_for_compatible_platform(server):
    url, handler = server
    provider(url, json_mode=False).complete([], [], INTENT_SCHEMA)
    assert "response_format" not in handler.requests[0]["body"]


def test_unknown_usage_stays_unknown(server):
    url, handler = server
    handler.payload.pop("usage")
    response = provider(url).complete([], [], INTENT_SCHEMA)
    assert response.input_tokens is None and response.output_tokens is None


def test_truncation_is_not_accepted(server):
    url, handler = server
    handler.payload["choices"][0]["finish_reason"] = "length"
    with pytest.raises(ToolError, match="model_response_incomplete"):
        provider(url).complete([], [], INTENT_SCHEMA)


@pytest.mark.parametrize("url", ["http://example.com/v1", "https://user:pass@example.com/v1", "https://example.com/v1?key=oops"])
def test_invalid_endpoint_fails_before_request(url):
    with pytest.raises(ToolError, match="invalid_model_base_url"):
        provider(url)


def test_settings_does_not_repr_secret_and_env_overrides_file(tmp_path, monkeypatch):
    path = tmp_path / ".env"
    path.write_text("DIETLENS_API_KEY=file-secret\nDIETLENS_MODEL=test-model\n")
    monkeypatch.setenv("DIETLENS_API_KEY", "shell-secret")
    # Track dotenv's environment mutation so the fixture cannot affect later tests.
    monkeypatch.setenv("DIETLENS_MODEL", "env-model")
    settings = Settings.from_env(str(path))
    assert settings.api_key == "shell-secret"
    assert settings.model_name == "env-model"
    assert "shell-secret" not in repr(settings)


@pytest.mark.parametrize("intent_name", ["micro_action", "menu_recommendation"])
def test_model_cli_loop_requires_context_confirmation_and_survives_restart(server, tmp_path, intent_name):
    from cli import collect_model_context, continue_task
    url, handler = server
    handler.payload["choices"][0]["message"]["content"] = json.dumps({**INTENT, "intent": intent_name})
    path = str(tmp_path / "loop.db")
    store = SQLiteStore(path)
    agent = DietLensAgent(Harness(store, provider(url)))
    agent.onboard("test-user", budget=20, allergies=[], consents={"review_history": True})
    task = agent.harness.create_task("test-user")
    assert task.state == TaskState.CREATED
    answers = iter(["午餐可选米饭或面条", "y"])
    task = collect_model_context(agent, task, input_fn=lambda _: next(answers), output_fn=lambda _: None)
    assert task.state == TaskState.AWAITING_CONFIRMATION
    assert store.list_actions("test-user") == []
    event = [e for e in store.list_events(task.task_id) if e.event_type == "model.result"][0]
    assert event.payload["model"] == "test-model"
    assert event.payload["input_tokens"] == 40
    assert event.payload["outcome"] == "validated"
    answers = iter(["0", ""])
    continue_task(agent, task, input_fn=lambda _: next(answers), output_fn=lambda _: None)
    store.close()
    store = SQLiteStore(path)
    agent = DietLensAgent(Harness(store))
    output = []
    continue_task(agent, store.get_task(task.task_id), input_fn=lambda _: "unknown", output_fn=output.append)
    assert output[-1]["adopted"] == 1
    assert output[-1]["completed"] == 0
    assert output[-1]["feedback_coverage"] == 0
    assert store.list_actions("test-user")[0].execution == Execution.UNKNOWN
    store.close()


def test_network_call_reservation_is_durable_and_outside_db_lock(tmp_path):
    path = str(tmp_path / "reservation.db")
    store = SQLiteStore(path)
    class ReservationProbe:
        def complete(self, *args):
            other = SQLiteStore(path)
            try:
                saved = other.get_task(task.task_id)
                assert saved.model_calls == 1
                assert other.list_events(task.task_id)[-1].event_type == "model.called"
            finally:
                other.close()
            raise OSError("offline")
    agent = DietLensAgent(Harness(store, ReservationProbe()))
    agent.onboard("u", budget=10, allergies=[], consents={"review_history": True})
    task = agent.harness.create_task("u")
    agent.harness.interpret(task.task_id, [])
    assert store.get_task(task.task_id).model_calls == 1
    assert store.list_events(task.task_id)[-1].payload["outcome"] == "manual_fallback"
    store.close()


@pytest.mark.parametrize("error", [TimeoutError(), URLError(TimeoutError())])
def test_timeout_is_classified_without_retry(error):
    class Offline:
        calls = 0
        def open(self, *args, **kwargs):
            self.calls += 1
            raise error
    client = provider("https://example.com/v1")
    client._opener = Offline()
    with pytest.raises(ToolError, match="model_timeout"):
        client.complete([], [], INTENT_SCHEMA)
    assert client._opener.calls == 1


def test_platform_network_restriction_has_specific_safe_code(server):
    url, handler = server
    handler.status = 403
    handler.payload = {"error": {"message": "当前网络环境不支持"}}
    with pytest.raises(ToolError, match="model_network_restricted"):
        provider(url).complete([], [], INTENT_SCHEMA)


def test_resolve_override_preserves_original_hostname_for_tls(monkeypatch):
    import socket
    import ssl
    from unittest.mock import Mock
    from dietlens_mvp.http_provider import ResolvedHTTPSConnection
    context = ssl.create_default_context()
    assert context.check_hostname
    assert context.verify_mode == ssl.CERT_REQUIRED
    tcp = Mock()
    connect = Mock(return_value=tcp)
    wrap = Mock(return_value=Mock())
    monkeypatch.setattr(socket, "create_connection", connect)
    monkeypatch.setattr(context, "wrap_socket", wrap)
    conn = ResolvedHTTPSConnection("agi.tongji.edu.cn", resolve_ip="10.67.0.251", context=context, timeout=5)
    conn.connect()
    assert connect.call_args.args[0] == ("10.67.0.251", 443)
    assert wrap.call_args.kwargs["server_hostname"] == "agi.tongji.edu.cn"
    conn.close()


def test_resolve_override_is_local_and_rejects_non_ip():
    with pytest.raises(ToolError, match="invalid_model_resolve_ip"):
        provider("https://example.com/v1", resolve_ip="not-an-ip")
    from urllib.request import HTTPSHandler
    plain = provider("https://example.com/v1")
    resolved = provider("https://example.com/v1", resolve_ip="10.67.0.251")
    assert not any(type(h).__name__ == "ResolvedHTTPSHandler" for h in plain._opener.handlers)
    assert any(type(h).__name__ == "ResolvedHTTPSHandler" for h in resolved._opener.handlers)


def test_noncritical_model_question_does_not_block_confirmed_context(server, tmp_path):
    from cli import collect_model_context
    url, handler = server
    handler.payload["choices"][0]["message"]["content"] = json.dumps({**INTENT, "missing_fields": ["behavior"]})
    store = SQLiteStore(str(tmp_path / "clarification.db"))
    agent = DietLensAgent(Harness(store, provider(url)))
    agent.onboard("u", budget=30, allergies=[], consents={"review_history": True})
    task = agent.harness.create_task("u")
    answers = iter(["午餐可选米饭或面条", "y"])
    task = collect_model_context(agent, task, input_fn=lambda _: next(answers), output_fn=lambda _: None)
    assert task.state == TaskState.AWAITING_CONFIRMATION
    assert store.list_actions("u") == []
    store.close()
