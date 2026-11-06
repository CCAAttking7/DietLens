from __future__ import annotations

import re


def clean_text(value: str) -> str:
    """Normalize user text without inventing missing facts."""
    return re.sub(r"\s+", " ", value.strip())


def clean_options(options: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for option in options:
        cleaned = clean_text(option)
        key = cleaned.casefold()
        if cleaned and key not in seen:
            result.append(cleaned)
            seen.add(key)
    return result


def clean_terms(terms: list[str] | None) -> list[str]:
    return clean_options(terms or [])
