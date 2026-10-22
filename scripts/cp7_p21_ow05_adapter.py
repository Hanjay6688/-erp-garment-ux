"""P21 administrative entry point for the complete current OW05 owner.

The caller owns the transaction. No connection, commit, provider, schedule or
production admission happens on import or through installation.
"""
from hashlib import sha256
from pathlib import Path

from cp7_contractor_correction import composition as owner
import cp7_ow05_restore as recovery

ROOT=Path(__file__).resolve().parents[1]
catalog=owner.predecessor.catalog
atomic=owner.predecessor.atomic
RECEIVABLES='erp.v_customer_receivables'
ARRAY_CAST="ANY ((ARRAY['POSTED'::character varying, 'PARTIAL_PAID'::character varying, 'PAID'::character varying])::text[])"
ARRAY_ELEMENTS="ANY (ARRAY[('POSTED'::character varying)::text, ('PARTIAL_PAID'::character varying)::text, ('PAID'::character varying)::text])"
ARRAY_IMPLICIT="ANY (ARRAY['POSTED'::character varying, 'PARTIAL_PAID'::character varying, 'PAID'::character varying])"


def sources():
    return dict(financial_product=owner.sources(),administrative_restore=recovery.sources(),
        adapter_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        default_P21_entrypoint_sha256=sha256((ROOT/'scripts/cp7_p21_full_rehearsal_probe.py').read_bytes()).hexdigest())


def install(cur):
    before=catalog._catalog_rows(cur)
    state=owner.install(cur)
    state['p21_preinstall_catalog']=before
    state['installed_catalog']=state['after']  # Same full 22-group catalog, no projection.
    return state


def verify(cur,state):return owner.verify(cur,state)


def rollback_preuse(cur,state):
    with atomic(cur):
        before=state['p21_preinstall_catalog']
        removed=owner.rollback_preuse(cur,state)
        after=catalog._catalog_rows(cur)
        if after!=before:
            # PostgreSQL's view deparser renders this implicit array coercion
            # as an explicit cast. Re-parsing that text pushes casts into the
            # elements. Restore the original parse using its implicit cast;
            # do not normalize or ignore either catalog representation.
            changes={group:{key for key in set(before[group])|set(after[group])
                if before[group].get(key)!=after[group].get(key)}
                for group in before if before[group]!=after[group]}
            if changes!={'relations':{RECEIVABLES},'rules':{RECEIVABLES+':_RETURN'}}:
                raise ValueError('P21_PREUSE_UNDECLARED_CATALOG_CHANGE')
            for group,key,index in (('relations',RECEIVABLES,9),('rules',RECEIVABLES+':_RETURN',3)):
                old,new=before[group][key],after[group][key]
                wanted=old.copy()
                if old[index].count(ARRAY_CAST)!=1:
                    raise ValueError('P21_PREUSE_ORIGINAL_VIEW_ARRAY_SOURCE_CHANGED')
                wanted[index]=old[index].replace(ARRAY_CAST,ARRAY_ELEMENTS)
                if new!=wanted:
                    raise ValueError('P21_PREUSE_VIEW_ROUNDTRIP_NOT_DECLARED')
            definition=before['relations'][RECEIVABLES][9].replace(ARRAY_CAST,ARRAY_IMPLICIT)
            cur.execute('create or replace view erp.v_customer_receivables with(security_invoker=true)as '+definition,
                prepare=False)
            if catalog._catalog_rows(cur)!=before:
                raise ValueError('P21_PREUSE_ORIGINAL_FULL_CATALOG_NOT_RESTORED')
        return dict(**removed,p21_original_all22_catalog_groups_equal=True,
            catalog_comparison_not_normalized=True)


def export_manifest(cur,state):return recovery.export_manifest(cur,state)


def rebind_restored(cur,backup,expected_sha256,*,expected_database):
    return recovery.rebind_restored(cur,backup,expected_sha256,expected_database=expected_database)
