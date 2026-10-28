"""Private opt-in finance on the exact full A frozen-unit predecessor."""
from hashlib import sha256
from pathlib import Path
import json
from cp7_production_stage import _row, _body
import cp7_current_frozen_units as inputs
import cp7_current_frozen_units_installation as parent
from . import render

ROOT = Path(__file__).resolve().parent
CONTRACT = 'cp7.current-frozen-official-finance-private.v1'
USED_ERROR = 'CURRENT_FROZEN_FINANCE_DELTA_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'
catalog = parent.catalog
NEW = {render.SOURCE:'s', render.FINANCE:'v'}


def sources():
    return dict(contract=CONTRACT, bound_inputs=inputs.sources(),
                files={p.name:sha256(p.read_bytes()).hexdigest() for p in sorted(ROOT.iterdir())
                       if p.is_file() and p.suffix in ('.py','.sql','.json')})


def verify_sources():
    if ((ROOT/'bridge.sql').read_text() != render.render()
            or json.loads((ROOT/'MANIFEST.json').read_bytes()) != render.manifest()):
        raise ValueError('CURRENT_FROZEN_FINANCE_GENERATED_SOURCE_CHANGED')
    return sources()


def admit_catalog(before, after, state):
    if set(before) != set(after) or len(before) != 22:
        raise ValueError('CURRENT_FROZEN_FINANCE_FULL22_REQUIRED')
    changed = set()
    for group in before:
        for key in set(before[group]) | set(after[group]):
            left, right = before[group].get(key), after[group].get(key)
            if left == right:
                continue
            changed.add((group,key))
            if group == 'functions' and key in render.originals():
                if left is not None and right is not None and left[1:] == right[1:] and right == state['after'][group][key]:
                    continue
            if left is None and right is not None and right == state['after'][group].get(key):
                if group == 'schemas' and key == render.SCHEMA:
                    continue
                if group == 'functions' and key in NEW:
                    continue
            raise ValueError('CURRENT_FROZEN_FINANCE_UNDECLARED_DELTA:'+group+':'+key)
    expected = {('schemas',render.SCHEMA)} | {('functions',k) for k in render.definitions()}
    if changed != expected:
        raise ValueError('CURRENT_FROZEN_FINANCE_INCOMPLETE_DELTA')


def verify(cur, state):
    catalog._authority(cur)
    if state['sources'] != verify_sources() or catalog._catalog_rows(cur) != state['after']:
        raise ValueError('CURRENT_FROZEN_FINANCE_SOURCE_OR_FULL22_CHANGED')
    originals, definitions = render.originals(), render.definitions()
    if set(state['old_rows']) != set(originals) or set(state['rows']) != set(definitions):
        raise ValueError('CURRENT_FROZEN_FINANCE_FUNCTION_SET_CHANGED')
    admit_catalog(state['before'], state['after'], state)
    for signature, definition in definitions.items():
        row = _row(cur, signature)
        if (row != state['rows'][signature] or row[1] != _body(definition)
                or row[0] != state['after']['functions'][signature][0]):
            raise ValueError('CURRENT_FROZEN_FINANCE_FUNCTION_CHANGED:'+signature)
        if signature in originals:
            old = state['old_rows'][signature]
            if (old[1] != _body(originals[signature]) or old[2:] != row[2:]
                    or old[0] != state['before']['functions'][signature][0]):
                raise ValueError('CURRENT_FROZEN_FINANCE_PREDECESSOR_AUTHORITY_CHANGED:'+signature)
        elif row[2:6] != ['cp7_capture',False,NEW[signature],['search_path=""','TimeZone=UTC']]:
            raise ValueError('CURRENT_FROZEN_FINANCE_PRIVATE_AUTHORITY_CHANGED:'+signature)
        for role in ('anon','authenticated','service_role','cp7_alert'):
            if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,signature)).fetchone()[0]:
                raise ValueError('CURRENT_FROZEN_FINANCE_EXECUTE_EXPOSED:'+signature+':'+role)
    if cur.execute('select pg_get_userbyid(nspowner)from pg_namespace where nspname=%s',(render.SCHEMA,)).fetchone() != ('cp7_capture',):
        raise ValueError('CURRENT_FROZEN_FINANCE_SCHEMA_OWNER_CHANGED')
    for role in ('anon','authenticated','service_role','cp7_alert'):
        if cur.execute("select has_schema_privilege(%s,%s,'USAGE')",(role,render.SCHEMA)).fetchone()[0]:
            raise ValueError('CURRENT_FROZEN_FINANCE_SCHEMA_EXPOSED:'+role)
    for group, keys in (('schemas',[render.SCHEMA]),('functions',NEW)):
        for key in keys:
            for grant in state['after'][group][key][-1]:
                if grant[0] != 'cp7_capture' or grant[1] != 'cp7_capture' or grant[3] is not False:
                    raise ValueError('CURRENT_FROZEN_FINANCE_UNDECLARED_GRANT:'+key)
    return dict(contract=CONTRACT, exact_full22=True, new_private_functions=2,
                existing_private_replacements=2, new_public_rpcs=0, new_tables=0,
                financial_math_added=False, official_finance_capture_reused=True,
                finance_mode_bound_before_first_seal=True, production_go=False)


def _locks(cur):
    catalog._authority(cur)
    cur.execute("select pg_advisory_xact_lock(hashtextextended('CP7:OW15:COMPOSITION',0))")
    cur.execute("select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))")
    catalog._lock_tables(cur)


def install_delta(cur, predecessor_checker):
    if not callable(predecessor_checker):
        raise ValueError('CURRENT_FROZEN_FINANCE_ACTUAL_PREDECESSOR_REQUIRED')
    with parent.atomic(cur):
        _locks(cur)
        predecessor_checker(cur)
        pins = verify_sources()
        if cur.execute('select to_regnamespace(%s)is not null',(render.SCHEMA,)).fetchone()[0]:
            raise ValueError('CURRENT_FROZEN_FINANCE_ALREADY_INSTALLED')
        if cur.execute("select exists(select 1 from cp7_analysis_stage.jobs where state='RUNNING')or exists(select 1 from cp7_analysis_jobs.jobs where state='WAITING')").fetchone()[0]:
            raise ValueError('CURRENT_FROZEN_FINANCE_QUIET_INSTALL_REQUIRED')
        originals = render.originals()
        old = {key:_row(cur,key) for key in originals}
        for key, definition in originals.items():
            if old[key][1] != _body(definition) or old[key][2] != 'cp7_capture':
                raise ValueError('CURRENT_FROZEN_FINANCE_ACTUAL_PREDECESSOR_CHANGED:'+key)
        before, data = catalog._catalog_rows(cur), catalog._data(cur)
        cur.execute((ROOT/'bridge.sql').read_text(),prepare=False)
        state = dict(sources=pins, before=before, after=catalog._catalog_rows(cur),
                     old_rows=old, rows={k:_row(cur,k) for k in render.definitions()},
                     preuse_data_and_sequences=data)
        if catalog._data(cur) != data:
            raise ValueError('CURRENT_FROZEN_FINANCE_INSTALL_CHANGED_ROWS_OR_SEQUENCES')
        verify(cur,state)
        return state


def rollback_preuse(cur, state):
    with parent.atomic(cur):
        _locks(cur)
        verify(cur,state)
        if catalog._data(cur) != state['preuse_data_and_sequences']:
            raise ValueError(USED_ERROR)
        for row in state['old_rows'].values():
            cur.execute(row[0],prepare=False)
        for key in (render.FINANCE,render.SOURCE):
            cur.execute('drop function '+key+' restrict')
        cur.execute('drop schema '+render.SCHEMA+' restrict')
        if (catalog._catalog_rows(cur) != state['before']
                or catalog._data(cur) != state['preuse_data_and_sequences']):
            raise ValueError('CURRENT_FROZEN_FINANCE_INVERSE_NOT_EXACT')
        return dict(status='EXACT_PRIVATE_FROZEN_FINANCE_INVERSE',
                    all22_equal=True, all_rows_and_sequences_equal=True,
                    used_guard_before_any_DDL=True, production_go=False)
