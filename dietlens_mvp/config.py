from dataclasses import dataclass, field
import os
from pathlib import Path

from dotenv import load_dotenv
from .errors import ToolError


@dataclass(frozen=True)
class Settings:
    database_path: str = "dietlens.db"
    log_level: str = "INFO"
    api_key: str = field(default="", repr=False)
    model_base_url: str = "https://api.openai.com/v1"
    model_name: str = ""
    model_timeout_seconds: float = 30
    model_json_mode: bool = True
    model_resolve_ip: str | None = None
    model_routes: dict[str, str] = field(default_factory=dict)
    model_route_json_modes: dict[str, bool] = field(default_factory=dict)
    supabase_url: str = ""
    supabase_db_url: str = ""
    supabase_publishable_key: str = field(default="", repr=False)
    auth_mode: str = "demo"

    @classmethod
    def from_env(cls, env_file: str | None = None) -> "Settings":
        # Load only the chosen file; shell environment always takes precedence.
        if env_file is not None:
            load_dotenv(Path(env_file), override=False)
        try:
            timeout = float(os.getenv("DIETLENS_MODEL_TIMEOUT", "30"))
        except ValueError:
            raise ToolError("invalid_model_config") from None
        return cls(database_path=os.getenv("DIETLENS_DB", "dietlens.db"),
                   log_level=os.getenv("DIETLENS_LOG_LEVEL", "INFO"),
                   api_key=os.getenv("DIETLENS_API_KEY", ""),
                   model_base_url=os.getenv("DIETLENS_MODEL_BASE_URL", "https://api.openai.com/v1"),
                   model_name=os.getenv("DIETLENS_MODEL", ""),
                   model_timeout_seconds=timeout,
                   model_json_mode=os.getenv("DIETLENS_MODEL_JSON_MODE", "true").lower() == "true",
                   model_resolve_ip=os.getenv("DIETLENS_MODEL_RESOLVE_IP") or None,
                   model_routes={route: value for route in ("context", "food", "plan", "review")
                                 if (value := os.getenv(f"DIETLENS_MODEL_{route.upper()}", "").strip())},
                   model_route_json_modes={route: value.lower() == "true"
                                           for route in ("context", "food", "plan", "review")
                                           if (value := os.getenv(f"DIETLENS_MODEL_{route.upper()}_JSON_MODE", "").strip())},
                   supabase_url=os.getenv("SUPABASE_URL", ""),
                   supabase_db_url=os.getenv("SUPABASE_DB_URL", ""),
                   supabase_publishable_key=os.getenv("SUPABASE_PUBLISHABLE_KEY", ""),
                   auth_mode=os.getenv("DIETLENS_AUTH_MODE", "demo").lower())

    def create_provider(self):
        from .http_provider import OpenAICompatibleProvider
        from .model_router import TaskModelRouter
        def make(model, json_mode=None):
            return OpenAICompatibleProvider(api_key=self.api_key, base_url=self.model_base_url,
                                            model=model, timeout_seconds=self.model_timeout_seconds,
                                            json_mode=self.model_json_mode if json_mode is None else json_mode, resolve_ip=self.model_resolve_ip)
        default = make(self.model_name)
        routes = set(self.model_routes) | set(self.model_route_json_modes)
        if not routes:
            return default
        return TaskModelRouter(default, {route: make(self.model_routes.get(route, self.model_name),
                                                    self.model_route_json_modes.get(route)) for route in routes})
