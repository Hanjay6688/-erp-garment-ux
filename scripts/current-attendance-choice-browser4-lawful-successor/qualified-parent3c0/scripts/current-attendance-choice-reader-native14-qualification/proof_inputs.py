"""Materialize only four immutable historical inputs, never overwrite them."""
from pathlib import Path
from hashlib import sha256
import gzip
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
HISTORICAL = 'docs/cp7/d17-14/ow08/vendor-combined41c-pass'


def documents(here=HERE):
    cfg = json.loads((here / 'CONFIG.json').read_bytes())
    result = {}
    for name, pin in cfg['retained41c'].items():
        packed = (here / 'retained41c' / (name + '.gz')).read_bytes()
        if len(packed) != pin['gzip_bytes'] or sha256(packed).hexdigest() != pin['gzip_sha256']:
            raise ValueError('S03_NATIVE11_HISTORICAL_GZIP_CHANGED:' + name)
        raw = gzip.decompress(packed)
        if len(raw) != pin['bytes'] or sha256(raw).hexdigest() != pin['sha256']:
            raise ValueError('S03_NATIVE11_HISTORICAL_RAW_CHANGED:' + name)
        result[name] = dict(compressed=packed, raw=raw, document=json.loads(raw))
    if len(result) != 4:
        raise ValueError('S03_NATIVE11_EXACT_FOUR_HISTORICAL_INPUTS_REQUIRED')
    return result


def materialize(root=ROOT, here=HERE):
    checked = documents(here)
    destination = root / HISTORICAL
    # Validate ALL existing targets before creating any missing target.
    for name, value in checked.items():
        target = destination / (name + '.gz')
        if target.exists() and target.read_bytes() != value['compressed']:
            raise ValueError('S03_NATIVE11_EXISTING_HISTORICAL_INPUT_CHANGED:' + name)
    destination.mkdir(parents=True, exist_ok=True)
    created, preserved = [], []
    for name, value in checked.items():
        target = destination / (name + '.gz')
        if target.exists():
            preserved.append(str(target.relative_to(root)))
            continue
        # Exclusive creation also refuses an unexpected concurrent writer.
        with target.open('xb') as stream:
            stream.write(value['compressed'])
        created.append(str(target.relative_to(root)))
    return dict(classification='EXACT_UNTRACKED_HISTORICAL_PROOF_INPUTS_ONLY',
        created=created, exact_existing_preserved=preserved, overwritten=[],
        new_S03_Native_credit=0, D1_failed_runtime_is_prerequisite=False)
