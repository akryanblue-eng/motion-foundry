"""Deterministic fake backend.

Produces a schema-valid storyboard purely from the brief, with no network access.
The same brief always yields byte-for-byte identical output — including the
``generated_at`` timestamp, which is derived from the brief fingerprint rather
than the wall clock. This is what makes fake-backend runs reproducible and lets
tests assert on exact output.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from ..fingerprint import brief_fingerprint
from ..models import SCHEMA_VERSION, EpisodeBrief, Framing
from .base import StoryboardBackend

# Deterministic timestamps are anchored to this reference and offset by the
# brief fingerprint, so they are stable per-brief but still differ between briefs.
_EPOCH = datetime(2020, 1, 1, tzinfo=timezone.utc)

# A framing rotation that reads like a plausible edit: establish, then vary
# distance shot to shot.
_FRAMING_CYCLE = [
    Framing.ESTABLISHING,
    Framing.WIDE,
    Framing.MEDIUM,
    Framing.OVER_THE_SHOULDER,
    Framing.CLOSE_UP,
    Framing.TWO_SHOT,
    Framing.MEDIUM_CLOSE_UP,
    Framing.INSERT,
]


def _split(total: float, parts: int) -> list[float]:
    """Split ``total`` into ``parts`` positive values that sum to ``total``.

    Deterministic: equal shares rounded to one decimal, with any rounding
    remainder folded into the last share.
    """
    if parts <= 0:
        return []
    share = round(total / parts, 1)
    values = [share] * (parts - 1)
    last = round(total - sum(values), 1)
    if last <= 0:
        # Degenerate case (very short total): give every part a tiny positive slice.
        values = [0.1] * (parts - 1)
        last = round(total - sum(values), 1)
        if last <= 0:
            last = 0.1
    values.append(last)
    return values


class FakeStoryboardBackend(StoryboardBackend):
    """Generates a deterministic storyboard from the brief alone."""

    name = "fake"
    model = "deterministic-v1"

    def generate(self, brief: EpisodeBrief) -> dict:
        fingerprint = brief_fingerprint(brief)
        rng = random.Random(int(fingerprint[:16], 16))

        scene_count = brief.scene_count or max(2, min(round(brief.target_duration_seconds / 45), 8))
        scene_durations = _split(float(brief.target_duration_seconds), scene_count)

        characters = brief.characters
        char_cursor = 0

        scenes: list[dict] = []
        for scene_index, scene_seconds in enumerate(scene_durations, start=1):
            location = self._location(brief, scene_index)
            shot_count = 2 + (rng.randrange(3))  # 2..4 shots
            shot_durations = _split(scene_seconds, shot_count)

            shots: list[dict] = []
            for shot_index, shot_seconds in enumerate(shot_durations, start=1):
                # Rotate through characters so the whole cast gets screen time.
                framing = _FRAMING_CYCLE[(scene_index + shot_index) % len(_FRAMING_CYCLE)]
                if framing is Framing.ESTABLISHING and shot_index == 1:
                    present = []
                else:
                    take = 2 if framing is Framing.TWO_SHOT and len(characters) >= 2 else 1
                    present = []
                    for _ in range(take):
                        present.append(characters[char_cursor % len(characters)].id)
                        char_cursor += 1

                action = self._action(brief, present, framing)
                dialogue_intent = self._dialogue_intent(present)
                shots.append(
                    {
                        "id": f"s{scene_index}_shot{shot_index}",
                        "character_ids": present,
                        "action": action,
                        "framing": framing.value,
                        "location": location,
                        "dialogue_intent": dialogue_intent,
                        "estimated_duration_seconds": shot_seconds,
                        "generation_prompt": self._prompt(brief, present, framing, location, action),
                    }
                )

            scenes.append(
                {
                    "id": f"scene{scene_index}",
                    "title": f"{brief.title} — Beat {scene_index}",
                    "location": location,
                    "summary": (
                        f"Beat {scene_index} of {scene_count}: advances the premise "
                        f"toward its resolution."
                    ),
                    "shots": shots,
                }
            )

        offset = int(fingerprint[:12], 16) % 1_000_000_000
        generated_at = _EPOCH + timedelta(seconds=offset)

        return {
            "schema_version": SCHEMA_VERSION,
            "episode_title": brief.title,
            "premise": brief.premise,
            "visual_tone": brief.visual_tone,
            "target_duration_seconds": brief.target_duration_seconds,
            "characters": [c.model_dump(mode="json") for c in brief.characters],
            "generation": {
                "backend": self.name,
                "model": self.model,
                "generated_at": generated_at.isoformat(),
                "request_fingerprint": fingerprint,
                "extra": {"scene_count": str(scene_count)},
            },
            "scenes": scenes,
        }

    def _location(self, brief: EpisodeBrief, scene_index: int) -> str:
        return f"Location {scene_index}"

    def _action(self, brief: EpisodeBrief, present: list[str], framing: Framing) -> str:
        if not present:
            return f"An establishing view sets the scene in a {brief.visual_tone} register."
        names = self._names(brief, present)
        return f"{' and '.join(names)} drive the beat forward in a {framing.value.replace('_', ' ')} shot."

    def _dialogue_intent(self, present: list[str]) -> str:
        if not present:
            return ""
        return "Convey the emotional stakes of the moment without exposition."

    def _prompt(
        self,
        brief: EpisodeBrief,
        present: list[str],
        framing: Framing,
        location: str,
        action: str,
    ) -> str:
        parts = [
            f"{framing.value.replace('_', ' ')} shot",
            f"at {location}",
            f"visual tone: {brief.visual_tone}",
            action,
        ]
        for cid in present:
            char = next(c for c in brief.characters if c.id == cid)
            sig = char.visual_signature or char.description
            parts.append(f"{char.name}: {sig}")
        # Strip any trailing period from each fragment so the join doesn't double up.
        return ". ".join(p.rstrip(". ") for p in parts) + "."

    def _names(self, brief: EpisodeBrief, ids: list[str]) -> list[str]:
        by_id = {c.id: c.name for c in brief.characters}
        return [by_id[i] for i in ids]
