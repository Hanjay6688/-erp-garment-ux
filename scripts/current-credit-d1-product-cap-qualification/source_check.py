"""File-only bounded quote successor; no runtime import, DB or Git required."""
from pathlib import Path
from hashlib import sha256
import json
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OWNING = 'scripts/cp7_credit_correction_de/owning.sql'
QUOTE = 'cp7_credit_correction_de.quote_v1'


def function(text, name):
    start = text.index('create function ' + name + '(')
    end = text.index('$$;', text.index('$$', start) + 2) + 3
    return text[start:end]


def quote_scope(before, current):
    if before.replace(function(before, QUOTE), '') != current.replace(function(current, QUOTE), ''):
        raise ValueError('D1_PRODUCT_CAP_OTHER_OWNING_BODY_CHANGED')
    if len(re.findall(r'^create function ', current, re.M)) != 14:
        raise ValueError('D1_PRODUCT_CAP_OWNING_FUNCTION_SET_CHANGED')
    return dict(changed_functions=[QUOTE], other_owning_function_bodies_byte_exact=13)


def admitted():
    source = json.loads((HERE / 'SOURCE.json').read_bytes())
    assert source['base_tree'] == '6f931e639bd8996378ff65b8a7be2a1ed8590b45'
    for path, pin in source['files'].items():
        raw = (ROOT / path).read_bytes()
        if len(raw) != pin['bytes'] or sha256(raw).hexdigest() != pin['sha256']:
            raise ValueError('D1_PRODUCT_CAP_SOURCE_CHANGED:' + path)
    parent = json.loads((HERE / 'PARENT.json').read_bytes())
    before = (HERE / 'retained/owning.before.sql').read_bytes()
    assert sha256(before).hexdigest() == parent['business_leaves'][OWNING]
    scope = quote_scope(before.decode(), (ROOT / OWNING).read_text())
    for path, expected in parent['business_leaves'].items():
        if path != OWNING:
            assert sha256((ROOT / path).read_bytes()).hexdigest() == expected, path
    for path, expected in parent['frozen_qualifier_files'].items():
        assert sha256((ROOT / path).read_bytes()).hexdigest() == expected, path
    return dict(status='PASS_BOUNDED_QUOTE_SOURCE_ONLY', scope=scope, other_business_leaves_byte_exact=8,
        original_Native13_qualifier_files_unchanged=len(parent['frozen_qualifier_files']),
        source_files=len(source['files']), Native_execution=False, production_go=False, independent_acceptance=False)


if __name__ == '__main__':
    print(json.dumps(admitted(), indent=2))
