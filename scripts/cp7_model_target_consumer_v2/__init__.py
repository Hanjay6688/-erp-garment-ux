"""Private versioned model consumer; caller integration is a separate stage."""
from pathlib import Path
from hashlib import sha256
import json
from .render import render
ROOT = Path(__file__).resolve().parent


def verify_sources():
    manifest = json.loads((ROOT/'MANIFEST.json').read_text())
    assert (ROOT/'consumer.sql').read_text()==render(), 'MODEL_CONSUMER_V2_RENDER_CHANGED'
    for name,digest in manifest['source_files_sha256'].items():
        assert sha256((ROOT/name).read_bytes()).hexdigest()==digest, 'MODEL_CONSUMER_V2_SOURCE_CHANGED: '+name
    for name,digest in manifest['dependency_files_sha256'].items():
        assert sha256((ROOT.parent/name).read_bytes()).hexdigest()==digest, 'MODEL_CONSUMER_V2_DEPENDENCY_CHANGED: '+name
    return manifest
