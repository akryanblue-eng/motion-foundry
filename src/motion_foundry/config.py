"""Backend selection via configuration.

The backend can be chosen through configuration rather than code: an explicit
argument (the CLI's ``--backend`` flag) takes precedence, otherwise the
``MOTION_FOUNDRY_BACKEND`` environment variable, otherwise the default (``fake``,
so the tool runs offline out of the box). The model for the real backend is read
from ``MOTION_FOUNDRY_MODEL`` when set.
"""

from __future__ import annotations

import os

from .backends.base import StoryboardBackend

DEFAULT_BACKEND = "fake"
_BACKEND_ENV = "MOTION_FOUNDRY_BACKEND"
_MODEL_ENV = "MOTION_FOUNDRY_MODEL"


def available_backends() -> list[str]:
    return ["fake", "anthropic"]


def resolve_backend_name(explicit: str | None = None) -> str:
    """Resolve the backend name: explicit arg > env var > default."""
    name = explicit or os.environ.get(_BACKEND_ENV) or DEFAULT_BACKEND
    return name.strip().lower()


def build_backend(explicit: str | None = None) -> StoryboardBackend:
    """Construct the configured backend instance."""
    name = resolve_backend_name(explicit)

    if name == "fake":
        from .backends.fake import FakeStoryboardBackend

        return FakeStoryboardBackend()

    if name == "anthropic":
        from .backends.anthropic_backend import DEFAULT_MODEL, AnthropicStoryboardBackend

        model = os.environ.get(_MODEL_ENV, DEFAULT_MODEL)
        return AnthropicStoryboardBackend(model=model)

    raise ValueError(
        f"unknown backend '{name}'; available backends: {', '.join(available_backends())}"
    )
