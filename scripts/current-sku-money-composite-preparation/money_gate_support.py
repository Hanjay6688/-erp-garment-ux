"""Bind the actual nineteen-case prerequisite Original without importing ERP."""
from datetime import date,datetime,timedelta
from pathlib import Path
import json

HERE=Path(__file__).resolve().parent


def expected():
    value=json.loads((HERE/'EXECUTION_PREREQUISITES.json').read_bytes())
    reference=json.loads((HERE/'SOURCE_REFERENCE.json').read_bytes())
    if value['source']!=reference['files']['scripts/current-sku-cost-money-qualification/native_preflight.py']:
        raise ValueError('CURRENT_MONEY_EXACT_DECLARED_PREFLIGHT_SOURCE')
    return value


def case_ids(runtime,admission):
    runtime.frozen(runtime.FROZEN_SKU,admission.SKU_HEAD,admission.SKU_TREE)
    reference=json.loads((HERE/'SOURCE_REFERENCE.json').read_bytes())
    name='scripts/current-sku-cost-money-qualification/CONFIG.json'
    path=runtime.FROZEN_SKU/name
    if path.is_symlink():raise ValueError('CURRENT_MONEY_CASE_CONFIG_SYMLINK')
    raw=path.read_bytes()
    if admission.pin(raw)!=reference['files'][name]:raise ValueError('CURRENT_MONEY_EXACT_NINETEEN_CONFIG_SOURCE')
    ids=json.loads(raw)['native_case_ids']
    if type(ids)is not list or len(ids)!=19 or len(set(ids))!=19 or ids!=reference['native_case_ids']:
        raise ValueError('CURRENT_MONEY_EXACT_NINETEEN_CASE_IDS')
    return ids


def validate_preflight(p,part,value):
    meta=expected()
    if value.get('synthetic_receipt_not_an_actual_qualification')is True:
        raise ValueError('CURRENT_MONEY_SYNTHETIC_PREFLIGHT_REFUSED')
    p.exact(part['native_prerequisites'],value,'CURRENT_MONEY_COMPLETE_PREFLIGHT_ORIGINAL')
    p.fields(value,dict(status='PASS',errors=[],actual_ERP_cases=0,clock_changed=False,
        posted_financial_fixtures='EXISTING_NATIVE_WRITERS_ONLY',
        source_graph='EXACT_QUALIFIED_PARENT_AND_ALL22_INSTALLATION',
        fixture_offsets_seconds=[-60,-59,-45,-40,-30,-20,-10]),'CURRENT_MONEY_PREFLIGHT_STATUS_AND_SOURCE')
    p.exact(value['functions'],{name:True for name in meta['required_functions']},'CURRENT_MONEY_ALL_23_FUNCTIONS')
    p.exact(set(value['actors']),set(meta['actor_functions']),'CURRENT_MONEY_ALL_THREE_ACTORS')
    for name,functions in meta['actor_functions'].items():
        row=value['actors'][name]
        if row.get('role')not in('OWNER','ADMIN'):raise ValueError('CURRENT_MONEY_NATIVE_ACTOR_APP_ROLE:'+name)
        database=row.get('database_role')
        if type(database)is not list or len(database)!=2 or database[0]!='authenticated' or type(database[1])is not str or not database[1]:
            raise ValueError('CURRENT_MONEY_ORDINARY_AUTHENTICATED_ACTOR_REQUIRED:'+name)
        p.exact(row['direct_call_capabilities'],{sig:True for sig in functions},'CURRENT_MONEY_ACTOR_CAPABILITIES:'+name)
        p.exact(row['permissions'],{key:True for key in meta['permissions'][name]},'CURRENT_MONEY_ACTOR_PERMISSIONS:'+name)
    p.exact(value['account_mappings'],{key:[[True,True]]for key in meta['account_mappings']},'CURRENT_MONEY_ACTIVE_ACCOUNT_MAPPINGS')
    p.exact(value['canonical_location'],[True,'FG_WAREHOUSE'],'CURRENT_MONEY_FG_LOCATION')
    p.exact(value['canonical_product_master'],[True]*5,'CURRENT_MONEY_EFFECTIVE_PRODUCT_MASTER')
    pcs=value['active_PCS']
    if type(pcs)is not list or len(pcs)!=1 or type(pcs[0])is not list or len(pcs[0])!=1 or type(pcs[0][0])is not str or pcs[0][0].upper()!='PCS':
        raise ValueError('CURRENT_MONEY_ONE_COUNT_PCS')
    p.exact(set(value['accounts']),{'4100','5100'},'CURRENT_MONEY_EXACT_LEGACY_ACCOUNTS')
    for code,rows in value['accounts'].items():
        if type(rows)is not list or len(rows)!=1 or type(rows[0])is not list or len(rows[0])!=3:
            raise ValueError('CURRENT_MONEY_SINGLE_ACTIVE_ACCOUNT:'+code)
        p.exact(rows[0][:2],[True,True],'CURRENT_MONEY_ACTIVE_POSTABLE_ACCOUNT:'+code)
    today=date.fromisoformat(value['business_day']);observed=datetime.fromisoformat(value['observed_WIB'])
    if observed.utcoffset()!=timedelta(hours=7)or observed.date()!=today or(observed.hour==0 and observed.minute<5):
        raise ValueError('CURRENT_MONEY_REAL_WIB_FIXTURE_WINDOW')
    p.exact(value['earliest_opening_day'],str(today-timedelta(days=4)),'CURRENT_MONEY_OPENING_DATE')
    p.exact(value['material_receipt_day'],str(today-timedelta(days=6)),'CURRENT_MONEY_MATERIAL_DATE')
    period=value['open_period']
    if type(period)is not list or len(period)!=1 or type(period[0])is not list or len(period[0])!=1:
        raise ValueError('CURRENT_MONEY_SINGLE_ACCOUNTING_PERIOD')
    if period[0][0]is not None and date.fromisoformat(period[0][0])>=today-timedelta(days=4):
        raise ValueError('CURRENT_MONEY_EARLIEST_FIXTURE_PERIOD_CLOSED')
