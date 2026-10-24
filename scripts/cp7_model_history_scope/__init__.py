"""Source-only private scoped history; persistent runtime admission is separate."""
from pathlib import Path
from hashlib import sha256
import json
from . import render

ROOT = Path(__file__).resolve().parent


def sources():
    return {p.name:sha256(p.read_bytes()).hexdigest()for p in sorted(ROOT.iterdir())
            if p.is_file()and p.suffix in('.py','.sql','.json')}


def verify_sources():
    if (ROOT/'scope.sql').read_text()!=render.render() or json.loads((ROOT/'MANIFEST.json').read_text())!=render.manifest():
        raise ValueError('MODEL_HISTORY_SCOPE_SOURCE_CHANGED')
    return sources()
