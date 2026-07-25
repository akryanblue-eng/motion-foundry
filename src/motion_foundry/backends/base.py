"""Backend adapter contract for storyboard generation.

A backend turns an :class:`EpisodeBrief` into a *raw* storyboard payload (a plain
dict). The orchestrator (:func:`motion_foundry.storyboard.build_storyboard`) is
solely responsible for validating that payload against the
:class:`~motion_foundry.models.Storyboard` schema. Keeping generation and
validation separate is what lets us "fail closed on invalid generated output":
the fake backend and the real backend are held to the exact same bar.
"""

from __future__ import annotations

import abc

from ..models import EpisodeBrief


class StoryboardBackendError(RuntimeError):
    """Raised when a backend cannot produce a payload (network, auth, parse, ...)."""


class StoryboardBackend(abc.ABC):
    """Produces a raw storyboard payload for a brief.

    Subclasses set ``name`` (adapter name) and ``model`` (model identifier) and
    implement :meth:`generate`, returning a dict that the orchestrator validates.
    Implementations must populate a ``generation`` block with ``backend``,
    ``model``, ``generated_at`` and ``request_fingerprint``.
    """

    #: Short adapter name recorded in generation metadata, e.g. "fake".
    name: str = "base"
    #: Model identifier recorded in generation metadata.
    model: str = "unknown"

    @abc.abstractmethod
    def generate(self, brief: EpisodeBrief) -> dict:
        """Return a raw (unvalidated) storyboard payload for ``brief``."""
        raise NotImplementedError
