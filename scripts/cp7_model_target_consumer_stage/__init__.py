"""Generated opt-in hook candidate; exact installer is not implemented yet."""
from pathlib import Path
import json
from . import render
ROOT=Path(__file__).resolve().parent


def verify_sources():
    if (ROOT/'hooks.sql').read_text()!=render.render()or json.loads((ROOT/'MANIFEST.json').read_text())!=render.manifest():
        raise ValueError('MODEL_TARGET_HOOK_SOURCE_CHANGED')
    return render.manifest()
