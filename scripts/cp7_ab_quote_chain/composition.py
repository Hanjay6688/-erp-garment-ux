"""Apply the single admitted quote correction after every declared A/B stage.

The previous A-only browser product and B composition remain byte-identical.
Every transition observes the real database. Used installations require full
backup/restore; a global lock and row census precede the first inverse DDL.
"""
from hashlib import sha256
from pathlib import Path

from cp7_b_extension_chain import composition as predecessor
import cp7_return_quote_capability as quote

catalog,atomic,base=predecessor.catalog,predecessor.atomic,predecessor.base
USED_ERROR=predecessor.USED_ERROR


def sources():
    return dict(predecessor=predecessor.sources(),quote=quote.sources(),
        composition_sha256=sha256(Path(__file__).read_bytes()).hexdigest())


def install(cur):
    with atomic(cur):
        authority=catalog._authority(cur)
        cur.execute("select pg_advisory_xact_lock(hashtextextended('CP7:OW15:COMPOSITION',0))")
        original_catalog=catalog._catalog_rows(cur)
        previous=predecessor.install(cur)
        proof=predecessor.verify(cur,previous)
        before=catalog._catalog_rows(cur)
        original=before['functions'][quote.SIGNATURE][0]
        definition=quote.patched(original)
        owner=before['functions'][quote.SIGNATURE][1]
        truth=cur.execute("select mode,mode='REFUND',mode is not distinct from 'REFUND' "
            "from(values(null::text),('CREDIT'),('REFUND'))m(mode)").fetchall()
        if truth!=[(None,None,False),('CREDIT',False,False),('REFUND',True,True)]:
            raise ValueError('OW15_AB_QUOTE_TRUTH_TABLE_CHANGED')
        with quote.predecessor.owner.as_owner(cur,owner):cur.execute(definition,prepare=False)
        after=catalog._catalog_rows(cur);quote.admit(before,after,definition)
        state=dict(sources=sources(),authority=authority,predecessor=previous,
            predecessor_proof=proof,p21_preinstall_catalog=original_catalog,
            before=before,after=after,installed_catalog=after,original=original,
            definition=definition,owner=owner,truth_table=truth,
            p21_seeded_private_rows=base.private_rows(cur))
        verify(cur,state)
        return state


def verify(cur,state):
    if state['sources']!=sources():raise ValueError('OW15_AB_QUOTE_SOURCE_CHANGED')
    if catalog._catalog_rows(cur)!=state['after']or state['installed_catalog']!=state['after']:
        raise ValueError('OW15_AB_QUOTE_FULL22_CHANGED')
    if state['before']!=state['predecessor']['after']:
        raise ValueError('OW15_AB_QUOTE_PREDECESSOR_TRANSITION_CHANGED')
    quote.admit(state['before'],state['after'],quote.patched(state['original']))
    predecessor.checked.verify(cur,state['predecessor']['stages'][-1]['state'])
    return dict(status='OW15_AB_QUOTE_EXACT_ALL22',
        B_stages=[name for name,_ in predecessor.STAGES],
        quote_changed_functions=[quote.SIGNATURE],counted_substitutions=1,
        predecessor_verified_before_real_delta=True,production_go=False,
        full_AB_chain_qualified=False,independent_acceptance=False)


def rollback_preuse(cur,state):
    with atomic(cur):
        catalog._authority(cur)
        cur.execute("select pg_advisory_xact_lock(hashtextextended('CP7:OW15:COMPOSITION',0))")
        verify(cur,state)
        quote.predecessor._lock_private_tables(cur,state)
        if base.private_rows(cur)!=state['p21_seeded_private_rows']:raise ValueError(USED_ERROR)
        with quote.predecessor.owner.as_owner(cur,state['owner']):cur.execute(state['original'],prepare=False)
        if catalog._catalog_rows(cur)!=state['before']:
            raise ValueError('OW15_AB_QUOTE_INVERSE_NOT_EXACT')
        predecessor.verify(cur,state['predecessor'])
        removed=predecessor.rollback_preuse(cur,state['predecessor'])
        if catalog._catalog_rows(cur)!=state['p21_preinstall_catalog']:
            raise ValueError('OW15_AB_QUOTE_PREINSTALL_NOT_EXACT')
        return dict(status='OW15_AB_QUOTE_PREUSE_EXACT_RESTORE',
            used_guard_before_any_DDL=True,all22_preinstall_equal=True,
            predecessor_removed=removed,production_go=False)
