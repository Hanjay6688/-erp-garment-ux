"""One fresh midnight case plus the unchanged separate committed used witness."""
from types import ModuleType
from midnight_common import HERE, ROOT, ID, document
import midnight_gate as gate
import midnight_admission as admission
import midnight_factory as factory
import midnight_derive as derive
import midnight_group as single

BOUND_PARENT = None


def exercise(conn, cur, database, url, report, state):
    cfg = document((HERE / 'CONFIG.json').read_bytes())
    gate.selected(cfg)
    if BOUND_PARENT is None:
        raise ValueError('MIDNIGHT_ACTUAL_SIX_ORIGINAL_PARENT_NOT_ADMITTED')
    import psycopg
    import cp6_bd_probe as financial_truth
    from cp7_attendance_period_choice import composition as product
    from cp7_p21_current_chain_rehearsal_probe import helper
    control, native = helper.control, helper.control.native
    module = ModuleType('midnight_exact_committed_used_helper')
    raw = (ROOT / 'scripts/current-attendance-period-choice-native11-qualification/native_runner.py').read_bytes()
    code, proof = derive.witness(raw)
    exec(compile(code, 'midnight-exact-committed-used-helper', 'exec'), module.__dict__)
    module.require_local(conn, cur)
    admission.checked(BOUND_PARENT['documents'], cfg, product.sources())
    factory.installed(product, state)
    report.update(status='INCOMPLETE', actual_Native_cases=0, required_Native_case_ids=[ID],
        actual_installed_capture=dict(originals=state['originals'], definitions=state['definitions'],
            clones=state['clones'], actual_all22=state['after'], source_derived_local_ABI_used=False),
        used_helper_derivation=proof, fresh_original11_or14_reexecuted=False,
        production_go=False, independent_acceptance=False)
    conn.rollback()
    cur.close()
    conn.close()

    def verify(cursor):
        with control.product_catalog(cursor):
            return product.verify(cursor, state)

    single.run(native, control, state, report, verify, BOUND_PARENT, product, cfg)
    exact = factory.historical()
    business = exact.originals()
    module.committed_used_witness(native, control, state, report, url, business, product,
        financial_truth, psycopg, module.require_local, module.sequence_prefix)
    report.update(actual_Native_cases=1, committed_used_witness_additional_cases=0,
        single_attempt=True, day_rollover_retry=False, combined_strict15_fabricated=False)
