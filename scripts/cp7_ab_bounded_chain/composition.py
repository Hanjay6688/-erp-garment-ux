"""Integrator's bounded stages above the qualified whole A/B/quote chain.

Each transition executes the unchanged stage source/body/authority verifier
and full22 delta admission before the next transition. The final catalog is
compared exactly; earlier definitions are never projected into a live check.
Inverse walks the same states backwards after one global before-DDL guard.
"""
from hashlib import sha256
from pathlib import Path
from cp7_ab_quote_chain import composition as predecessor
import cp7_schedule_staged_review as schedule
import cp7_history_bounded as history
import cp7_history_reference as reference
import cp7_ab_bounded_stage as bounded

STAGES=(('STAGED_SCHEDULE',schedule),('BOUNDED_HISTORY',history),
        ('FULL_STOCK_REFERENCE',reference),('AB_BOUNDED',bounded))
catalog,atomic,base=predecessor.catalog,predecessor.atomic,predecessor.base
USED_ERROR=predecessor.USED_ERROR


def sources():
    return dict(predecessor=predecessor.sources(),stages={name:module.sources()for name,module in STAGES},
        stage_order=[name for name,_ in STAGES],composition_sha256=sha256(Path(__file__).read_bytes()).hexdigest())


def install(cur):
    with atomic(cur):
        authority=catalog._authority(cur)
        cur.execute("select pg_advisory_xact_lock(hashtextextended('CP7:OW15:COMPOSITION',0))")
        original=catalog._catalog_rows(cur)
        previous=predecessor.install(cur)
        before=catalog._catalog_rows(cur)
        previous_proof=predecessor.verify(cur,previous)
        stages=[]
        for name,module in STAGES:
            left=catalog._catalog_rows(cur)
            state=module.install_delta(cur)
            right=catalog._catalog_rows(cur)
            module.admit_catalog(left,right,state)
            proof=module.verify(cur,state)
            stages.append(dict(name=name,state=state,before=left,after=right,proof_before_next_stage=proof))
        after=catalog._catalog_rows(cur)
        state=dict(sources=sources(),authority=authority,predecessor=previous,
            predecessor_proof=previous_proof,p21_preinstall_catalog=original,
            before=before,after=after,installed_catalog=after,stages=stages,
            p21_seeded_private_rows=base.private_rows(cur),truth_table=previous['truth_table'])
        verify(cur,state)
        return state


def verify(cur,state):
    if state['sources']!=sources():raise ValueError('OW15_AB_BOUNDED_CHAIN_SOURCE_CHANGED')
    if [row['name']for row in state['stages']]!=[name for name,_ in STAGES]:raise ValueError('OW15_AB_BOUNDED_CHAIN_ORDER_CHANGED')
    current=catalog._catalog_rows(cur)
    if len(current)!=22 or current!=state['after']or state['installed_catalog']!=state['after']:
        raise ValueError('OW15_AB_BOUNDED_CHAIN_FULL22_CATALOG_CHANGED')
    # Validate the captured transition chain as well as the exact final catalog.
    # Some later stages intentionally replace earlier hooks. Their earlier
    # verifiers ran on the real earlier DB, never on substituted definitions.
    left=state['before']
    for row,(name,module)in zip(state['stages'],STAGES):
        if row['before']!=left:raise ValueError('OW15_AB_BOUNDED_CHAIN_BROKEN_TRANSITION: '+name)
        module.admit_catalog(row['before'],row['after'],row['state'])
        left=row['after']
    if left!=current:raise ValueError('OW15_AB_BOUNDED_CHAIN_TOP_TRANSITION_CHANGED')
    bounded.verify(cur,state['stages'][-1]['state'])
    return dict(status='OW15_AB_BOUNDED_EXTENSIONS_EXACT_SOURCE_ALL22_TRANSITIONS_VERIFIED',
        stages=[name for name,_ in STAGES],earlier_verifiers_executed_before_each_real_delta=True,
        substituted_catalog_or_definitions=False,full_AB_chain_qualified=False,
        installed_schedules=False,production_go=False,independent_acceptance=False)


def rollback_preuse(cur,state):
    with atomic(cur):
        catalog._authority(cur)
        cur.execute("select pg_advisory_xact_lock(hashtextextended('CP7:OW15:COMPOSITION',0))")
        verify(cur,state)
        predecessor.quote.predecessor._lock_private_tables(cur,state)
        if base.private_rows(cur)!=state['p21_seeded_private_rows']:raise ValueError(USED_ERROR)
        for row,(name,module)in reversed(list(zip(state['stages'],STAGES))):
            module.verify(cur,row['state'])
            module.rollback_preuse(cur,row['state'])
            if catalog._catalog_rows(cur)!=row['before']:raise ValueError('OW15_AB_BOUNDED_CHAIN_STAGE_INVERSE_NOT_EXACT: '+name)
        predecessor.verify(cur,state['predecessor'])
        removed=predecessor.rollback_preuse(cur,state['predecessor'])
        if catalog._catalog_rows(cur)!=state['p21_preinstall_catalog']:raise ValueError('OW15_AB_BOUNDED_CHAIN_PREINSTALL_NOT_EXACT')
        return dict(status='OW15_AB_BOUNDED_CHAIN_PREUSE_EXACT_RESTORE',all22_preinstall_equal=True,
            used_guard_before_any_DDL=True,financial_facts_deleted=False,
            predecessor_removed=removed,production_go=False)
