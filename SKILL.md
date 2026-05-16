# Agent #3 — Competitor Review Miner

**Layer:** Discovery  
**Priority:** v2  
**Human Touch:** No  

## Role

Automated agent in the OpenClaw SaaS Factory portfolio system.

## Inputs

- Task manifests from `data/inbox/`
- Shared state from portfolio-level context

## Workflow

1. Read manifest from `data/inbox/`
2. Execute task logic
3. Write artifacts to `data/outbox/`
4. Update `data/state.json`

## Outputs

- Structured JSON artifacts in `data/outbox/`
- State updates for downstream agents

## 🛑 Human Escalation Points

- Ambiguous inputs requiring judgment
- Threshold breaches
- First 20–30 calibration decisions

## Runtime

```bash
python runtime/main.py
```

## Directory Structure

```
data/
  inbox/     # Incoming task manifests
  outbox/    # Outgoing artifacts
  archive/   # Processed manifests
runtime/
  main.py    # Agent runtime skeleton
skills/
  # Layer-specific skill bindings
```
