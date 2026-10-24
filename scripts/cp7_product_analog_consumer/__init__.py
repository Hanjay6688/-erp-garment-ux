"""Private source prototype only. No connection, installer or public caller."""
from pathlib import Path
from hashlib import sha256
import json
ROOT=Path(__file__).resolve().parent

def verify_sources():
    expected=json.loads((ROOT/'MANIFEST.json').read_text())
    for name,digest in expected['source_files_sha256'].items():
        if sha256((ROOT/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('ANALOG_CONSUMER_PROTOTYPE_CHANGED: '+name)
    for name,digest in expected['dependency_files_sha256'].items():
        if sha256((ROOT.parent/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('ANALOG_CONSUMER_DEPENDENCY_CHANGED: '+name)
    return expected
