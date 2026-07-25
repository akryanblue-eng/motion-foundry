"""Human-readable storyboard rendering (Markdown)."""

from __future__ import annotations

from pathlib import Path

from .models import Storyboard

_FRAMING_LABELS = {
    "establishing": "Establishing",
    "extreme_wide": "Extreme wide",
    "wide": "Wide",
    "full": "Full",
    "medium": "Medium",
    "medium_close_up": "Medium close-up",
    "close_up": "Close-up",
    "extreme_close_up": "Extreme close-up",
    "over_the_shoulder": "Over-the-shoulder",
    "pov": "POV",
    "two_shot": "Two-shot",
    "insert": "Insert",
}


def _fmt_duration(seconds: float) -> str:
    total = round(seconds)
    minutes, secs = divmod(total, 60)
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def render_markdown(storyboard: Storyboard) -> str:
    """Render a storyboard to a human-readable Markdown document."""
    lines: list[str] = []
    gen = storyboard.generation

    lines.append(f"# {storyboard.episode_title}")
    lines.append("")
    lines.append(f"> {storyboard.premise}")
    lines.append("")
    lines.append(f"- **Visual tone:** {storyboard.visual_tone}")
    lines.append(f"- **Target duration:** {_fmt_duration(storyboard.target_duration_seconds)}")
    lines.append(
        f"- **Storyboard duration:** {_fmt_duration(storyboard.total_estimated_duration_seconds)} "
        f"across {len(storyboard.scenes)} scene(s)"
    )
    lines.append(f"- **Backend / model:** {gen.backend} / {gen.model}")
    lines.append(f"- **Generated at:** {gen.generated_at.isoformat()}")
    lines.append(f"- **Brief fingerprint:** `{gen.request_fingerprint}`")
    lines.append("")

    lines.append("## Characters")
    lines.append("")
    for c in storyboard.characters:
        sig = f" — _{c.visual_signature}_" if c.visual_signature else ""
        lines.append(f"- **{c.name}** (`{c.id}`, {c.role}): {c.description}{sig}")
    lines.append("")

    for scene_index, scene in enumerate(storyboard.scenes, start=1):
        scene_seconds = sum(s.estimated_duration_seconds for s in scene.shots)
        lines.append(f"## Scene {scene_index}: {scene.title}")
        lines.append("")
        lines.append(f"- **Location:** {scene.location}")
        lines.append(f"- **Duration:** {_fmt_duration(scene_seconds)} ({len(scene.shots)} shot(s))")
        lines.append("")
        lines.append(f"{scene.summary}")
        lines.append("")
        for shot_index, shot in enumerate(scene.shots, start=1):
            cast = ", ".join(shot.character_ids) if shot.character_ids else "—"
            framing = _FRAMING_LABELS.get(shot.framing.value, shot.framing.value)
            lines.append(f"### Shot {scene_index}.{shot_index} · {framing}")
            lines.append("")
            lines.append(f"- **Duration:** {_fmt_duration(shot.estimated_duration_seconds)}")
            lines.append(f"- **Cast:** {cast}")
            lines.append(f"- **Location:** {shot.location}")
            lines.append(f"- **Action:** {shot.action}")
            lines.append(
                f"- **Dialogue intent:** {shot.dialogue_intent}" if shot.dialogue_intent
                else "- **Dialogue intent:** (silent)"
            )
            lines.append(f"- **Generation prompt:** {shot.generation_prompt}")
            lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


def write_markdown(storyboard: Storyboard, path: str | Path) -> None:
    Path(path).write_text(render_markdown(storyboard), encoding="utf-8")
