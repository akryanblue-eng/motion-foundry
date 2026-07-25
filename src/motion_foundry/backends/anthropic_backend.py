"""Real generation backend: Anthropic Claude.

Asks Claude to break the episode brief into ordered scenes and shots, constrained
to a JSON schema via structured outputs. The model only produces the creative
payload (``scenes``); the deterministic fields (title, premise, characters,
generation metadata) are assembled here from the brief. The orchestrator then
validates the whole thing against the full ``Storyboard`` schema — including
character-id referential integrity, which the JSON schema alone cannot express —
so a hallucinated character id or malformed shot fails closed.

Credentials are resolved by the Anthropic SDK from the environment
(``ANTHROPIC_API_KEY`` / ``ANTHROPIC_AUTH_TOKEN`` / an ``ant auth login`` profile);
this adapter never handles keys directly.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from ..fingerprint import brief_fingerprint
from ..models import SCHEMA_VERSION, EpisodeBrief, Framing
from .base import StoryboardBackend, StoryboardBackendError

DEFAULT_MODEL = "claude-opus-5"

_SYSTEM_PROMPT = (
    "You are a storyboard supervisor for Quantum Star, an internal animation "
    "production tool. Given an episode brief, break the premise into an ordered "
    "sequence of scenes, each containing ordered shots. Respect the target "
    "duration: the sum of every shot's estimated_duration_seconds should land "
    "close to the target. Use only the character ids provided in the brief; never "
    "invent new ids. dialogue_intent describes the purpose of any dialogue, not "
    "verbatim lines — use an empty string for silent shots. Each generation_prompt "
    "must be a self-contained visual description a downstream image/video model "
    "could render without seeing the rest of the storyboard, and must reflect the "
    "requested visual tone."
)


def _output_schema() -> dict:
    """JSON schema for the model's creative payload (scenes only).

    Kept within structured-outputs limits (no length/numeric constraints; every
    object sets additionalProperties=false and lists required fields).
    """
    framing_values = [f.value for f in Framing]
    shot = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "id": {"type": "string"},
            "character_ids": {"type": "array", "items": {"type": "string"}},
            "action": {"type": "string"},
            "framing": {"type": "string", "enum": framing_values},
            "location": {"type": "string"},
            "dialogue_intent": {"type": "string"},
            "estimated_duration_seconds": {"type": "number"},
            "generation_prompt": {"type": "string"},
        },
        "required": [
            "id",
            "character_ids",
            "action",
            "framing",
            "location",
            "dialogue_intent",
            "estimated_duration_seconds",
            "generation_prompt",
        ],
    }
    scene = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "id": {"type": "string"},
            "title": {"type": "string"},
            "location": {"type": "string"},
            "summary": {"type": "string"},
            "shots": {"type": "array", "items": shot},
        },
        "required": ["id", "title", "location", "summary", "shots"],
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {"scenes": {"type": "array", "items": scene}},
        "required": ["scenes"],
    }


class AnthropicStoryboardBackend(StoryboardBackend):
    """Generates a storyboard by prompting Claude with structured outputs."""

    name = "anthropic"

    def __init__(self, model: str = DEFAULT_MODEL, max_tokens: int = 16000, client=None):
        self.model = model
        self.max_tokens = max_tokens
        self._client = client

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - exercised only without the dep
            raise StoryboardBackendError(
                "the 'anthropic' package is required for the anthropic backend; "
                "install it with `pip install anthropic`"
            ) from exc
        self._client = anthropic.Anthropic()
        return self._client

    def generate(self, brief: EpisodeBrief) -> dict:
        client = self._get_client()
        user_prompt = self._user_prompt(brief)

        try:
            response = client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=_SYSTEM_PROMPT,
                output_config={"format": {"type": "json_schema", "schema": _output_schema()}},
                messages=[{"role": "user", "content": user_prompt}],
            )
        except Exception as exc:  # noqa: BLE001 - surface any SDK/transport error uniformly
            raise StoryboardBackendError(f"Anthropic request failed: {exc}") from exc

        if getattr(response, "stop_reason", None) == "refusal":
            raise StoryboardBackendError("Anthropic declined the request (stop_reason=refusal)")

        text = next((b.text for b in response.content if getattr(b, "type", None) == "text"), None)
        if not text:
            raise StoryboardBackendError("Anthropic response contained no text block")

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise StoryboardBackendError(f"Anthropic returned invalid JSON: {exc}") from exc

        scenes = payload.get("scenes")
        if not isinstance(scenes, list):
            raise StoryboardBackendError("Anthropic payload is missing a 'scenes' array")

        request_id = getattr(response, "_request_id", None)
        extra = {"request_id": request_id} if request_id else {}

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
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "request_fingerprint": brief_fingerprint(brief),
                "extra": extra,
            },
            "scenes": scenes,
        }

    def _user_prompt(self, brief: EpisodeBrief) -> str:
        lines = [
            f"Episode title: {brief.title}",
            f"Target duration (seconds): {brief.target_duration_seconds}",
            f"Visual tone: {brief.visual_tone}",
        ]
        if brief.scene_count:
            lines.append(f"Requested scene count: {brief.scene_count}")
        lines.append("")
        lines.append("Premise:")
        lines.append(brief.premise)
        lines.append("")
        lines.append("Characters (use these ids exactly):")
        for c in brief.characters:
            sig = f" | visual: {c.visual_signature}" if c.visual_signature else ""
            lines.append(f"- id={c.id} | name={c.name} | role={c.role} | {c.description}{sig}")
        lines.append("")
        lines.append(
            "Produce the storyboard as JSON matching the required schema: an object "
            "with a 'scenes' array. Give scenes and shots stable lowercase ids "
            "(letters, digits, underscores)."
        )
        return "\n".join(lines)
