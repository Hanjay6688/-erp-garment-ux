"""Check the supplier and accessory fixture prerequisites before committed setup."""


ACCOUNTS = ('AP_SUPPLIER', 'GRNI_MATERIAL', 'MATERIAL_INVENTORY', 'OPENING_EQUITY')
SUPPLIER_ROUTES = (
    'public.erp_cp7_save_procurement_v1(text,jsonb,uuid,text)',
    'public.erp_cp7_get_supplier_transfer_v1(jsonb)',
    'public.erp_cp7_save_supplier_transfer_v1(jsonb,uuid)',
    'public.erp_cp7_get_supplier_payments_v1(uuid,text,integer,uuid)',
    'public.erp_cp7_reverse_supplier_payment_v1(jsonb,uuid)',
    'public.erp_cp7_get_supplier_payment_create_v1(jsonb)',
    'public.erp_cp7_create_supplier_payment_v1(jsonb,uuid)',
    'public.erp_cp7_get_supplier_payment_correction_v1(jsonb)',
    'public.erp_cp7_correct_supplier_payment_v1(jsonb,uuid)',
)
S05_ROUTE = 'public.erp_cp7_get_accessory_standard_report_v1(date,date,uuid,uuid,text,integer,integer)'
ROUTES = (*SUPPLIER_ROUTES, S05_ROUTE)

MAPPINGS_SQL = '''select m.mapping_key,a.is_active,a.is_postable
    from erp.accounting_account_mappings m
    left join erp.chart_accounts a on a.id=m.account_id
    where m.mapping_key=any(%s::text[])
    order by m.mapping_key collate "C"'''

ROUTES_SQL = '''select r.signature,p.oid is not null,
        has_schema_privilege('authenticated',p.pronamespace,'USAGE')
            and has_function_privilege('authenticated',p.oid,'EXECUTE')
    from unnest(%s::text[]) as r(signature)
    left join pg_proc p on p.oid=to_regprocedure(r.signature)
    order by r.signature collate "C"'''


def observe(cur):
    accounts = {name: [] for name in ACCOUNTS}
    for name, active, postable in cur.execute(MAPPINGS_SQL, (list(ACCOUNTS),)).fetchall():
        accounts[name].append([active, postable])
    routes = {name: dict(installed=exists, authenticated_execute=execute)
              for name, exists, execute in cur.execute(ROUTES_SQL, (list(ROUTES),)).fetchall()}
    if set(routes) != set(ROUTES):
        raise ValueError('GLOBAL_SNAPSHOT_COMPLETE_ROUTE_CHECK_REQUIRED')
    errors = [f'ACTIVE_POSTABLE_ACCOUNT_MAPPING_REQUIRED:{name}' for name, rows in accounts.items()
              if rows != [[True, True]]]
    for name, row in routes.items():
        if row['installed'] is not True or row['authenticated_execute'] is not True:
            errors.append('GLOBAL_SNAPSHOT_PUBLIC_RPC_NOT_AVAILABLE:' + name)
    return dict(status='PASS' if not errors else 'REFUSED', accounts=accounts, routes=routes, errors=errors,
                app_user_permissions_and_real_Auth_separately_observed_by_case=True, actual_business_cases=0)
