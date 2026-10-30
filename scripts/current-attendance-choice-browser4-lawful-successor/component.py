"""Actual S03 product above unchanged Source6 physical browser-copy bridge."""
from pathlib import Path
from hashlib import sha256
from contextlib import contextmanager
import gzip
import importlib.util
import json
import os
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CASE = 'S03_MOUNTED_FULL_APP_AUTH_BROWSER4'


@contextmanager
def actual_catalog_environment(digest):
    key = 'S03_BROWSER_EXPECTED_CATALOG_SHA256'
    previous = os.environ.get(key)
    os.environ[key] = digest
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = previous


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def exercise(conn, cur, database, url, report, state):
    proof = load('s03_browser4_component_source_first', HERE / 'source_guard.py').admitted()
    loader = load('s03_browser4_component_actual_backend', HERE / 'backend_runtime.py')
    with loader.actual_backend(proof) as product:
        return actual_browser(conn, cur, report, state, proof, product)


def actual_browser(conn, cur, report, state, proof, product):
    # Admission has already read exact terminal Native14/full5/full-restore originals.
    import cp6_auditor_modes as modes
    from cp7_p21_current_chain_rehearsal_probe import helper
    if product.sources() != proof['current_installation'] or state['sources'] != product.sources():
        raise ValueError('S03_BROWSER4_ACTUAL_INSTALLED_PRODUCT_SOURCE_REQUIRED')
    if len(state['originals']) != 15 or len(state['definitions']) != 15 or len(state['clones']) != 2:
        raise ValueError('S03_BROWSER4_ACTUAL15_CAPTURE_AND_TWO_CLONES_REQUIRED')
    # The actual canonical15-capture/two-clone installer must be verified
    # before the browser-copy bridge can create any fixture.
    from cp7_attendance_period_choice import native_delta
    if (set(state['originals']) != set(native_delta.SIGNATURES)
            or state['definitions'] != native_delta.patched(state['originals'])
            or state['clones'] != native_delta.clones(state['originals'])):
        raise ValueError('S03_BROWSER4_EXACT_CANONICAL15_PLUS2_INSTALLER_REQUIRED')
    with helper.control.product_catalog(cur):
        report['canonical_qualified15_installed_proof'] = product.verify(cur, state)
    bridge = load('s03_browser4_frozen_ui_copy_bridge', ROOT / 'scripts/current-attendance-choice-mount-ui/browser_adapter.py')
    adapter = load('s03_browser4_unchanged_physical_copy_authority', ROOT / 'scripts/ow04-payment-current-qualification/copy_authority.py')
    temp = Path(tempfile.gettempdir())
    before_host_reports = set(temp.glob('cp6-auditor-browser-*/BROWSER.json'))
    # Even a first-original retention failure must restore the caller's environment.
    with actual_catalog_environment(product.runtime()[4].digest(state['after'])):
        try:
            bridge._bridge(conn, cur, report, state, product=product, modes=modes, helper=helper,
                adapter=adapter, script=HERE / 'cases.mjs', prerequisite=proof)
        finally:
            retained = []
            destination = ROOT / 'cp6-proof/t3'
            destination.mkdir(parents=True, exist_ok=True)
            for path in sorted(set(temp.glob('cp6-auditor-browser-*/BROWSER.json')) - before_host_reports):
                raw = path.read_bytes()
                document = json.loads(raw)
                if document.get('phase') != 'S03_CHOICE_MOUNTED4' or document.get('ui_mode') != 'DISPOSABLE':
                    raise ValueError('S03_BROWSER4_UNDECLARED_HOST_ORIGINAL')
                name = 'S03_BROWSER4_HOST_ORIGINAL_' + path.parent.name + '.json.gz'
                target = destination / name
                if target.exists():
                    raise ValueError('S03_BROWSER4_HOST_FIRST_ORIGINAL_OVERWRITE_REFUSED')
                packed = gzip.compress(raw, mtime=0)
                target.write_bytes(packed)
                retained.append(dict(name=name, raw_bytes=len(raw), raw_sha256=sha256(raw).hexdigest(),
                    gzip_bytes=len(packed), gzip_sha256=sha256(packed).hexdigest()))
            report['actual_browser_host_originals'] = retained
    report.update(actual_backend14_retained_not_rerun=True, normal_full_App=True,
        exact_case_source=str(HERE / 'cases.mjs'), source_admission_before_every_fixture_operation=True,
        actual_captured_originals=15, actual_Native_clones=2, actual_backend_runtime_files=product.sources()['files'],
        canonical_backend_selected_from_qualified3c0=True, frozen_UI82_source_unchanged=True,
        backend_ROOT_or_method_override=False, product_sources_override=False)


def scheduler_quiet(url):
    return load('s03_browser4_retained_scheduler_quiet', ROOT / 'scripts/current-vendor-receivable-qualification/native_runner.py').scheduler_quiet(url)
