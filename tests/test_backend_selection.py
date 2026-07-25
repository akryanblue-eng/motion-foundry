from __future__ import annotations

import json

from motion_foundry import EpisodeBrief, Storyboard, build_storyboard
from motion_foundry.backends.anthropic_backend import AnthropicStoryboardBackend
from motion_foundry.backends.fake import FakeStoryboardBackend
from motion_foundry.config import build_backend, resolve_backend_name


def test_default_backend_is_fake() -> None:
    assert resolve_backend_name() == "fake"
    assert isinstance(build_backend(), FakeStoryboardBackend)


def test_explicit_arg_overrides_env(monkeypatch) -> None:
    monkeypatch.setenv("MOTION_FOUNDRY_BACKEND", "anthropic")
    assert resolve_backend_name("fake") == "fake"


def test_anthropic_backend_selected_via_config(monkeypatch) -> None:
    monkeypatch.setenv("MOTION_FOUNDRY_BACKEND", "anthropic")
    monkeypatch.setenv("MOTION_FOUNDRY_MODEL", "claude-sonnet-5")
    adapter = build_backend()
    assert isinstance(adapter, AnthropicStoryboardBackend)
    assert adapter.model == "claude-sonnet-5"


class _StubMessages:
    """Minimal stand-in for client.messages, returning a canned scenes payload."""

    def __init__(self, scenes: list[dict]):
        self._scenes = scenes
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        text = json.dumps({"scenes": self._scenes})
        block = type("Block", (), {"type": "text", "text": text})()
        return type(
            "Resp",
            (),
            {"content": [block], "stop_reason": "end_turn", "_request_id": "req_test"},
        )()


class _StubClient:
    def __init__(self, scenes: list[dict]):
        self.messages = _StubMessages(scenes)


def test_anthropic_backend_with_injected_client(brief: EpisodeBrief) -> None:
    # A well-formed scenes payload referencing a real character id.
    scenes = [
        {
            "id": "scene1",
            "title": "Cold open",
            "location": "Relay deck",
            "summary": "Mara hears the signal.",
            "shots": [
                {
                    "id": "s1",
                    "character_ids": ["mara"],
                    "action": "Mara leans toward the terminal.",
                    "framing": "close_up",
                    "location": "Relay deck",
                    "dialogue_intent": "Register her alarm.",
                    "estimated_duration_seconds": 6.0,
                    "generation_prompt": "Close-up of Mara at a glowing terminal, teal light.",
                }
            ],
        }
    ]
    backend = AnthropicStoryboardBackend(model="claude-opus-5", client=_StubClient(scenes))
    board = build_storyboard(brief, backend)
    assert isinstance(board, Storyboard)
    assert board.generation.backend == "anthropic"
    assert board.generation.model == "claude-opus-5"
    assert board.generation.extra.get("request_id") == "req_test"
    assert board.scenes[0].shots[0].character_ids == ["mara"]
