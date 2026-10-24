"""Source-only private prototype; no connection, installation or public caller."""
from pathlib import Path
from hashlib import sha256
import json

ROOT=Path(__file__).resolve().parent


def verify_sources():
    expected=json.loads((ROOT/'MANIFEST.json').read_text())
    sql=ROOT/'candidates.sql'
    if sha256(sql.read_bytes()).hexdigest()!=expected['sql_sha256']:
        raise ValueError('PRODUCT_ANALOG_PROTOTYPE_SOURCE_CHANGED')
    for name,digest in expected['dependency_files_sha256'].items():
        if sha256((ROOT.parent/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('PRODUCT_ANALOG_NATIVE_DEPENDENCY_CHANGED: '+name)
    return expected
