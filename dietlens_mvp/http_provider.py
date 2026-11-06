"""Small Chat Completions transport for explicitly configured compatible services."""
import json
import http.client
import ipaddress
import ssl
import math
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, ProxyHandler, Request, build_opener

from .errors import ToolError
from .model_provider import ModelResponse


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward the bearer credential to a redirected host.
        return None


class ResolvedHTTPSConnection(http.client.HTTPSConnection):
    """Override the TCP destination while retaining hostname-based TLS verification."""

    def __init__(self, host: str, *, resolve_ip: str, **kwargs) -> None:
        super().__init__(host, **kwargs)
        def connect_to_ip(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None):
            return socket.create_connection((resolve_ip, address[1]), timeout, source_address)
        self._create_connection = connect_to_ip


class ResolvedHTTPSHandler(HTTPSHandler):
    def __init__(self, hostname: str, resolve_ip: str) -> None:
        super().__init__(context=ssl.create_default_context())
        self.hostname = hostname
        self.resolve_ip = resolve_ip

    def https_open(self, request):
        if urlsplit(request.full_url).hostname != self.hostname:
            raise ToolError("model_host_mismatch")
        def connection(host, **kwargs):
            return ResolvedHTTPSConnection(host, resolve_ip=self.resolve_ip, **kwargs)
        return self.do_open(connection, request, context=self._context)


class OpenAICompatibleProvider:
    def __init__(self, *, api_key: str, base_url: str, model: str,
                 timeout_seconds: float = 30, json_mode: bool = True, resolve_ip: str | None = None) -> None:
        url = urlsplit(base_url)
        if (url.scheme != "https" and not (url.scheme == "http" and url.hostname in {"127.0.0.1", "localhost", "::1"})) or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ToolError("invalid_model_base_url")
        if not api_key.strip() or not model.strip() or not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 120:
            raise ToolError("invalid_model_config")
        if any(c in api_key for c in "\r\n"):
            raise ToolError("invalid_model_config")
        self._api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.json_mode = json_mode
        handlers = [NoRedirect()]
        if resolve_ip:
            try:
                ipaddress.ip_address(resolve_ip)
            except ValueError:
                raise ToolError("invalid_model_resolve_ip") from None
            if url.scheme != "https":
                raise ToolError("invalid_model_resolve_ip")
            handlers.extend([ProxyHandler({}), ResolvedHTTPSHandler(url.hostname, resolve_ip)])
        self._opener = build_opener(*handlers)

    def complete(self, messages: list[dict], tools: list[dict], response_schema: dict) -> ModelResponse:
        # The model proposes fields only. No runtime functions or secrets enter the prompt.
        system = (
            "你是 DietLens 的中文饮食情境解析器。仅返回符合以下 Schema 的 JSON。"
            "提取用户明确自述的餐次 entities.meal（字符串）及可选餐食 entities.options（字符串数组）。"
            "不推断未提供的配料、过敏安全、价格或营养；不提供诊断、治疗或药物建议。"
            "本入口只需提取 meal 和 options；这两个字段缺失时放入 missing_fields 并简短澄清。"
            "不得把行为、预算或偏好列为本次缺失字段：微行动由后续确定性规则生成，不需用户提供。"
            "一般饮食情境 intent=micro_action。"
            "candidate_tool 留空，任何字段均需用户核对，不得宣称已经保存或执行。"
            "user_message 用一句简体中文说明已提取信息或需要澄清的问题。Schema: "
            + json.dumps(response_schema, ensure_ascii=False)
        )
        if tools:
            raise ToolError("model_tools_not_supported")
        if any(m.get("role") not in {"user", "assistant"} or not isinstance(m.get("content"), str) for m in messages):
            raise ToolError("invalid_model_messages")
        payload = {"model": self.model, "messages": [{"role": "system", "content": system}, *messages], "stream": False}
        if self.json_mode:
            payload["response_format"] = {"type": "json_object"}
        request = Request(self.base_url + "/chat/completions", data=json.dumps(payload).encode(),
                          headers={"Authorization": "Bearer " + self._api_key,
                                   "Content-Type": "application/json", "Accept": "application/json"})
        try:
            # No automatic retry: a timeout may still have incurred a charge upstream.
            with self._opener.open(request, timeout=self.timeout_seconds) as response:
                raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ToolError("model_response_too_large")
        except HTTPError as exc:
            status = exc.code
            try:
                detail = exc.read(16000).decode("utf-8", errors="replace")
            except OSError:
                detail = ""
            finally:
                exc.close()
            try:
                decoded = json.loads(detail)
                error = decoded.get("error", {}) if isinstance(decoded, dict) else {}
                message = error.get("message", "") if isinstance(error, dict) else str(error)
            except ValueError:
                message = detail
            if status == 403 and "当前网络环境不支持" in message:
                raise ToolError("model_network_restricted") from None
            codes = {401: "model_authentication_failed", 403: "model_access_denied",
                     429: "model_rate_limited"}
            raise ToolError(codes.get(status, "model_http_failed")) from None
        except (TimeoutError, socket.timeout):
            raise ToolError("model_timeout") from None
        except URLError as exc:
            code = "model_timeout" if isinstance(exc.reason, (TimeoutError, socket.timeout)) else "model_connection_failed"
            raise ToolError(code) from None
        try:
            data = json.loads(raw)
            choice = data["choices"][0]
            if choice.get("finish_reason") != "stop":
                raise ToolError("model_response_incomplete")
            content = choice["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ToolError("invalid_model_response")
            usage = data.get("usage") or {}
            counts = [usage.get("prompt_tokens"), usage.get("completion_tokens")]
            if any(v is not None and (type(v) is not int or v < 0) for v in counts):
                raise ToolError("invalid_model_response")
            return ModelResponse(content=content, input_tokens=counts[0], output_tokens=counts[1],
                                 model=self.model)
        except (ValueError, KeyError, IndexError, TypeError, AttributeError):
            raise ToolError("invalid_model_response") from None
