# motion-foundry

Internal [Quantum Star](#) animation production tooling.

The long-term pipeline is **characters → storyboard → shots → voices → final
episode**. This repository currently implements the **storyboard stage** only,
end-to-end: it turns an episode brief into a validated, machine-readable
storyboard plus a human-readable version, ready to hand to the shot stage.

> Scope note: shot rendering, voices, video assembly, the full orchestrator, and
> a UI are intentionally **not** in this repository yet. This is the storyboard
> stage, lights on.

## What it does

**Input** — an episode brief (JSON):

- structured character definitions (id, name, role, description, visual signature)
- an episode premise
- a target duration and a visual tone
- an optional scene-count hint

**Output** — written to the chosen output directory:

- `storyboard.json` — a schema-validated storyboard: ordered scenes and shots,
  each shot carrying its character ids, action, framing, location, dialogue
  intent, estimated duration, and a self-contained generation prompt. Includes
  a `generation` block recording the backend, model, timestamp, and a
  fingerprint of the brief it was built from.
- `storyboard.md` — the same storyboard as a readable document.

It **fails closed**: a malformed brief or an invalid generated storyboard raises
and writes nothing, rather than emitting a degraded artifact.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

Convert the bundled fixture brief into a storyboard:

```bash
motion-foundry storyboard fixtures/pilot_episode.json --out-dir out
```

This writes:

- `out/storyboard.json`
- `out/storyboard.md`

The default backend is `fake` (deterministic, offline), so the command above
runs with no network access and produces byte-identical output on every run.

## Backends

Two backends, selected through configuration:

| Backend     | Purpose                                                         |
| ----------- | -------------------------------------------------------------- |
| `fake`      | Deterministic, offline. The default; used by the test suite.  |
| `anthropic` | Real generation via Claude (structured outputs).              |

Select a backend with the `--backend` flag or the `MOTION_FOUNDRY_BACKEND`
environment variable (the flag wins):

```bash
# Real backend via flag
motion-foundry storyboard fixtures/pilot_episode.json --out-dir out --backend anthropic

# Or via environment
export MOTION_FOUNDRY_BACKEND=anthropic
export MOTION_FOUNDRY_MODEL=claude-opus-5      # optional; defaults to claude-opus-5
motion-foundry storyboard fixtures/pilot_episode.json --out-dir out
```

The `anthropic` backend needs the `anthropic` package (installed with the `dev`
or `anthropic` extra) and resolves credentials the way the Anthropic SDK does
(`ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN` / an `ant auth login` profile).
Whatever the backend returns is validated against the same storyboard schema as
the fake backend — a hallucinated character id or malformed shot is rejected.

## Test

```bash
pytest
```

The suite runs entirely on the `fake` backend and needs no network access (one
test asserts this by blocking socket creation). The `anthropic` backend is
covered with an injected stub client, so those tests are offline too.

## Layout

```
src/motion_foundry/
  models.py                  Pydantic models for the brief and the storyboard
  storyboard.py              load brief → generate → validate → write
  render.py                  storyboard.md renderer
  config.py                  backend selection (flag / env / default)
  fingerprint.py             deterministic hash of a brief
  cli.py                     `motion-foundry` CLI (Click)
  backends/
    base.py                  backend contract
    fake.py                  deterministic offline backend
    anthropic_backend.py     real Claude backend
fixtures/pilot_episode.json  example brief
tests/                       pytest suite
```
