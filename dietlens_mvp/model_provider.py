"""Model output is advisory; no provider receives repository or write tools."""
from dataclasses import dataclass
import json
import re
from typing import Protocol
from jsonschema import ValidationError, validate
from .errors import ToolError

INTENT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["intent", "entities", "missing_fields", "candidate_tool", "user_message", "confidence"],
    "properties": {
        "intent": {"enum": ["food_search", "menu_recommendation", "plan", "meal_record", "micro_action", "review"]},
        "entities": {"type": "object"},
        "missing_fields": {"type": "array", "items": {"type": "string"}},
        "candidate_tool": {"type": "string"},
        "user_message": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
}


@dataclass(frozen=True)
class ModelResponse:
    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_units: int = 0
    prompt_version: str = "intent-v1"
    model: str = "stub"


class ModelProvider(Protocol):
    def complete(self, messages: list[dict], tools: list[dict], response_schema: dict) -> ModelResponse: ...


class StubModelProvider:
    def complete(self, messages: list[dict], tools: list[dict], response_schema: dict) -> ModelResponse:
        return ModelResponse(json.dumps({
            "intent": "micro_action", "entities": {}, "missing_fields": ["meal", "options"],
            "candidate_tool": "", "user_message": "请提供餐次和当前可选餐食。", "confidence": 0,
        }, ensure_ascii=False))


def fallback_intent(messages: list[dict]) -> dict:
    """Extract the two fields needed for the next state without a network call."""
    text = next((message.get("content", "") for message in reversed(messages)
                 if message.get("role") == "user" and isinstance(message.get("content"), str)), "")
    meal_match = re.search(r"(早餐|早饭|午餐|午饭|晚餐|晚饭)", text)
    meal_alias = {"早饭": "早餐", "午饭": "午餐", "晚饭": "晚餐"}
    meal = meal_alias.get(meal_match.group(1), meal_match.group(1)) if meal_match else ""
    remainder = text[meal_match.end():] if meal_match else text
    remainder = re.sub(r"想在|想吃|可以|可选|选择|选|里面|里|一个|吃什么|吃", "", remainder)
    options = [item.strip(" ：:。！？!?（）()") for item in re.split(r"[、,/，]|或|还是|和|以及", remainder)]
    options = [item for item in options if 1 < len(item) <= 40]
    missing = []
    if not meal:
        missing.append("meal")
    if not options:
        missing.append("options")
    if missing:
        message = "我还没听清餐次或可选餐食，请再说一次。"
    else:
        message = f"我先整理为：{meal}，可选 { '、'.join(options) }。请核对。"
    return {"intent": "micro_action", "entities": {"meal": meal, "options": options},
            "missing_fields": missing, "candidate_tool": "", "user_message": message,
            "confidence": 0.5 if not missing else 0}


def parse_intent(response: ModelResponse) -> dict:
    try:
        def reject_constant(value):
            raise ValueError("non_finite_number")
        data = json.loads(response.content, parse_constant=reject_constant)
        validate(data, INTENT_SCHEMA)
        return data
    except (ValueError, TypeError, ValidationError) as exc:
        raise ToolError("invalid_model_output") from exc
