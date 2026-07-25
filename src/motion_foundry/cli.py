"""Command-line interface for the storyboard stage.

    motion-foundry storyboard BRIEF.json --out-dir out/

Converts an episode brief into a validated ``storyboard.json`` and a
human-readable ``storyboard.md``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
from pydantic import ValidationError

from . import __version__
from .config import available_backends, build_backend, resolve_backend_name
from .render import write_markdown
from .storyboard import (
    StoryboardValidationError,
    build_storyboard,
    load_brief,
    write_storyboard_json,
)


@click.group()
@click.version_option(__version__, prog_name="motion-foundry")
def cli() -> None:
    """motion-foundry — internal Quantum Star animation production tool."""


@cli.command()
@click.argument("brief", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--out-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("out"),
    show_default=True,
    help="Directory to write storyboard.json and storyboard.md into.",
)
@click.option(
    "--backend",
    type=click.Choice(available_backends()),
    default=None,
    help="Generation backend. Overrides MOTION_FOUNDRY_BACKEND. Defaults to 'fake'.",
)
def storyboard(brief: Path, out_dir: Path, backend: str | None) -> None:
    """Generate a storyboard from an episode BRIEF (JSON)."""
    try:
        episode = load_brief(brief)
    except ValidationError as exc:
        raise click.ClickException(f"invalid episode brief:\n{exc}") from exc
    except (OSError, ValueError) as exc:
        raise click.ClickException(f"could not read brief '{brief}': {exc}") from exc

    backend_name = resolve_backend_name(backend)
    click.echo(f"Backend: {backend_name}")

    try:
        adapter = build_backend(backend)
        board = build_storyboard(episode, adapter)
    except StoryboardValidationError as exc:
        raise click.ClickException(str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - surface backend/config failures cleanly
        raise click.ClickException(f"storyboard generation failed: {exc}") from exc

    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "storyboard.json"
    md_path = out_dir / "storyboard.md"
    write_storyboard_json(board, json_path)
    write_markdown(board, md_path)

    click.echo(
        f"Wrote {len(board.scenes)} scene(s), "
        f"{sum(len(s.shots) for s in board.scenes)} shot(s) "
        f"(~{round(board.total_estimated_duration_seconds)}s)."
    )
    click.echo(f"  {json_path}")
    click.echo(f"  {md_path}")


def main() -> int:
    try:
        cli.main(standalone_mode=False)
    except click.ClickException as exc:
        exc.show()
        return 1
    except click.Abort:
        click.echo("Aborted.", err=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
