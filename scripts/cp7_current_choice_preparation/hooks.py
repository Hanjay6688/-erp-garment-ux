"""Two counted hooks into the existing K4 runner and retention transaction."""
from hashlib import sha256
from pathlib import Path
import json,re
from cp7_production_stage import _row,_body
from cp7_finance_capture import native_delta
from cp7_bounded_analysis_stage.source import once
from cp7_ow04_restore_bundle import _catalog_rows

ROOT=Path(__file__).resolve().parents[1]
RUNNER='cp7_background.run_next()'
RETENTION='cp7_ops.retention_tick()'
FUNCTIONS={RUNNER:('v',False),RETENTION:('v',True)}

def block(text,name):
    matches=re.findall(r'create (?:or replace )?function '+re.escape(name)+r'\(.*?\$\$;',text,re.S)
    if len(matches)!=1:raise ValueError('CHOICE_HOOK_SINGLE_PARENT_REQUIRED:'+name)
    return matches[0]

def originals():
    runner=block((ROOT/'cp7-src/ops/background.sql').read_text(),RUNNER[:-2])
    for label,old,new in native_delta.STEPS[RUNNER]:
        runner=native_delta.once(runner,old,new,RUNNER+':'+label)
    return {RUNNER:runner,RETENTION:block((ROOT/'cp7-src/ops/schedule.sql').read_text(),RETENTION[:-2])}

def definitions():
    old=originals();runner=old[RUNNER]
    runner=once(runner,'create function ','create or replace function ')
    runner=once(runner,"  union all select 'FINANCE',min(updated_at)from cp7_finance_capture.captures where state='RUNNING'\n",
        "  union all select 'FINANCE',min(updated_at)from cp7_finance_capture.captures where state='RUNNING'\n"
        "  union all select 'CHOICE_PREPARATION',min(updated_at)from cp7_frozen_choice_preparation.work where state='QUEUED'\n")
    runner=once(runner,"when 'FINANCE'then cp7_finance_capture.run_next()else",
        "when 'FINANCE'then cp7_finance_capture.run_next()when 'CHOICE_PREPARATION'then "
        "cp7_frozen_choice_preparation.run_next()||jsonb_build_object('family','CHOICE_PREPARATION')else")
    retention=once(old[RETENTION],'create function ','create or replace function ')
    retention=once(retention,"jsonb_build_object('tick','cp7-staged-retention'",
        "jsonb_build_object('choice_preparation_payloads',cp7_frozen_choice_preparation.purge_expired(200),'tick','cp7-staged-retention'")
    return {RUNNER:runner,RETENTION:retention}

def verify_sources():
    return dict(module_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        original_bodies={k:sha256(_body(v).encode()).hexdigest()for k,v in originals().items()},
        generated_bodies={k:sha256(_body(v).encode()).hexdigest()for k,v in definitions().items()},
        schedule_unchanged=True,statement_limits_unchanged=True)

def own(catalog):
    return {g:{k:v for k,v in rows.items()if g=='functions'and k in FUNCTIONS}for g,rows in catalog.items()}

def verify(cur,state):
    if state['sources']!=verify_sources()or _catalog_rows(cur)!=state['after']:
        raise ValueError('CHOICE_HOOK_SOURCE_OR_CATALOG_CHANGED')
    for sig,definition in definitions().items():
        row=_row(cur,sig);old=state['old_replacements'][sig]
        if row!=state['rows'][sig]or row[1]!=_body(definition)or row[2:]!=old[2:]or old[1]!=_body(originals()[sig]):
            raise ValueError('CHOICE_HOOK_BODY_OR_AUTHORITY_CHANGED:'+sig)
        if state['before']['functions'][sig][1:]!=state['after']['functions'][sig][1:]:
            raise ValueError('CHOICE_HOOK_CATALOG_AUTHORITY_CHANGED:'+sig)
    return dict(existing_replacements=2,new_public_rpcs=0,new_tables=0,
        existing_finance_dispatch_preserved=True,existing_schedule_unchanged=True,
        unit_statement_limits_unchanged=True,retention_batch=200,production_go=False)

def install_delta(cur,predecessor_checker):
    predecessor_checker(cur)
    before=_catalog_rows(cur);old={k:_row(cur,k)for k in FUNCTIONS}
    for sig,definition in originals().items():
        if old[sig][1]!=_body(definition):raise ValueError('CHOICE_HOOK_ACTUAL_PARENT_CHANGED:'+sig)
    for definition in definitions().values():cur.execute(definition,prepare=False)
    after=_catalog_rows(cur)
    changed={(g,k)for g in before for k in set(before[g])|set(after[g])if before[g].get(k)!=after[g].get(k)}
    if set(before)!=set(after)or len(before)!=22 or changed!={('functions',k)for k in FUNCTIONS}:
        raise ValueError('CHOICE_HOOK_UNDECLARED_DELTA')
    state=dict(sources=verify_sources(),before=before,after=after,catalog=own(after),
        old_replacements=old,rows={k:_row(cur,k)for k in FUNCTIONS})
    verify(cur,state);return state

def rollback_preuse(cur,state):
    verify(cur,state)
    for row in state['old_replacements'].values():cur.execute(row[0],prepare=False)
    if _catalog_rows(cur)!=state['before']:raise ValueError('CHOICE_HOOK_INVERSE_NOT_EXACT')
