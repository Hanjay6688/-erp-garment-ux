"""Counted return-quote capability correction over the admitted complete A chain.

SQL mode=NULL emitted refund_cash=NULL, contradicting the public boolean
contract. A null choice requests no refund, so its capability is false. No
unknown amount, balance or permission is converted to zero or granted here.
"""
from hashlib import sha256
from pathlib import Path
import cp7_p21_chain_adapter as predecessor

catalog=predecessor.catalog
atomic=predecessor.atomic
base=predecessor.base
SIGNATURE='cp7_credit.build_initial_return_for_draft_v1(jsonb,text,jsonb,uuid)'
OLD="'refund_cash',mode='REFUND'"
NEW="'refund_cash',mode is not distinct from 'REFUND'"


def sources():
    return dict(predecessor=predecessor.sources(),correction_sha256=sha256(Path(__file__).read_bytes()).hexdigest())


def patched(original):
    if original.count(OLD)!=1 or NEW in original:
        raise ValueError('OW04_RETURN_QUOTE_CAPABILITY_SOURCE_CHANGED')
    return original.replace(OLD,NEW,1)


def admit(before,after,definition):
    if set(before)!=set(after)or len(before)!=22:
        raise ValueError('OW04_RETURN_QUOTE_CAPABILITY_CATALOG_GROUPS_CHANGED')
    for group in before:
        for key in set(before[group])|set(after[group]):
            old,new=before[group].get(key),after[group].get(key)
            if old==new:continue
            if group=='functions'and key==SIGNATURE and old is not None and new is not None \
                    and new[0]==definition and old[1:]==new[1:]:continue
            raise ValueError('OW04_RETURN_QUOTE_CAPABILITY_UNDECLARED_DELTA: '+group+':'+key)


def install(cur):
    with atomic(cur):
        catalog._authority(cur)
        previous=predecessor.install(cur)
        proof=predecessor.verify(cur,previous)
        before=catalog._catalog_rows(cur)
        original=before['functions'][SIGNATURE][0]
        definition=patched(original)
        owner=before['functions'][SIGNATURE][1]
        truth=cur.execute("select mode,mode='REFUND',mode is not distinct from 'REFUND' "
            "from(values(null::text),('CREDIT'),('REFUND'))m(mode)").fetchall()
        if truth!=[(None,None,False),('CREDIT',False,False),('REFUND',True,True)]:
            raise ValueError('OW04_RETURN_QUOTE_CAPABILITY_TRUTH_TABLE_CHANGED')
        with predecessor.owner.as_owner(cur,owner):cur.execute(definition,prepare=False)
        after=catalog._catalog_rows(cur);admit(before,after,definition)
        state=dict(sources=sources(),predecessor=previous,predecessor_proof=proof,
            before=before,after=after,installed_catalog=after,original=original,
            definition=definition,owner=owner,truth_table=truth,
            p21_seeded_private_rows=base.private_rows(cur))
        verify(cur,state);return state


def verify(cur,state):
    if state['sources']!=sources()or catalog._catalog_rows(cur)!=state['after']:
        raise ValueError('OW04_RETURN_QUOTE_CAPABILITY_SOURCE_OR_ALL22_CHANGED')
    admit(state['before'],state['after'],patched(state['original']))
    return dict(status='OW04_RETURN_QUOTE_CAPABILITY_EXACT_ALL22',
        changed_functions=[SIGNATURE],counted_substitutions=1,
        no_choice_refund_capability=False,positive_modes_unchanged=True,
        grants_owners_metadata_and_business_rows_unchanged=True,production_go=False)


def rollback_preuse(cur,state):
    with atomic(cur):
        catalog._authority(cur);verify(cur,state)
        predecessor._lock_private_tables(cur,state)
        if base.private_rows(cur)!=state['p21_seeded_private_rows']:
            raise ValueError(predecessor.USED_ERROR)
        with predecessor.owner.as_owner(cur,state['owner']):cur.execute(state['original'],prepare=False)
        if catalog._catalog_rows(cur)!=state['before']:
            raise ValueError('OW04_RETURN_QUOTE_CAPABILITY_PREDECESSOR_NOT_EXACT')
        predecessor.verify(cur,state['predecessor'])
        return dict(correction_removed_exactly=True,
            predecessor=predecessor.rollback_preuse(cur,state['predecessor']),production_go=False)
