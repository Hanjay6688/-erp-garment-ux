"""Native current-context precedence controls inside existing private cases.

The predecessor retains every installed guard byte except the declared early
branch and uses the unchanged full access document for its late sales branch.
Temporary comparison functions, contexts and profiles are all rolled back.
No Native business writer or case budget is replaced or extended.
"""
import hashlib
import json
import re
import uuid
import cp6_auditor_runner as native
import cp7_sales_bundle as sales
from cp7_catalog_state import exact_public_catalog

CONTEXTS = (
    ('erp.cutting_bridge_execution_context', 'POST_CUTTING', ('production.cutting.post',)),
    ('erp.bs_resolution_execution_context', 'SAVE_REWORK', ('production.bs_rework.create',)),
    ('erp.cp6_laundry_qc_execution_context', 'POST_RECEIPT', ('production.laundry.post',)),
    ('cp7_procurement.execution_context', 'POST', ('warehouse.procurement.view', 'warehouse.procurement.post')),
    ('cp7_material.execution_context', 'POST_COUNT', ('warehouse.material.view', 'warehouse.stock.adjust')),
    ('cp7_supplier_return.execution_context', 'POST', ('warehouse.procurement.view', 'warehouse.procurement.reverse')),
    ('cp7_payroll.execution_context', 'POST_NOTE', ('production.fg_handoff.view', 'production.fg_handoff.post')),
    ('cp7_payroll.settlement_context', 'APPROVE', ('finance.payroll.view', 'finance.payroll.approve')),
    ('cp7_attendance.command_context', 'SAVE', ('finance.attendance.view', 'finance.attendance.create')),
)
SALES_RIGHTS = ('sales.invoice.view', 'finance.ar.view', 'sales.invoice.post')


def compare(cur, auth, api, boundary):
    with exact_public_catalog(native, retain_raw=True, retain_locations=True) as audit:
        return _compare(cur, auth, api, boundary, audit)


def _compare(cur, auth, api, boundary, audit):
    api.admin(cur)
    before = boundary.snapshot(cur)
    public_before = native.public_state(cur)
    definition = cur.execute("select pg_get_functiondef('erp.require_internal()'::regprocedure)").fetchone()[0]
    blocks = re.findall(r' if exists\(select 1 from cp7_sales.command_context.*?then return;end if;\n', definition, re.S)
    assert len(blocks) == 2 and 'not exists(' in blocks[0] and blocks[1] == sales.ADMISSION
    predecessor = definition.replace(blocks[0], '', 1)
    preceding = re.findall(r'\bfrom\s+([a-z0-9_]+\.[a-z0-9_]*context)\s+c\b', predecessor.split(sales.ANCHOR, 1)[0])
    # Exclude the late sales branch from the complete ordered predecessor list.
    assert preceding[-1] == 'cp7_sales.command_context'
    preceding = preceding[:-1]
    assert preceding in ([r[0] for r in CONTEXTS[:6]], [r[0] for r in CONTEXTS])
    assert blocks[0] == sales.early_admission(predecessor.replace(sales.ADMISSION, '', 1))
    needle = 'then cp7_sales.command_allowed(c.action) else false end)'
    assert predecessor.count(needle) == 1
    predecessor = predecessor.replace(needle, 'then cp7_sales.command_access(c.action) is not null else false end)', 1)
    cur.execute('savepoint p19_dispatch_equivalence')
    decisions = []
    try:
        assert cur.execute("select to_regprocedure('public.cp7_p19_guard_control_v1(boolean)') is null").fetchone()[0]
        cur.execute(predecessor.replace('erp.require_internal()', 'cp7_sales.p19_dispatch_predecessor()', 1), prepare=False)
        cur.execute("""alter function cp7_sales.p19_dispatch_predecessor() owner to postgres;
          revoke all on function cp7_sales.p19_dispatch_predecessor() from public;
          create function public.cp7_p19_guard_control_v1(candidate boolean) returns jsonb
          language plpgsql security definer set search_path='' as $$begin
            if candidate then perform erp.require_internal();else perform cp7_sales.p19_dispatch_predecessor();end if;
            return jsonb_build_array('ALLOW');
          exception when others then return jsonb_build_array(SQLSTATE,SQLERRM);end$$;
          alter function public.cp7_p19_guard_control_v1(boolean) owner to postgres;
          revoke all on function public.cp7_p19_guard_control_v1(boolean) from public;
          grant execute on function public.cp7_p19_guard_control_v1(boolean) to authenticated;""", prepare=False)
        subject, role = auth.custom_actor(cur)
        auth.actor(cur, subject)
        api.admin(cur)
        actor_key = cur.execute('select erp._idempotency_actor_key()').fetchone()[0]
        pid, tx = cur.execute('select pg_backend_pid(),txid_current()').fetchone()

        def permissions(keys):
            api.admin(cur)
            cur.execute('delete from erp.app_role_permissions where role_id=%s', (role,))
            for key in set(keys):
                cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s)', (role, key))

        def insert(row, foreign_actor=False, foreign_tx=False, foreign_pid=False):
            table, action, rights = row
            values = dict(backend_pid=pid + int(foreign_pid), transaction_id=tx + int(foreign_tx), action=action)
            if table.startswith('erp.'):
                values['actor_key'] = 'p19-foreign:' + str(uuid.uuid4()) if foreign_actor else actor_key
            else:
                values['actor'] = str(uuid.uuid4()) if foreign_actor else subject
            if table != 'cp7_payroll.settlement_context':
                values['permission' if table == 'cp7_attendance.command_context' else 'permission_key'] = rights[-1]
            if table == 'erp.cp6_laundry_qc_execution_context':
                values.update(client_request_id=uuid.uuid4(), payload=json.dumps({}))
            elif table == 'cp7_payroll.settlement_context':
                values['payroll_id'] = uuid.uuid4()
            elif table == 'cp7_attendance.command_context':
                values.update(contractor_id=uuid.uuid4(), owner_required=False)
            cur.execute('insert into '+table+'('+','.join(values)+') values('+','.join(['%s']*len(values))+')', tuple(values.values()))

        def pair(label, expected):
            auth.actor(cur, subject)
            old = cur.execute('select public.cp7_p19_guard_control_v1(false)').fetchone()[0]
            new = cur.execute('select public.cp7_p19_guard_control_v1(true)').fetchone()[0]
            assert old == new, ('P19_NATIVE_DISPATCH_DIFFERENCE', label, old, new)
            assert old == expected, ('P19_PREDECLARED_DISPATCH_ORACLE', label, old, expected)
            decisions.append(dict(state=label, decision=old))
            api.admin(cur)

        denied = ['42501', 'CP7_SALES_WRITE_DENIED']
        selected = CONTEXTS[:len(preceding)]
        for row in selected:
            for state in ('PRIOR_ALLOW_SALES_DENIED', 'BOTH_ALLOW', 'PRIOR_REVOKED_SALES_ALLOW', 'BOTH_REVOKED',
                          'FOREIGN_ACTOR_SALES_ALLOW', 'FOREIGN_ACTOR_SALES_DENIED', 'FOREIGN_TX_SALES_ALLOW', 'FOREIGN_PID_SALES_ALLOW'):
                cur.execute('savepoint p19_dispatch_row')
                keys = list(SALES_RIGHTS)
                if state in ('PRIOR_ALLOW_SALES_DENIED', 'BOTH_REVOKED', 'FOREIGN_ACTOR_SALES_DENIED'):
                    keys.remove('finance.ar.view')
                if state not in ('PRIOR_REVOKED_SALES_ALLOW', 'BOTH_REVOKED'):
                    keys.extend(row[2])
                permissions(keys)
                insert(row, foreign_actor=state.startswith('FOREIGN_ACTOR'), foreign_tx=state.startswith('FOREIGN_TX'), foreign_pid=state.startswith('FOREIGN_PID'))
                cur.execute("insert into cp7_sales.command_context(backend_pid,transaction_id,actor,action) values(%s,%s,%s,'POST')", (pid,tx,subject))
                expected = denied if state in ('BOTH_REVOKED', 'FOREIGN_ACTOR_SALES_DENIED') else ['ALLOW']
                pair(row[0]+':'+state, expected)
                cur.execute('rollback to savepoint p19_dispatch_row;release savepoint p19_dispatch_row')
        for state in ('ALL_PRIOR_ALLOW_SALES_DENIED', 'ALL_PRIOR_REVOKED', 'NO_CONTEXT_FORGED_GUC'):
            cur.execute('savepoint p19_dispatch_row')
            keys = ['sales.invoice.view','sales.invoice.post']
            if state == 'ALL_PRIOR_ALLOW_SALES_DENIED':
                keys.extend(k for row in selected for k in row[2])
            permissions(keys)
            if state != 'NO_CONTEXT_FORGED_GUC':
                for row in selected:
                    insert(row)
                cur.execute("insert into cp7_sales.command_context(backend_pid,transaction_id,actor,action) values(%s,%s,%s,'POST')", (pid,tx,subject))
            cur.execute("select set_config('app.role','OWNER',true)")
            pair(state, ['ALLOW'] if state == 'ALL_PRIOR_ALLOW_SALES_DENIED' else (
                ['P0001','Internal ERP access required'] if state == 'NO_CONTEXT_FORGED_GUC' else denied))
            cur.execute('rollback to savepoint p19_dispatch_row;release savepoint p19_dispatch_row')
    finally:
        api.admin(cur)
        cur.execute('rollback to savepoint p19_dispatch_equivalence;release savepoint p19_dispatch_equivalence')
    assert boundary.snapshot(cur) == before and native.public_state(cur) == public_before
    assert len(decisions) == 8*len(preceding)+3
    return dict(status='EXACT_NATIVE_CONTEXT_PRECEDENCE_AND_REFUSALS', comparisons=len(decisions), decisions=decisions,
                predecessor_definition_sha256=hashlib.sha256(predecessor.encode()).hexdigest(),
                candidate_definition_sha256=hashlib.sha256(definition.encode()).hexdigest(),
                preceding_contexts=preceding, current_permissions_not_cached=True,
                raw_public_catalog_and_function_identities=audit,
                temporary_fixture_functions_and_profiles_rolled_back=True, full_boundary_and_public_catalog_restored=True,
                Native_business_engines_changed=False, Native_case_credit_added=0)
