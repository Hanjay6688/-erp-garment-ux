"""Declared one-function delta for non-authoritative sibling return drafts.

The original qualified source stays frozen. This stage keeps every source lock,
raw draft dependency, financial event and posted-document proof. Only a DRAFT
RETURN's customer mismatch stops poisoning a different legitimate operation.
The selected draft is still validated by its unchanged Native posting command.
No connection, commit, application permission, context or new object is added.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import re
from cp7_ab_bounded_chain import composition as product
from cp7_customer_credit.integration import owning_bundle as credit

CONTRACT='cp7.draft-return-customer-dependency-isolation.v1'
SIGNATURE='ow04_source_proposal.locked_source_family(uuid)'
SOURCE='source/source.sql'
ANCHOR="  if doc.customer_id is distinct from customer then raise exception 'OW04_SOURCE_CUSTOMER_MISMATCH';end if;"
REPLACEMENT="""  -- Sibling DRAFT returns contribute their actual row to the dependency hash,
  -- but are not posted financial facts. The selected return's Native command
  -- still checks its own customer against its source sale before any posting.
  if not(doc.kind='RETURN'and doc.status='DRAFT')and doc.customer_id is distinct from customer then
   raise exception 'OW04_SOURCE_CUSTOMER_MISMATCH';end if;"""
catalog=product.catalog
USED_ERROR='DRAFT_RETURN_ISOLATION_AFTER_USE_REQUIRES_BACKUP_RESTORE'


def bodies():
    text=credit._actual_sql(SOURCE)
    matches=re.findall(r'create function ow04_source_proposal\.locked_source_family\(p_sale uuid\)returns jsonb\n.*?as \$\$(.*?)\$\$;',text,re.S)
    if len(matches)!=1 or matches[0].count(ANCHOR)!=1:
        raise ValueError('DRAFT_RETURN_ISOLATION_SOURCE_ANCHOR_CHANGED')
    before=matches[0];after=before.replace(ANCHOR,REPLACEMENT,1)
    return before,after


def sources():
    old,new=bodies()
    return dict(contract=CONTRACT,module_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        original_source_path='scripts/cp7_customer_credit/'+SOURCE,
        original_source_sha256=sha256((credit.ROOT/SOURCE).read_bytes()).hexdigest(),
        signature=SIGNATURE,before_body_sha256=sha256(old.encode()).hexdigest(),after_body_sha256=sha256(new.encode()).hexdigest())


def expected(before):
    if len(before)!=22 or SIGNATURE not in before['functions']:
        raise ValueError('DRAFT_RETURN_ISOLATION_FULL22_REQUIRED')
    old,new=bodies();row=before['functions'][SIGNATURE]
    if row[0].count(old)!=1:
        raise ValueError('DRAFT_RETURN_ISOLATION_UNEXPECTED_DEFINITION')
    after=deepcopy(before);after['functions'][SIGNATURE][0]=row[0].replace(old,new,1)
    return after


def install_delta(cur):
    catalog._authority(cur)
    cur.execute("select pg_advisory_xact_lock(hashtextextended('CP7:OW15:COMPOSITION',0))")
    cur.execute("select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))")
    before=catalog._catalog_rows(cur);data=catalog._data(cur)
    actual=cur.execute('select prosrc from pg_proc where oid=%s::regprocedure',(SIGNATURE,)).fetchone()[0]
    if actual!=bodies()[0]:raise ValueError('DRAFT_RETURN_ISOLATION_PREIMAGE_CHANGED')
    after=expected(before)
    cur.execute(after['functions'][SIGNATURE][0],prepare=False)
    state=dict(sources=sources(),before=before,after=after,preuse_data_and_sequences=data)
    verify(cur,state)
    if catalog._data(cur)!=data:raise ValueError('DRAFT_RETURN_ISOLATION_INSTALL_CHANGED_DATA')
    return state


def verify(cur,state):
    if state['sources']!=sources()or state['after']!=expected(state['before']):
        raise ValueError('DRAFT_RETURN_ISOLATION_DECLARATION_CHANGED')
    if catalog._catalog_rows(cur)!=state['after']:
        raise ValueError('DRAFT_RETURN_ISOLATION_LIVE_FULL22_CHANGED')
    return dict(status='EXACT_SINGLE_FUNCTION_DELTA',signature=SIGNATURE,
        unchanged_authority_and_all_other_catalog_fields=True,draft_rows_still_dependencies=True,
        posted_proofs_unchanged=True,production_go=False)


def rollback_preuse(cur,state):
    catalog._authority(cur)
    cur.execute("select pg_advisory_xact_lock(hashtextextended('CP7:OW15:COMPOSITION',0))")
    cur.execute("select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))")
    verify(cur,state)
    # Global table locks and every row/sequence are checked BEFORE the one DDL.
    # A used database needs the independent complete backup/restore route.
    catalog._lock_tables(cur)
    if catalog._data(cur)!=state['preuse_data_and_sequences']:raise ValueError(USED_ERROR)
    cur.execute(state['before']['functions'][SIGNATURE][0],prepare=False)
    if catalog._catalog_rows(cur)!=state['before']or catalog._data(cur)!=state['preuse_data_and_sequences']:
        raise ValueError('DRAFT_RETURN_ISOLATION_INVERSE_NOT_EXACT')
    return dict(status='EXACT_PREUSE_INVERSE',full22_restored=True,all_data_and_sequences_equal=True,
        used_guard_before_DDL=True,production_go=False)
