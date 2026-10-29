"""Exact retained vendor11/package is mandatory; no network or Git reads."""
from hashlib import sha256
from pathlib import Path
import gzip
import importlib.util
import json

VERIFIER = 'scripts/current-vendor-integration-source/check.py'
VERIFIER_SHA256 = '78ad89e2a0e9433c3acedd5ad0d081799ef3b3fb8fdd7cc5a38f64877591d65a'
RUNTIME = ('scripts/cp7_vendor_receivable/receivable.sql', 'scripts/cp7_vendor_receivable/native_delta.py', 'scripts/cp7_vendor_receivable/composition.py')
PACKAGE_GATES = ('installed', 'primary_unchanged', 'backup_restore_drill', 'security_advisors', 'writer_runtime')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def checked(repo, pin, original, package, runtime_files, parent_digest):
    if pin is None:
        raise ValueError('S05_VENDOR11_ACTUAL_ORIGINAL_AND_PACKAGE_REQUIRED')
    # This verifier was admitted by A for the real vendor41c result. Importing
    # it is inert. Only admit() is called; its separate Git-based source checker
    # is never invoked by this qualifier.
    path = Path(repo)/VERIFIER
    if sha256(path.read_bytes()).hexdigest() != VERIFIER_SHA256:
        raise ValueError('S05_FROZEN_VENDOR11_VERIFIER_CHANGED')
    spec = importlib.util.spec_from_file_location('s05_frozen_vendor11_verifier', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    proof = module.admit(pin, original, package, runtime_files, parent_digest)
    actual, pkg = json.loads(original), json.loads(package)
    if actual['focused_preuse_removal']['used_guard_before_DDL'] is not True:
        raise ValueError('S05_VENDOR11_PREUSE_INVERSE_REQUIRED')
    if pkg.get('gate') != {key: True for key in PACKAGE_GATES}:
        raise ValueError('S05_VENDOR11_ALL_FIVE_PACKAGE_GATES_REQUIRED')
    return dict(status=proof['status'], head=proof['head'], retained_Native_cases=proof['fresh_Native'],
                retained_races=proof['fresh_races'], retained_Auth_HTTP=proof['fresh_Auth_HTTP'], retained_browser=proof['fresh_browser'],
                retained_only=True, reexecuted=False, fresh_S05_runtime_credit=0,
                original_sha256=sha256(original).hexdigest(), package_sha256=sha256(package).hexdigest())


def retained(repo, config, current=None):
    repo = Path(repo)
    pin = config.get('qualified_vendor11')
    if pin is None:
        raise ValueError('S05_VENDOR11_ACTUAL_ORIGINAL_AND_PACKAGE_REQUIRED')
    raw = {kind: gzip.decompress((repo/pin[kind]['path']).read_bytes()) for kind in ('original', 'package')}
    runtime_files = {path: sha256((repo/path).read_bytes()).hexdigest() for path in RUNTIME}
    parent_digest = config['backend3194_sha256']
    if current is not None:
        if current['files'] != runtime_files:
            raise ValueError('S05_OTHER_VENDOR_RUNTIME_REFUSED')
        if sha256(canonical(current['predecessor'])).hexdigest() != parent_digest:
            raise ValueError('S05_OTHER_BACKEND3194_REFUSED')
    proof = checked(repo, pin, raw['original'], raw['package'], runtime_files, parent_digest)
    actual = json.loads(raw['original'])
    # Bind the exact engine bytes to what the real parent result declared.
    declarations = actual['source_declaration']['qualification']['files']
    for local, old in config['frozen_vendor_files'].items():
        b = (repo/local).read_bytes()
        if sha256(b).hexdigest() != declarations[old]:
            raise ValueError('S05_FROZEN_VENDOR_SOURCE_NOT_DECLARED_BY_ORIGINAL: '+old)
    return proof
