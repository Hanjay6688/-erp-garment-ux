"""Counted B SQL delta; A owns predecessor-chain composition and release admission.

No connection, implicit commit, schedule, provider call, Native write or default
installer change. These functions operate inside the caller's atomic stage.
"""
from hashlib import sha256
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
MANIFEST = json.loads((ROOT/'MANIFEST.json').read_text())
FUNCTIONS = tuple(x['signature'] for x in MANIFEST['functions'])
TABLES = ('cp7_stock_formula.material_settings', 'cp7_stock_formula.material_evaluations')
NEW_COLUMNS = frozenset(MANIFEST['new_columns'])
CONSTRAINTS = frozenset(('cp7_stock_formula.material_settings:'+x)for x in
    ('ow14b_material_rule','ow14b_legacy_requires_point','ow14b_formula_clears_point')) | \
    {'cp7_stock_formula.material_evaluations:ow14b_evaluation_rule'}


def _body(definition):
    return re.search(r'\bas\s+(\$[a-zA-Z_0-9]*\$)(.*?)\1', definition, re.S | re.I)[2]


def sources():
    files = sorted(p for p in ROOT.rglob('*') if p.is_file() and p.suffix in ('.py','.sql','.json'))
    return {str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest() for p in files}


def verify_sources():
    source_root = ROOT.parents[1]/'scripts/cp7-src'
    for item in MANIFEST['files']:
        if sha256((source_root/item['path']).read_bytes()).hexdigest() != item['frozen_sha256']:
            raise ValueError('CP7_PRODUCTION_FROZEN_SOURCE_CHANGED: '+item['path'])
    for item in MANIFEST['functions']:
        for direction in ('forward','inverse'):
            actual = sha256((ROOT/'sql'/item[direction]).read_bytes()).hexdigest()
            if actual != item[direction+'_sha256']:
                raise ValueError('CP7_PRODUCTION_DELTA_SOURCE_CHANGED: '+item['signature'])
    return sources()


def _row(cur, signature):
    r = cur.execute("select pg_get_functiondef(p.oid),prosrc,pg_get_userbyid(proowner),prosecdef,provolatile::text,"
                    "proconfig,proacl::text,prorettype::regtype::text,proargtypes::text,prokind::text,proleakproof,"
                    "proparallel::text,procost::text,prorows::text from pg_proc p where p.oid=%s::regprocedure", (signature,)).fetchone()
    if r is None:
        raise ValueError('CP7_PRODUCTION_FUNCTION_MISSING: '+signature)
    return list(r)


def _columns(cur):
    return cur.execute("select c.oid::regclass::text||'.'||a.attname from pg_attribute a join pg_class c on c.oid=a.attrelid "
                       "where c.oid=any(%s::regclass[])and a.attnum>0 and not a.attisdropped order by 1", (list(TABLES),)).fetchall()


def extension(include_paths=None):
    """Closed disposable harness: frozen install, exact before bodies, then B delta.

    The owning chain should use apply()/verify() with A's 22-group admission.
    The SQL guard also applies when the harness installs the delta in one call.
    """
    verify_sources()
    selected = [x for x in MANIFEST['functions'] if include_paths is None or x['path'] in include_paths]
    declarations = []
    for item in selected:
        sig = item['signature'].replace("'", "''")
        declarations.append("if(select encode(sha256(convert_to(prosrc,'UTF8')),'hex')from pg_proc where oid='"+sig+
                            "'::regprocedure)is distinct from'"+item['before_body_sha256']+"'then raise exception 'CP7_PRODUCTION_PREDECESSOR_BODY_CHANGED: "+sig+"';end if;")
    guard = 'do $$begin\n'+'\n'.join(declarations)+'\nend $$;'
    return '\n'.join((guard, (ROOT/'sql/upgrade.sql').read_text() if any(x['path']=='stock-formula/materials.sql'for x in selected)else'',
                      *[(ROOT/'sql'/i['forward']).read_text()for i in selected]))


def apply(cur, include_paths=None):
    """Capture exact prior DDL/authority; caller installs and admits the full chain."""
    src = verify_sources()
    selected = [x for x in MANIFEST['functions'] if include_paths is None or x['path'] in include_paths]
    before = {x['signature']:_row(cur,x['signature'])for x in selected}
    columns = any(x['path']=='stock-formula/materials.sql'for x in selected)
    if columns and NEW_COLUMNS & {r[0] for r in _columns(cur)}:
        raise ValueError('CP7_PRODUCTION_STAGE_ALREADY_PRESENT')
    cur.execute(extension(include_paths), prepare=False)
    state = dict(sources=src, functions=before, columns=columns)
    verify(cur, state)
    return state


def verify(cur, state):
    if sources() != state['sources']:
        raise ValueError('CP7_PRODUCTION_STAGE_SOURCE_CHANGED')
    for item in MANIFEST['functions']:
        signature = item['signature']
        if signature not in state['functions']:
            continue
        r = _row(cur, signature)
        if sha256(r[1].encode()).hexdigest() != item['after_body_sha256'] or r[2:] != state['functions'][signature][2:]:
            raise ValueError('CP7_PRODUCTION_FUNCTION_OR_AUTHORITY_CHANGED: '+signature)
    if state['columns'] and not NEW_COLUMNS <= {r[0]for r in _columns(cur)}:
        raise ValueError('CP7_PRODUCTION_PRIVATE_COLUMNS_CHANGED')
    return dict(stage=MANIFEST['contract'], changed_functions=len(state['functions']), new_columns=sorted(NEW_COLUMNS)if state['columns']else[],
                Native_DML=False, full_chain_qualified=False, production_go=False)


def admit_catalog(before, after, state):
    """No exceptions for anything outside the 18 bodies/3 columns/4 constraints."""
    if set(before) != set(after) or len(before) != 22:
        raise ValueError('CP7_PRODUCTION_COMPLETE_CATALOG_GROUPS_CHANGED')
    for group in before:
        for key in set(before[group]) | set(after[group]):
            old, new = before[group].get(key), after[group].get(key)
            if old == new:
                continue
            if group == 'functions' and key in state['functions'] and old is not None and new is not None:
                if old[0] == state['functions'][key][0] and old[1:] == new[1:]:
                    item = next(x for x in MANIFEST['functions'] if x['signature'] == key)
                    if sha256(_body(new[0]).encode()).hexdigest() == item['after_body_sha256']:
                        continue
            if group == 'columns' and old is None and new is not None and key.replace(':','.',1) in NEW_COLUMNS:
                continue
            if group == 'constraints' and old is None and new is not None and key in CONSTRAINTS:
                continue
            raise ValueError('CP7_PRODUCTION_UNDECLARED_CATALOG_DELTA: '+group+':'+key)


def rollback_preuse(cur, state):
    """A must first run its global use guard/locks inside the same transaction."""
    verify(cur, state)
    if state['columns'] and cur.execute('select exists(select 1 from cp7_stock_formula.material_settings where fabric_rule is not null)').fetchone()[0]:
        raise ValueError('CP7_PRODUCTION_STAGE_AFTER_USE_REQUIRES_BACKUP_RESTORE')
    for signature in reversed(state['functions']):
        cur.execute(state['functions'][signature][0], prepare=False)
    if state['columns']:
        cur.execute((ROOT/'sql/rollback-columns.sql').read_text(), prepare=False)
    if state['columns'] and {r[0]for r in _columns(cur)} & NEW_COLUMNS:
        raise ValueError('CP7_PRODUCTION_PRIVATE_COLUMNS_NOT_RESTORED')
    for signature in state['functions']:
        if _row(cur, signature) != state['functions'][signature]:
            raise ValueError('CP7_PRODUCTION_FUNCTION_NOT_RESTORED: '+signature)


def rehearse(cur, include_paths=None):
    """Mandatory gate on the disposable harness, before any case is counted.

    Does not install A's evolving chain or claim release admission. Both
    directions use the same 22-group catalogue as the owning-chain verifier.
    """
    import cp7_ow04_restore_bundle as catalog
    before = catalog._catalog_rows(cur)
    state = apply(cur, include_paths)
    after = catalog._catalog_rows(cur)
    admit_catalog(before, after, state)
    rollback_preuse(cur, state)
    if catalog._catalog_rows(cur) != before:
        raise ValueError('CP7_PRODUCTION_PREUSE_CATALOG_NOT_EXACTLY_RESTORED')
    state = apply(cur, include_paths)
    admit_catalog(before, catalog._catalog_rows(cur), state)
    return dict(verify(cur, state), preuse_22_groups_exactly_restored=True, sources=state['sources'],
                retained_case_budget_unchanged=True, independent_acceptance=False)
