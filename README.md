# Competitor Review Miner Agent

Agent #3 in the OpenClaw SaaS Factory.

## Overview

- **Layer:** Discovery
- **Priority:** v2
- **Human Touch:** No

## Quick Start

```bash
pip install -r requirements.txt
AGENT_NAME="Competitor Review Miner" AGENT_ID=3 python runtime/main.py
```

## Structure

- `SKILL.md` — Agent specification
- `runtime/main.py` — OpenClaw-compatible runtime
- `data/inbox/` — Task manifests
- `data/outbox/` — Output artifacts
- `data/archive/` — Processed tasks
- `skills/` — Skill bindings

## License

Private — OpenClaw SaaS Factory
