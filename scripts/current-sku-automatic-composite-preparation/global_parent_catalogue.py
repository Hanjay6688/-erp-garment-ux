"""Retain Global's exact parent catalogue from the existing owning SKU run."""
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from types import ModuleType
import ast
import os
import re

ROOT = Path(__file__).resolve().parents[2]
PROVIDERS = ROOT / 'scripts/cp7_global_nonpo_envelope'
SOURCE_PINS = {
    'composition.py': (21891, 'aa5139dcc0a87445e4fbecd1af0aca9cdf70b9e53b5a6be523aebe86d38029e4'),
    'catalogue_profile.py': (4607, 'e34234eab2e4c36f8c63742a504569f954957241c0cbc679e9b420d12218b19e'),
}
ORIGINAL = 'SKU_GLOBAL_PARENT_ACTUAL_FULL25.json'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def exact_readers():
    verified = {}
    for name, (size, digest) in SOURCE_PINS.items():
        path = PROVIDERS / name
        require(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents)),
                'SKU_GLOBAL_REGULAR_REVIEWED_READER_REQUIRED:' + name)
        raw = path.read_bytes()
        require((len(raw), sha256(raw).hexdigest()) == (size, digest), 'SKU_GLOBAL_EXACT_REVIEWED_READER_REQUIRED:' + name)
        verified[name] = raw
    profile = ModuleType('sku_exact_global_catalogue_queries')
    profile.__file__ = str(PROVIDERS / 'catalogue_profile.py')
    exec(compile(verified['catalogue_profile.py'], profile.__file__, 'exec', dont_inherit=True), profile.__dict__)
    groups = profile.queries()
    require(len(groups) == 25 and set(profile.EXTRA) == {'operators', 'casts', 'languages'},
            'SKU_GLOBAL_COMPLETE_REVIEWED_TWENTY_FIVE_GROUPS_REQUIRED')
    path = PROVIDERS / 'composition.py'
    names = {'metadata_context', 'capture', 'fingerprint'}
    selected = [node for node in ast.parse(verified['composition.py']).body
                if isinstance(node, ast.FunctionDef) and node.name in names]
    require(len(selected) == len(names) and {node.name for node in selected} == names,
            'SKU_GLOBAL_EXACT_CAPTURE_AND_FINGERPRINT_FUNCTIONS_REQUIRED')
    namespace = dict(contextmanager=contextmanager, sha256=sha256, catalogue_profile=profile)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), 'exec', dont_inherit=True), namespace)
    return namespace['capture'], namespace['fingerprint'], set(groups)


def bind(exercise, originals):
    capture, fingerprint, groups = exact_readers()

    def run(conn, cursor, database, url, report, state):
        require(conn.info.host in ('127.0.0.1', 'localhost') and conn.info.port == 54322
                and not conn.autocommit and cursor.connection is conn,
                'SKU_GLOBAL_EXISTING_DISPOSABLE_OWNER_CONNECTION_REQUIRED')
        head, run_id, attempt = (os.environ.get(name, '') for name in ('GITHUB_SHA', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT'))
        require(re.fullmatch('[a-f0-9]{40}', head) and re.fullmatch('[1-9][0-9]*', run_id) and attempt == '1',
                'SKU_GLOBAL_EXACT_OWNING_FIRST_ATTEMPT_REQUIRED')
        require(cursor.execute('select current_database()').fetchone() == ('cp6_rollback',),
                'SKU_GLOBAL_FIXED_DISPOSABLE_DATABASE_REQUIRED')
        value = capture(cursor)
        require(set(value) == groups, 'SKU_GLOBAL_ACTUAL_FULL25_REQUIRED')
        fingerprint_pin = fingerprint(cursor, value)
        require(fingerprint_pin['groups'] == len(value)
                and fingerprint_pin['counts'] == {name: len(rows) for name, rows in value.items()},
                'SKU_GLOBAL_SAME_CAPTURE_FINGERPRINT_REQUIRED')
        output = ROOT / 'cp6-proof/t3' / ORIGINAL
        output.parent.mkdir(parents=True, exist_ok=True)
        original = originals.save_sorted(output, value, 'SKU_GLOBAL_ACTUAL_CATALOGUE_ORIGINAL_CONFLICT')
        report['Global_parent_catalogue'] = dict(status='ACTUAL_FULL25_SKU_CATALOGUE_OBSERVED',
            head=head, run_id=run_id, attempt=1, original=original, fingerprint=fingerprint_pin,
            readers={name: dict(bytes=size, sha256=digest) for name, (size, digest) in SOURCE_PINS.items()},
            actual_ERP_case_credit=0, complete_input_review=False, production_go=False)
        return exercise(conn, cursor, database, url, report, state)

    return run
