"""Read every retained and automatic prerequisite before any case starts."""

FUNCTIONS = (
    'public.erp_save_bs_resolution_action_v1(text,jsonb,uuid,bigint)',
    'public.erp_save_laundry_qc_action_v1(text,jsonb,uuid,bigint)',
    'public.erp_cp7_get_purchase_invoices_v1(uuid,integer,integer)',
    'public.erp_cp7_save_purchase_invoice_v1(text,jsonb,uuid,text)',
    'erp.process_cost_recalc_queue(integer)',
    'erp.get_hpp_completeness(uuid)',
)
ACTOR_PERMISSIONS = {
    'upstream_completion_owner': ('production.bs_rework.create', 'production.bs_rework.post', 'production.bs_rework.reverse',
                                  'production.laundry.create', 'production.laundry.post', 'production.final_sku.post'),
    'supplier_invoice_owner': ('warehouse.procurement.view', 'warehouse.procurement.post',
                               'warehouse.procurement.reverse', 'finance.ap.view'),
}
ACTOR_FUNCTIONS = {
    'upstream_completion_owner': FUNCTIONS[:2],
    'supplier_invoice_owner': FUNCTIONS[2:4],
}


def check(cur, today, business, retained, product, native, invoices):
    # The retained nineteen-way check already collects actors, permissions,
    # fixture masters, locations, PCS, accounts, periods, dates and sources.
    original = retained.check(cur, today, business)
    errors = list(original['errors'])
    business.f.admin(cur)
    before = business.n.capture(cur)
    available = {sig: cur.execute('select to_regprocedure(%s) is not null', (sig,)).fetchone()[0] for sig in FUNCTIONS}
    errors.extend('AUTOMATIC_MISSING_FUNCTION:' + sig for sig, found in available.items() if not found)
    bindings = {}
    modules = None
    try:
        fixture, modules = native.context(product)
        bindings = dict(upstream=native.source_contract(fixture, modules), invoices=invoices.source_contract(modules))
    except Exception as error:
        errors.append('AUTOMATIC_NATURAL_CALLER_BINDING_REFUSED')
        bindings = dict(error_type=type(error).__name__, error=str(error))
    actors = {}
    selectors = {} if modules is None else {
        'upstream_completion_owner': lambda: modules.bd.chain.production.owner(cur),
        'supplier_invoice_owner': lambda: modules.invoice.auth.actor(cur, None),
    }
    for name, select_actor in selectors.items():
        cur.execute('savepoint automatic_all_prerequisite_actor')
        try:
            select_actor()
            actor = dict(role=cur.execute('select erp.current_app_role()::text').fetchone()[0],
                         database_role=cur.execute('select current_user,session_user').fetchone(),
                         permissions={key: cur.execute('select erp.has_permission(%s)', (key,)).fetchone()[0]
                                      for key in ACTOR_PERMISSIONS[name]},
                         functions={sig: available[sig] and cur.execute(
                             "select has_schema_privilege(current_user,%s,'USAGE') and has_function_privilege(current_user,%s,'EXECUTE')",
                             (sig.split('.')[0], sig)).fetchone()[0] for sig in ACTOR_FUNCTIONS[name]})
            actors[name] = actor
            if actor['database_role'][0] != 'authenticated' or actor['role'] not in ('OWNER', 'ADMIN'):
                errors.append('AUTOMATIC_ORDINARY_OWNER_ADMIN_REQUIRED:' + name)
            errors.extend('AUTOMATIC_ACTOR_PERMISSION:' + name + ':' + key
                          for key, value in actor['permissions'].items() if value is not True)
            errors.extend('AUTOMATIC_ACTOR_FUNCTION:' + name + ':' + sig
                          for sig, value in actor['functions'].items() if value is not True)
        except Exception as error:
            actors[name] = dict(error_type=type(error).__name__, sqlstate=getattr(error, 'sqlstate', None), error=str(error))
            errors.append('AUTOMATIC_ACTOR_CHECK_REFUSED:' + name)
        finally:
            cur.execute('rollback to savepoint automatic_all_prerequisite_actor')
            cur.execute('release savepoint automatic_all_prerequisite_actor')
            business.f.admin(cur)
    unchanged = business.n.capture(cur) == before
    if not unchanged:
        errors.append('AUTOMATIC_READ_ONLY_PREREQUISITES_CHANGED_CURRENT_BOUNDARY')
    return dict(status='PASS' if not errors else 'REFUSED', errors=errors, retained_money19=original,
                automatic_functions=available, automatic_actors=actors, natural_callers=bindings,
                all_prerequisites_checked_before_first_case=True, source=product.sources(),
                all22_rows_and_all_sequences_unchanged=unchanged, actual_ERP_cases=0, production_go=False)
