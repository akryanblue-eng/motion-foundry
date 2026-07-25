"""Storyboard stage orchestration.

Loads and validates an episode brief, asks a backend for a raw storyboard
payload, then validates that payload against the ``Storyboard`` schema. Both
boundaries fail closed:

* a malformed brief raises ``pydantic.ValidationError`` on load;
* an invalid generated storyboard raises ``StoryboardValidationError`` here,
  rather than being written to disk.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from .backends.base import StoryboardBackend
from .models import EpisodeBrief, Storyboard


class StoryboardValidationError(RuntimeError):
    """Raised when a backend produces a payload that fails schema validation."""


def load_brief(path: str | Path) -> EpisodeBrief:
    """Load and validate an episode brief from a JSON file (fails closed)."""
    raw = Path(path).read_text(encoding="utf-8")
    data = json.loads(raw)
    return EpisodeBrief.model_validate(data)


def build_storyboard(brief: EpisodeBrief, backend: StoryboardBackend) -> Storyboard:
    """Generate and validate a storyboard for ``brief`` using ``backend``."""
    payload = backend.generate(brief)
    try:
        return Storyboard.model_validate(payload)
    except ValidationError as exc:
        raise StoryboardValidationError(
            f"backend '{backend.name}' produced an invalid storyboard:\n{exc}"
        ) from exc


def write_storyboard_json(storyboard: Storyboard, path: str | Path) -> None:
    """Write the validated storyboard as pretty JSON.

    Serialized deterministically (stable key order, trailing newline) so repeated
    fake-backend runs produce byte-identical files.
    """
    payload = storyboard.model_dump(mode="json")
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    Path(path).write_text(text, encoding="utf-8")
