"""Owned accepted14 factory. The historical fresh11 factory is never invoked."""
import importlib.util
from midnight_common import HERE, ROOT, ID, document, pin
import midnight_gate as gate
import midnight_admission as admission


def historical():
    origin = document((HERE / 'ORIGIN.json').read_bytes())
    where = HERE / 'historical-midnight-c0'
    for name, expected in origin['files'].items():
        if pin((where / name).read_bytes()) != expected:
            raise ValueError('MIDNIGHT_IMMUTABLE_ORIGINAL_CHANGED:' + name)
    path = where / 'cases.py'
    spec = importlib.util.spec_from_file_location('midnight_exact_c0_case_body', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # One explicit filesystem-metadata route: the unchanged originals() reads
    # the ACTUAL current source tree, not the nested historical directory.
    # No source text, callback, oracle, product.sources or installed state changes.
    module.ROOT = ROOT
    return module


def installed(product, state):
    import cp7_attendance_period_choice.native_delta as delta
    actual = product.sources()
    if (state.get('sources') != actual or len(actual.get('files', {})) != 7
            or set(state.get('originals', {})) != set(delta.SIGNATURES)
            or len(state['originals']) != 15 or len(state.get('clones', {})) != 2
            or state.get('definitions') != delta.patched(state['originals'])
            or state['clones'] != delta.clones(state['originals'])
            or len(state.get('after', {})) != 22):
        raise ValueError('MIDNIGHT_ACTUAL_CURRENT7_INSTALLED15_CLONES2_REQUIRED')


def cases(cur, today, *, state, evidence, accepted_parent14, product, cfg=None):
    """New contract replaces old prerequisite intake; it does not call old cases()."""
    cfg = document((HERE / 'CONFIG.json').read_bytes()) if cfg is None else cfg
    gate.selected(cfg)
    proof = admission.checked(accepted_parent14['documents'], cfg, product.sources())
    installed(product, state)
    verified = product.verify(cur, state)
    original = historical()
    current_helpers = original.originals()
    evidence['midnight_accepted14_prerequisite'] = proof
    evidence['midnight_actual_installed_boundary'] = verified
    evidence['midnight_factory_contract'] = dict(
        old_fresh11_factory_invoked=False, fresh_original11_or14_reexecuted=False,
        exact_standalone_callback='run_boundary(cur,today,original)',
        actual_Native_credit_before_execution=0)
    return [(ID, lambda: original.run_boundary(cur, today, current_helpers))]
