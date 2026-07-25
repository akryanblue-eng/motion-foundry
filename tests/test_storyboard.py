from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from motion_foundry import EpisodeBrief, build_storyboard
from motion_foundry.backends.base import StoryboardBackend
from motion_foundry.backends.fake import FakeStoryboardBackend
from motion_foundry.cli import cli
from motion_foundry.render import render_markdown
from motion_foundry.storyboard import StoryboardValidationError


class BrokenBackend(StoryboardBackend):
    """Returns a payload that violates the schema (a shot with no duration)."""

    name = "broken"
    model = "broken-v0"

    def generate(self, brief: EpisodeBrief) -> dict:
        payload = FakeStoryboardBackend().generate(brief)
        del payload["scenes"][0]["shots"][0]["estimated_duration_seconds"]
        return payload


def test_build_fails_closed_on_invalid_generated_output(brief: EpisodeBrief) -> None:
    with pytest.raises(StoryboardValidationError):
        build_storyboard(brief, BrokenBackend())


def test_markdown_render_contains_key_sections(brief: EpisodeBrief) -> None:
    board = build_storyboard(brief, FakeStoryboardBackend())
    md = render_markdown(board)
    assert md.startswith("# The Last Signal")
    assert "## Characters" in md
    assert "## Scene 1" in md
    assert "Generation prompt:" in md


def test_cli_generates_artifacts(brief_path: Path, tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["storyboard", str(brief_path), "--out-dir", str(out_dir), "--backend", "fake"],
    )
    assert result.exit_code == 0, result.output

    json_path = out_dir / "storyboard.json"
    md_path = out_dir / "storyboard.md"
    assert json_path.exists()
    assert md_path.exists()

    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["schema_version"] == "1.0"
    assert data["episode_title"] == "The Last Signal"
    assert data["generation"]["backend"] == "fake"
    assert data["scenes"]

    # Re-running the fake backend produces byte-identical artifacts.
    result2 = runner.invoke(
        cli,
        ["storyboard", str(brief_path), "--out-dir", str(out_dir), "--backend", "fake"],
    )
    assert result2.exit_code == 0, result2.output
    assert json.loads(json_path.read_text(encoding="utf-8")) == data


def test_cli_rejects_malformed_brief(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"title": "x"}), encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(cli, ["storyboard", str(bad), "--out-dir", str(tmp_path / "o")])
    assert result.exit_code != 0
    assert "invalid episode brief" in result.output


def test_cli_backend_selected_via_config(brief_path: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MOTION_FOUNDRY_BACKEND", "fake")
    runner = CliRunner()
    result = runner.invoke(cli, ["storyboard", str(brief_path), "--out-dir", str(tmp_path / "o")])
    assert result.exit_code == 0, result.output
    assert "Backend: fake" in result.output
