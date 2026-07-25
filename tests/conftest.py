from __future__ import annotations

from pathlib import Path

import pytest

from motion_foundry import EpisodeBrief, load_brief

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


@pytest.fixture
def brief_path() -> Path:
    return FIXTURES / "pilot_episode.json"


@pytest.fixture
def brief(brief_path: Path) -> EpisodeBrief:
    return load_brief(brief_path)
