"""Pydantic models for the storyboard stage.

These define the contract for every input the storyboard stage accepts and every
output it produces. Inputs are validated on the way in; generated output is
validated on the way out (see ``storyboard.build_storyboard``). Both fail closed:
a malformed brief or an invalid generated storyboard raises rather than silently
producing a degraded artifact.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Bump when the storyboard.json shape changes in a backward-incompatible way.
SCHEMA_VERSION = "1.0"

_ID_PATTERN = r"^[a-z0-9][a-z0-9_]*$"


class Character(BaseModel):
    """A structured character definition supplied in the episode brief."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(
        ...,
        pattern=_ID_PATTERN,
        min_length=1,
        max_length=64,
        description="Stable lowercase identifier, referenced by shots (e.g. 'mara').",
    )
    name: str = Field(..., min_length=1, max_length=120, description="Display name.")
    role: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="Narrative role, e.g. 'protagonist', 'rival', 'mentor'.",
    )
    description: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Who the character is: personality, motivation, background.",
    )
    visual_signature: str | None = Field(
        default=None,
        max_length=2000,
        description="Key visual traits used to keep the character on-model across shots.",
    )


class EpisodeBrief(BaseModel):
    """The full input to the storyboard stage."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=200, description="Episode title.")
    premise: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="What happens in the episode: the story to be broken into scenes.",
    )
    characters: list[Character] = Field(
        ...,
        min_length=1,
        description="Characters available to the episode. Shots reference these by id.",
    )
    target_duration_seconds: int = Field(
        ...,
        gt=0,
        le=3600,
        description="Target runtime of the finished episode, in seconds.",
    )
    visual_tone: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Overall look and mood, e.g. 'moody neo-noir, hand-painted'.",
    )
    scene_count: int | None = Field(
        default=None,
        gt=0,
        le=100,
        description="Optional hint for how many scenes to produce.",
    )

    @model_validator(mode="after")
    def _unique_character_ids(self) -> "EpisodeBrief":
        ids = [c.id for c in self.characters]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            raise ValueError(f"duplicate character ids: {', '.join(dupes)}")
        return self


class Framing(str, Enum):
    """Shot framing / camera distance vocabulary."""

    ESTABLISHING = "establishing"
    EXTREME_WIDE = "extreme_wide"
    WIDE = "wide"
    FULL = "full"
    MEDIUM = "medium"
    MEDIUM_CLOSE_UP = "medium_close_up"
    CLOSE_UP = "close_up"
    EXTREME_CLOSE_UP = "extreme_close_up"
    OVER_THE_SHOULDER = "over_the_shoulder"
    POV = "pov"
    TWO_SHOT = "two_shot"
    INSERT = "insert"


class Shot(BaseModel):
    """A single shot within a scene."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., pattern=_ID_PATTERN, min_length=1, max_length=80)
    character_ids: list[str] = Field(
        default_factory=list,
        description="Character ids present in the shot. May be empty (e.g. an establishing shot).",
    )
    action: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="What visibly happens in the shot.",
    )
    framing: Framing = Field(..., description="Camera distance / framing.")
    location: str = Field(..., min_length=1, max_length=200, description="Where the shot takes place.")
    dialogue_intent: str = Field(
        ...,
        max_length=2000,
        description="The intent of any dialogue (not verbatim lines). Empty string if silent.",
    )
    estimated_duration_seconds: float = Field(
        ...,
        gt=0,
        le=600,
        description="Estimated on-screen duration of this shot, in seconds.",
    )
    generation_prompt: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Self-contained prompt for a downstream image/video generator.",
    )


class Scene(BaseModel):
    """An ordered group of shots sharing a location and story beat."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., pattern=_ID_PATTERN, min_length=1, max_length=80)
    title: str = Field(..., min_length=1, max_length=200)
    location: str = Field(..., min_length=1, max_length=200)
    summary: str = Field(..., min_length=1, max_length=2000, description="What this scene accomplishes.")
    shots: list[Shot] = Field(..., min_length=1)


class GenerationMetadata(BaseModel):
    """Provenance for a generated storyboard: which backend/model produced it."""

    model_config = ConfigDict(extra="forbid")

    backend: str = Field(..., min_length=1, description="Backend adapter name, e.g. 'fake' or 'anthropic'.")
    model: str = Field(..., min_length=1, description="Model identifier used by the backend.")
    generated_at: datetime = Field(..., description="UTC timestamp the storyboard was produced.")
    request_fingerprint: str = Field(
        ...,
        min_length=1,
        description="Deterministic hash of the episode brief this storyboard was built from.",
    )
    extra: dict[str, str] = Field(
        default_factory=dict,
        description="Additional backend-specific metadata (e.g. request id, effort level).",
    )


class Storyboard(BaseModel):
    """The validated output artifact of the storyboard stage."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = SCHEMA_VERSION
    episode_title: str = Field(..., min_length=1, max_length=200)
    premise: str = Field(..., min_length=1, max_length=5000)
    visual_tone: str = Field(..., min_length=1, max_length=1000)
    target_duration_seconds: int = Field(..., gt=0, le=3600)
    characters: list[Character] = Field(
        ...,
        min_length=1,
        description="Copied from the brief so the storyboard is self-contained.",
    )
    generation: GenerationMetadata
    scenes: list[Scene] = Field(..., min_length=1)

    @model_validator(mode="after")
    def _validate_references(self) -> "Storyboard":
        known = {c.id for c in self.characters}

        scene_ids: list[str] = []
        shot_ids: list[str] = []
        for scene in self.scenes:
            scene_ids.append(scene.id)
            for shot in scene.shots:
                shot_ids.append(shot.id)
                unknown = [cid for cid in shot.character_ids if cid not in known]
                if unknown:
                    raise ValueError(
                        f"shot '{shot.id}' references unknown character id(s): "
                        f"{', '.join(sorted(set(unknown)))}"
                    )
                dupes = sorted({c for c in shot.character_ids if shot.character_ids.count(c) > 1})
                if dupes:
                    raise ValueError(
                        f"shot '{shot.id}' lists duplicate character id(s): {', '.join(dupes)}"
                    )

        scene_dupes = sorted({s for s in scene_ids if scene_ids.count(s) > 1})
        if scene_dupes:
            raise ValueError(f"duplicate scene ids: {', '.join(scene_dupes)}")
        shot_dupes = sorted({s for s in shot_ids if shot_ids.count(s) > 1})
        if shot_dupes:
            raise ValueError(f"duplicate shot ids across storyboard: {', '.join(shot_dupes)}")
        return self

    @property
    def total_estimated_duration_seconds(self) -> float:
        return round(
            sum(shot.estimated_duration_seconds for scene in self.scenes for shot in scene.shots),
            3,
        )
