"""Deterministic fingerprinting of an episode brief.

The fingerprint is a stable hash over the brief's canonical JSON. It is stored in
the storyboard's generation metadata (so a storyboard can be traced back to the
exact input that produced it) and is used by the fake backend to seed its
deterministic generation.
"""

from __future__ import annotations

import hashlib
import json

from .models import EpisodeBrief


def brief_fingerprint(brief: EpisodeBrief) -> str:
    """Return a stable sha256 hex digest of the brief.

    Canonical JSON (sorted keys, no insignificant whitespace) guarantees the same
    brief always fingerprints identically, regardless of field ordering.
    """
    payload = brief.model_dump(mode="json")
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
