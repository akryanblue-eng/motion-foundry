from __future__ import annotations

import socket

import pytest

from motion_foundry import EpisodeBrief, Storyboard, build_storyboard
from motion_foundry.backends.fake import FakeStoryboardBackend


def test_fake_backend_produces_valid_storyboard(brief: EpisodeBrief) -> None:
    board = build_storyboard(brief, FakeStoryboardBackend())
    assert isinstance(board, Storyboard)
    assert board.episode_title == brief.title
    assert board.generation.backend == "fake"
    assert len(board.scenes) >= 1
    assert all(scene.shots for scene in board.scenes)


def test_fake_backend_is_deterministic(brief: EpisodeBrief) -> None:
    first = FakeStoryboardBackend().generate(brief)
    second = FakeStoryboardBackend().generate(brief)
    assert first == second


def test_fake_backend_output_is_byte_identical(brief: EpisodeBrief, tmp_path) -> None:
    from motion_foundry.storyboard import write_storyboard_json

    board_a = build_storyboard(brief, FakeStoryboardBackend())
    board_b = build_storyboard(brief, FakeStoryboardBackend())
    path_a = tmp_path / "a.json"
    path_b = tmp_path / "b.json"
    write_storyboard_json(board_a, path_a)
    write_storyboard_json(board_b, path_b)
    assert path_a.read_bytes() == path_b.read_bytes()


def test_fake_backend_timestamp_is_stable(brief: EpisodeBrief) -> None:
    a = FakeStoryboardBackend().generate(brief)
    b = FakeStoryboardBackend().generate(brief)
    assert a["generation"]["generated_at"] == b["generation"]["generated_at"]


def test_fake_backend_differs_between_briefs(brief: EpisodeBrief) -> None:
    other = brief.model_copy(update={"premise": brief.premise + " (alternate cut)"})
    a = FakeStoryboardBackend().generate(brief)
    b = FakeStoryboardBackend().generate(other)
    assert a["generation"]["request_fingerprint"] != b["generation"]["request_fingerprint"]
    assert a != b


def test_fake_backend_needs_no_network(brief: EpisodeBrief, monkeypatch) -> None:
    def _blocked(*args, **kwargs):  # pragma: no cover - only fires on a violation
        raise AssertionError("fake backend must not open a network connection")

    monkeypatch.setattr(socket, "socket", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    board = build_storyboard(brief, FakeStoryboardBackend())
    assert isinstance(board, Storyboard)


def test_fake_backend_honors_scene_count(brief: EpisodeBrief) -> None:
    brief_two = brief.model_copy(update={"scene_count": 2})
    board = build_storyboard(brief_two, FakeStoryboardBackend())
    assert len(board.scenes) == 2
