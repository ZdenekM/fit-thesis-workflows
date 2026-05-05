"""Identifier validation shared by workflow scripts."""

from __future__ import annotations

import re

ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def invalid_id_message(label: str) -> str:
    return f"Invalid {label}. Use only letters, numbers, dot, underscore, and dash; dot-only ids are not allowed."


def is_valid_id(value: str) -> bool:
    return bool(ID_RE.fullmatch(value) and set(value) != {"."})


def validate_id(label: str, value: str) -> None:
    if not is_valid_id(value):
        raise ValueError(invalid_id_message(label))
