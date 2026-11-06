from dataclasses import dataclass
from typing import Any, Callable

from jsonschema import ValidationError, validate
from .errors import ToolError


@dataclass(frozen=True)
class ToolSpec:
    name: str
    access: str
    requires_confirmation: bool
    input_schema: dict
    output_schema: dict
    timeout_seconds: float = 10
    max_retries: int = 0
    idempotent: bool = True


class ToolRegistry:
    """Explicit allowlist. Confirmation authority is supplied by Harness only."""

    def __init__(self) -> None:
        self._tools: dict[str, tuple[ToolSpec, Callable[..., dict]]] = {}

    def register(self, spec: ToolSpec, handler: Callable[..., dict]) -> None:
        if spec.name in self._tools:
            raise ValueError("duplicate_tool")
        if spec.access not in {"read", "write"} or (spec.access == "write" and not spec.requires_confirmation):
            raise ValueError("unsafe_tool_spec")
        self._tools[spec.name] = (spec, handler)

    def invoke(self, name: str, arguments: dict, *, confirmed: bool = False) -> dict:
        if name not in self._tools:
            raise ToolError("tool_not_allowed")
        spec, handler = self._tools[name]
        if spec.requires_confirmation and not confirmed:
            raise ToolError("confirmation_required")
        try:
            validate(arguments, spec.input_schema)
        except ValidationError as exc:
            raise ToolError("invalid_tool_input") from exc
        result = handler(**arguments)
        try:
            validate(result, spec.output_schema)
        except ValidationError as exc:
            raise ToolError("invalid_tool_output") from exc
        return result
