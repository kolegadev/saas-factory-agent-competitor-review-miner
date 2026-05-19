#!/usr/bin/env python3
"""
OpenClaw Agent Runtime — Workflow-driven skill execution.
Reads manifest from data/inbox/, resolves skills, executes workflow, writes artifacts.
Compatible with GitHub Actions one-shot mode.
"""
import os
import sys
import json
import shutil
import logging
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

AGENT_NAME = os.getenv('AGENT_NAME', 'unknown-agent')
AGENT_ID = int(os.getenv('AGENT_ID', '0'))
INBOX = Path('data/inbox')
OUTBOX = Path('data/outbox')
ARCHIVE = Path('data/archive')
STATE_DIR = Path('data/state')
STATE_FILE = Path('data/state.json')

sys.path.insert(0, str(Path(__file__).parent.parent / 'skills'))
from skill_resolver import execute_workflow


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text())


def write_artifact(name: str, payload: dict):
    out_path = OUTBOX / f"{int(datetime.now(timezone.utc).timestamp())}_{name}.json"
    out_path.write_text(json.dumps(payload, indent=2))
    logger.info(f"Wrote artifact: {out_path}")
    return str(out_path)


def save_state(status: str = 'idle', extra: dict = None):
    state = {}
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text())
    state['status'] = status
    state['last_run'] = datetime.now(timezone.utc).isoformat()
    state['runs'] = state.get('runs', 0) + 1
    if extra:
        state.update(extra)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def process_manifest(path: Path):
    logger.info(f"Processing manifest: {path}")
    save_state('running')
    manifest = load_manifest(path)
    workflow = manifest.get('workflow', manifest.get('task'))
    if isinstance(workflow, str):
        # Legacy: task name maps to a single-skill workflow
        workflow = {'steps': [{'skill': workflow, 'inputs': manifest.get('inputs', {})}]}
    if not workflow or not workflow.get('steps'):
        raise ValueError("Manifest has no workflow or steps")

    context = execute_workflow(workflow)
    output = {
        'agent': AGENT_NAME,
        'agent_id': AGENT_ID,
        'manifest_id': manifest.get('request_id', 'unknown'),
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'context': context,
    }
    artifact_path = write_artifact('output', output)

    # Archive manifest
    archive_path = ARCHIVE / path.name
    shutil.move(str(path), str(archive_path))
    logger.info(f"Archived manifest: {archive_path}")

    save_state('idle', {'last_artifact': artifact_path, 'last_manifest': str(path)})
    return output


def run():
    logger.info(f"Starting runtime for {AGENT_NAME} ({AGENT_ID})")
    for d in [INBOX, OUTBOX, ARCHIVE, STATE_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    manifests = sorted(INBOX.glob('*.json'))
    if not manifests:
        logger.info('No manifests in inbox')
        save_state('idle')
        return

    # Only process the most recent manifest to avoid long runs from accumulated files
    manifest = manifests[-1]
    logger.info(f'Processing latest manifest ({len(manifests)} total in inbox): {manifest.name}')
    try:
        process_manifest(manifest)
    except Exception as e:
        logger.error(f"Error processing {manifest}: {e}")
        save_state(f'error: {str(e)[:50]}')
        raise

    logger.info('One-shot execution complete')


if __name__ == '__main__':
    run()
