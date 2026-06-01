"""Tests del backoff de transporte de FoundryClient (offline, sin red real)."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from openai import APITimeoutError

from app.core.config import get_settings
from app.core.exceptions import FoundryError
from app.services.foundry_client import FoundryClient


def _respuesta_chat_ok(content: str = '{"ok": true}') -> MagicMock:
    resp = MagicMock()
    choice = MagicMock()
    choice.message.content = content
    choice.finish_reason = "stop"
    resp.choices = [choice]
    resp.usage = SimpleNamespace(prompt_tokens=10, completion_tokens=20, total_tokens=30)
    return resp


@pytest.fixture
def foundry(monkeypatch):
    """FoundryClient real con time.sleep neutralizado; registra los delays en _sleeps."""
    sleeps: list[float] = []
    monkeypatch.setattr("app.services.foundry_client.time.sleep", sleeps.append)
    fc = FoundryClient(get_settings())
    fc._sleeps = sleeps
    return fc


def _mockear_create(foundry, monkeypatch, side_effect) -> MagicMock:
    create = MagicMock(side_effect=side_effect)
    monkeypatch.setattr(foundry._client.chat.completions, "create", create)
    return create


def test_reintenta_ante_error_transitorio(foundry, monkeypatch):
    req = httpx.Request("POST", "https://fake/chat")
    create = _mockear_create(
        foundry, monkeypatch, [APITimeoutError(request=req), _respuesta_chat_ok()]
    )

    _, parsed = foundry.chat_json_raw("sys", "user")

    assert parsed == {"ok": True}
    assert create.call_count == 2  # falló una vez, reintentó y funcionó
    assert len(foundry._sleeps) == 1  # un solo backoff


def test_no_reintenta_ante_error_permanente(foundry, monkeypatch):
    create = _mockear_create(foundry, monkeypatch, ValueError("boom"))

    with pytest.raises(FoundryError):
        foundry.chat_json_raw("sys", "user")

    assert create.call_count == 1  # sin reintentos
    assert foundry._sleeps == []


def test_agota_reintentos_y_envuelve_en_foundry_error(foundry, monkeypatch):
    req = httpx.Request("POST", "https://fake/chat")
    create = _mockear_create(foundry, monkeypatch, APITimeoutError(request=req))

    with pytest.raises(FoundryError):
        foundry.chat_json_raw("sys", "user")

    # llm_max_retries=2 → 3 intentos totales, 2 esperas
    assert create.call_count == 3
    assert len(foundry._sleeps) == 2
