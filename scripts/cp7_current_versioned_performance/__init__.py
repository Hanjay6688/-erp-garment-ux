"""A-owned late application of two exact B context-path function bodies.

Qualified B input files are retained byte-for-byte. Only the two whitelisted
definitions are executed, after verification of the actual full predecessor.
No predecessor source, rows, sequences, owner, ACL or function settings change.
"""
from hashlib import sha256
from pathlib import Path
import json,re
from cp7_production_stage import _row,_body
from cp7_ow04_restore_bundle import _catalog_rows,_data

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
CONTRACT='cp7.current-versioned-performance-two-function-delta.v1'
FUNCTIONS={
 'cp7_product_analog_consumer.resolve(jsonb,text,jsonb)':'qualified-kernel.sql',
 'cp7_product_analog_consumer.baseline_rows(jsonb,jsonb,jsonb,text,jsonb)':'qualified-provenance-hooks.sql'}
CHANGES={
 'qualified-kernel.sql':(
  ("v->'choices'->p_target","v#>array['choices',p_target]"),
  ("v->'products'->p_target","v#>array['products',p_target]"),
  ("v->'products'->source","v#>array['products',source]"),
  ("v->'histories'->source","v#>array['histories',source]")),
 'qualified-provenance-hooks.sql':(
  ("context->'histories'->(r->>'target_key')","context#>array['histories',r->>'target_key']"),
  ("context->'choices'->(r->>'target_key')->>'state'","context#>>array['choices',r->>'target_key','state']"))}
COMMENT=' -- Traverse each path directly: an intermediate histories/choices object\n -- would copy the factory-wide map for every target. Guards and values stay exact.\n'


def sources():
    declaration=json.loads((ROOT/'BOUND_B_SOURCES.json').read_bytes())
    for name,record in declaration['files'].items():
        old=(REPO/record['retained_path']).read_bytes();new=(ROOT/name).read_bytes()
        if sha256(old).hexdigest()!=record['retained_sha256']or sha256(new).hexdigest()!=record['qualified_sha256']:
            raise ValueError('CURRENT_VERSIONED_PERFORMANCE_INPUT_SOURCE_CHANGED')
        expected=old.decode()
        for before,after in CHANGES[name]:
            if expected.count(before)!=1:raise ValueError('CURRENT_VERSIONED_PERFORMANCE_PATH_ANCHOR_CHANGED')
            expected=expected.replace(before,after)
        actual=new.decode()
        if name=='qualified-provenance-hooks.sql':
            if actual.count(COMMENT)!=1:raise ValueError('CURRENT_VERSIONED_PERFORMANCE_DECLARED_COMMENT_CHANGED')
            actual=actual.replace(COMMENT,'')
        if actual!=expected:raise ValueError('CURRENT_VERSIONED_PERFORMANCE_UNDECLARED_BUSINESS_CHANGE')
    return dict(contract=CONTRACT,B_head=declaration['B_head'],actual_B_component_proof=declaration['actual_component_proof'],
        files={p.name:sha256(p.read_bytes()).hexdigest()for p in sorted(ROOT.iterdir())if p.is_file()},
        retained_sources={r['retained_path']:r['retained_sha256']for r in declaration['files'].values()},
        changed_json_paths=6,functions=2,unchanged_business_predicates=True)


def definitions():
    sources();manifest=json.loads((ROOT/'BOUND_B_SOURCES.json').read_bytes());old={};new={}
    for signature,name in FUNCTIONS.items():
        pattern=r'create(?: or replace)? function '+re.escape(signature.split('(')[0])+r'\(.*?\$\$;'
        for text,destination in (((REPO/manifest['files'][name]['retained_path']).read_text(),old),((ROOT/name).read_text(),new)):
            matches=re.findall(pattern,text,re.S|re.I)
            if len(matches)!=1:raise ValueError('CURRENT_VERSIONED_PERFORMANCE_DEFINITION_COUNT_CHANGED')
            destination[signature]=re.sub(r'^create function ','create or replace function ',matches[0],flags=re.I)
        if _body(old[signature])==_body(new[signature]):raise ValueError('CURRENT_VERSIONED_PERFORMANCE_EXPECTED_BODY_CHANGE_MISSING')
    return old,new


def admit_catalog(before,after):
    if set(before)!=set(after)or len(before)!=22:raise ValueError('CURRENT_VERSIONED_PERFORMANCE_FULL22_REQUIRED')
    changed=set()
    for group in before:
        for key in set(before[group])|set(after[group]):
            left,right=before[group].get(key),after[group].get(key)
            if left==right:continue
            if group!='functions'or key not in FUNCTIONS or left is None or right is None or left[1:]!=right[1:]:
                raise ValueError('CURRENT_VERSIONED_PERFORMANCE_UNDECLARED_CATALOG_CHANGE')
            changed.add(key)
    if changed!=set(FUNCTIONS):raise ValueError('CURRENT_VERSIONED_PERFORMANCE_INCOMPLETE_DELTA')


def verify(cur,state):
    if state['sources']!=sources()or _catalog_rows(cur)!=state['after']:
        raise ValueError('CURRENT_VERSIONED_PERFORMANCE_SOURCE_OR_FULL22_CHANGED')
    old,new=definitions();admit_catalog(state['before'],state['after'])
    if set(state['old_rows'])!=set(FUNCTIONS)or set(state['new_rows'])!=set(FUNCTIONS):
        raise ValueError('CURRENT_VERSIONED_PERFORMANCE_FUNCTION_SET_CHANGED')
    for signature in FUNCTIONS:
        left,right=state['old_rows'][signature],state['new_rows'][signature]
        if(_row(cur,signature)!=right or left[0]!=state['before']['functions'][signature][0]
           or right[0]!=state['after']['functions'][signature][0]
           or left[1]!=_body(old[signature])or right[1]!=_body(new[signature])or left[2:]!=right[2:]):
            raise ValueError('CURRENT_VERSIONED_PERFORMANCE_BODY_OR_AUTHORITY_CHANGED')
    return dict(stage=CONTRACT,two_exact_B_function_bodies=True,six_path_substitutions=True,
        complete22_catalog_verified=True,unchanged_owner_ACL_settings=True,new_tables=0,new_schemas=0,new_functions=0,new_public_rpcs=0,production_go=False)


def install_delta(cur,predecessor_checker):
    if not callable(predecessor_checker):raise ValueError('CURRENT_VERSIONED_PERFORMANCE_ACTUAL_PARENT_REQUIRED')
    predecessor_checker(cur)
    if cur.execute("select exists(select 1 from cp7_analysis_stage.jobs where state='RUNNING')or exists(select 1 from cp7_analysis_jobs.jobs where state='WAITING')").fetchone()[0]:
        raise ValueError('CURRENT_VERSIONED_PERFORMANCE_QUIET_INSTALL_REQUIRED')
    old,new=definitions();before=_catalog_rows(cur);data=_data(cur);rows={s:_row(cur,s)for s in FUNCTIONS}
    for signature in FUNCTIONS:
        if rows[signature][1]!=_body(old[signature])or rows[signature][2]!='cp7_capture':
            raise ValueError('CURRENT_VERSIONED_PERFORMANCE_ACTUAL_PREDECESSOR_CHANGED')
    for definition in new.values():cur.execute(definition,prepare=False)
    if _data(cur)!=data:raise ValueError('CURRENT_VERSIONED_PERFORMANCE_DELTA_CHANGED_ROWS_OR_SEQUENCES')
    state=dict(sources=sources(),before=before,after=_catalog_rows(cur),old_rows=rows,new_rows={s:_row(cur,s)for s in FUNCTIONS},preuse_data_and_sequences=data)
    verify(cur,state);return state


def rollback_preuse(cur,state):
    """The full composer and this stage both check every row before any DDL."""
    verify(cur,state)
    if _data(cur)!=state['preuse_data_and_sequences']:
        raise ValueError('CURRENT_VERSIONED_PERFORMANCE_DELTA_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE')
    for row in state['old_rows'].values():cur.execute(row[0],prepare=False)
    if _catalog_rows(cur)!=state['before']:raise ValueError('CURRENT_VERSIONED_PERFORMANCE_INVERSE_NOT_EXACT')
