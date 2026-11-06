from dataclasses import asdict
from datetime import datetime
from enum import Enum
import json
from typing import Any


def dumps(value: Any) -> str:
    def encode(item: Any) -> Any:
        if isinstance(item, Enum):
            return item.value
        if isinstance(item, datetime):
            return item.isoformat()
        if hasattr(item, "__dataclass_fields__"):
            return {k: encode(v) for k, v in asdict(item).items()}
        if isinstance(item, dict):
            return {k: encode(v) for k, v in item.items()}
        if isinstance(item, (list, tuple)):
            return [encode(v) for v in item]
        return item
    return json.dumps(encode(value), ensure_ascii=False)

