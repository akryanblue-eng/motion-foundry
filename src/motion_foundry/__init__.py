"""motion-foundry: an internal Quantum Star animation production tool.

This package currently implements the **storyboard** stage: it turns an episode
brief (characters + premise + target duration + visual tone) into a validated
``storyboard.json`` and a human-readable ``storyboard.md``.
"""

from __future__ import annotations

from .models import (
    Character,
    EpisodeBrief,
    Framing,
    GenerationMetadata,
    Scene,
    Shot,
    Storyboard,
)
from .storyboard import (
    StoryboardValidationError,
    build_storyboard,
    load_brief,
    write_storyboard_json,
)

__all__ = [
    "Character",
    "EpisodeBrief",
    "Framing",
    "GenerationMetadata",
    "Scene",
    "Shot",
    "Storyboard",
    "StoryboardValidationError",
    "build_storyboard",
    "load_brief",
    "write_storyboard_json",
]

__version__ = "0.1.0"
