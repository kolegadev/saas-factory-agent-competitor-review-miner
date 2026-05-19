"""
Skill Resolver — dynamically loads and executes skills from the local skills/ directory.
Falls back to ClawHub public API for skill discovery and download.
Skills are Python modules with a run(inputs: dict) -> dict function.
"""
import importlib.util
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

SKILLS_DIR = Path(__file__).parent
CLAWHUB_BASE = os.getenv('CLAWHUB_REGISTRY', 'https://clawhub.ai')


def clawhub_api_get(path: str):
    """Fetch JSON from ClawHub public API."""
    url = f"{CLAWHUB_BASE}{path}"
    req = urllib.request.Request(url, headers={
        'Accept': 'application/json',
        'User-Agent': 'openclaw-agent-runtime/1.0',
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"[clawhub] API error: {e}")
        return None


def download_skill(slug: str) -> bool:
    """Download a skill from ClawHub and save it to the local skills/ directory.
    Returns True if successful.
    """
    print(f"[clawhub] Resolving skill '{slug}' from ClawHub...")

    # Fetch skill metadata
    meta = clawhub_api_get(f"/api/v1/skills/{slug}")
    if not meta:
        print(f"[clawhub] Skill '{slug}' not found on ClawHub")
        return False

    version = meta.get('latestVersion') or meta.get('versions', [{}])[0].get('version', 'latest')
    download_url = f"{CLAWHUB_BASE}/api/v1/download?slug={slug}&version={version}"

    print(f"[clawhub] Downloading {slug} v{version}...")

    req = urllib.request.Request(download_url, headers={
        'User-Agent': 'openclaw-agent-runtime/1.0',
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read()
    except Exception as e:
        print(f"[clawhub] Download failed: {e}")
        return False

    # Save as zip file first (ClawHub serves skills as zips)
    zip_path = SKILLS_DIR / f"{slug}.zip"
    zip_path.write_bytes(content)
    print(f"[clawhub] Saved zip: {zip_path}")

    # Try to extract SKILL.md or main skill file from zip
    try:
        import zipfile
        with zipfile.ZipFile(zip_path, 'r') as zf:
            namelist = zf.namelist()
            # Look for .py files in the archive
            py_files = [n for n in namelist if n.endswith('.py') and not n.startswith('__')]
            skill_md = [n for n in namelist if n.lower().endswith('skill.md')]

            if py_files:
                # Extract the first non-init .py file as the skill module
                skill_py = py_files[0]
                target_name = slug.replace('-', '_') + '.py'
                target_path = SKILLS_DIR / target_name
                with zf.open(skill_py) as src, open(target_path, 'wb') as dst:
                    dst.write(src.read())
                print(f"[clawhub] Extracted skill module: {target_path}")
            elif skill_md:
                # If only SKILL.md, save it for reference
                target_path = SKILLS_DIR / f"{slug.replace('-', '_')}_SKILL.md"
                with zf.open(skill_md[0]) as src, open(target_path, 'wb') as dst:
                    dst.write(src.read())
                print(f"[clawhub] Extracted SKILL.md: {target_path}")
            else:
                print(f"[clawhub] No Python files or SKILL.md found in archive")
                return False
    except Exception as e:
        print(f"[clawhub] Extraction failed: {e}")
        return False
    finally:
        # Clean up zip
        zip_path.unlink(missing_ok=True)

    return True


def resolve_skill(skill_id: str):
    """Load a skill module by ID and return its run function.
    Falls back to ClawHub if the skill is not found locally.
    """
    module_name = skill_id.replace('-', '_')
    file_path = SKILLS_DIR / f"{module_name}.py"

    # Try local first
    if not file_path.exists():
        # Attempt to download from ClawHub
        success = download_skill(skill_id)
        if not success or not file_path.exists():
            raise FileNotFoundError(f"Skill '{skill_id}' not found locally or on ClawHub")

    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if not spec or not spec.loader:
        raise ImportError(f"Cannot load spec for skill '{skill_id}'")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    if not hasattr(module, 'run'):
        raise AttributeError(f"Skill '{skill_id}' has no run() function")
    return module.run


def execute_workflow(workflow: dict, context: dict = None) -> dict:
    """
    Execute a workflow defined as a list of steps.
    Each step: { skill: str, inputs: dict }
    Inputs can reference previous step outputs via {{steps.N.key}}
    Returns the final context with all step outputs.
    """
    context = context or {}
    steps = workflow.get('steps', [])
    for idx, step in enumerate(steps):
        skill_id = step.get('skill')
        if not skill_id:
            raise ValueError(f"Step {idx} missing 'skill'")
        raw_inputs = step.get('inputs', {})
        inputs = resolve_placeholders(raw_inputs, context)
        print(f"[workflow] Step {idx}: running skill '{skill_id}'")
        run_fn = resolve_skill(skill_id)
        outputs = run_fn(inputs)
        context[f"step_{idx}"] = outputs
        context['last_output'] = outputs
    return context


def resolve_placeholders(obj, context):
    """Replace {{steps.N.key}} placeholders with actual values from context."""
    if isinstance(obj, str):
        import re
        match = re.match(r'^\{\{steps\.(\d+)\.(.+)\}\}$', obj.strip())
        if match:
            step_idx = int(match.group(1))
            key = match.group(2)
            step_output = context.get(f"step_{step_idx}", {})
            return step_output.get(key, obj)
        return obj
    if isinstance(obj, list):
        return [resolve_placeholders(item, context) for item in obj]
    if isinstance(obj, dict):
        return {k: resolve_placeholders(v, context) for k, v in obj.items()}
    return obj
