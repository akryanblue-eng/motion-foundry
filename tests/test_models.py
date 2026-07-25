from __future__ import annotations

import pytest
from pydantic import ValidationError

from motion_foundry import Character, EpisodeBrief, Storyboard
from motion_foundry.backends.fake import FakeStoryboardBackend


def test_valid_brief_loads(brief: EpisodeBrief) -> None:
    assert brief.title == "The Last Signal"
    assert brief.target_duration_seconds == 180
    assert {c.id for c in brief.characters} == {"mara", "caretaker", "the_voice"}


def test_brief_rejects_zero_duration() -> None:
    with pytest.raises(ValidationError):
        EpisodeBrief(
            title="x",
            premise="p",
            target_duration_seconds=0,
            visual_tone="t",
            characters=[Character(id="a", name="A", role="lead", description="d")],
        )


def test_brief_rejects_empty_cast() -> None:
    with pytest.raises(ValidationError):
        EpisodeBrief(
            title="x",
            premise="p",
            target_duration_seconds=10,
            visual_tone="t",
            characters=[],
        )


def test_brief_rejects_duplicate_character_ids() -> None:
    with pytest.raises(ValidationError, match="duplicate character ids"):
        EpisodeBrief(
            title="x",
            premise="p",
            target_duration_seconds=10,
            visual_tone="t",
            characters=[
                Character(id="a", name="A", role="lead", description="d"),
                Character(id="a", name="B", role="rival", description="d"),
            ],
        )


def test_brief_rejects_bad_character_id() -> None:
    with pytest.raises(ValidationError):
        Character(id="Not-Valid", name="A", role="lead", description="d")


def test_brief_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        Character(id="a", name="A", role="lead", description="d", surprise="!")


def test_storyboard_rejects_unknown_character_reference(brief: EpisodeBrief) -> None:
    payload = FakeStoryboardBackend().generate(brief)
    # Corrupt a shot to reference a character id that does not exist.
    payload["scenes"][0]["shots"][-1]["character_ids"] = ["ghost"]
    with pytest.raises(ValidationError, match="unknown character id"):
        Storyboard.model_validate(payload)


def test_storyboard_rejects_duplicate_shot_ids(brief: EpisodeBrief) -> None:
    payload = FakeStoryboardBackend().generate(brief)
    first_id = payload["scenes"][0]["shots"][0]["id"]
    payload["scenes"][0]["shots"][1]["id"] = first_id
    with pytest.raises(ValidationError, match="duplicate shot ids"):
        Storyboard.model_validate(payload)
