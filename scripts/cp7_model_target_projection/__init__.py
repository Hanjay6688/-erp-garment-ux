"""Private target arithmetic only; no model admission or caller installation."""
from pathlib import Path
from hashlib import sha256
import json
ROOT=Path(__file__).resolve().parent


def verify_sources():
    manifest=json.loads((ROOT/'MANIFEST.json').read_text())
    for name,digest in manifest['source_files_sha256'].items():
        if sha256((ROOT/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('MODEL_TARGET_SOURCE_CHANGED: '+name)
    for name,digest in manifest['dependency_files_sha256'].items():
        if sha256((ROOT.parent/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('MODEL_TARGET_DEPENDENCY_CHANGED: '+name)
    return manifest
