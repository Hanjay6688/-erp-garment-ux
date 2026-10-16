"""Closed current-authority facades over the accepted pre-sewing cutting inverse and the Native cutting fabric return.

return.sql (SG-02, owner D14-4): leftover fabric of a posted cutting goes back to the warehouse through the accepted
Native erp.post_cutting_material_returns; the command writes only the three physical return columns of the reviewed
group's erp.cutting_group_rolls before that posting. A return can be cancelled or corrected (owner D14-10): the return part
of the accepted Native pre-sewing inverse alone (Native erp.reverse_journal, REVERSAL movements, material cost
recalculation), the three return columns and material_return_posted back to their state before the return, and an
optional corrected return through the same posting, all in one transaction with immutable history.
pickup.sql (SG-01): a POSTED pickup is reversed before any sewing or other use, through the two declared Native deltas
of cp7_pickup_reversal_bundle.py; the group, PO status/stage and Mandor return to their values before the POST.
sewing.sql (D14-14 gap G1): SELESAI DIJAHIT from the connected WIP & Sewing screen through the accepted Native writers
(work rate snapshot, work completion + WORK_COMPLETION wage journal, sewing terminal); cancel through the Native inverses
only while the pieces are still at the Mandor, unpaid and outside an active attendance HPP pool. A Potongan bound to SKU
waves (BF commercial ranges, Sol R2-10) is recorded per SKU instead: one work completion at that SKU's snapshot rates and
one SELESAI_DIJAHIT per SKU line, all lines in one transaction; the single-quantity path refuses it.
finish.sql (D14-14 gap G2): a Production Order is finished from the connected HPP screen through the accepted Native
erp.finish_production_order (HPP rebuild, conversion HPP, HPP to GL, residual WIP close) once its Native preconditions hold;
the PO must end FINISHED with a zero WIP balance. Its workspace also carries the predicate of the Native trigger
erp.guard_finished_po_source_accounting (Astra ASTRA-C17-05).
po-reopen.sql (owner D15-4, Fable FABLE-014): a FINISHED PO is reopened from the same screen through the accepted Native
erp.reopen_production_order (residual-close journals reversed, PO back to its stage), refused while its finished goods are
used, or the reversal would reach a closed period; the PO must end not FINISHED with its WIP up by the reversed residual.
auto-po.sql (owner D15-6, Sol SOL-R1-002): Buat Potongan creates its Production Order when the cutting is posted, in one
transaction with the accepted Native cutting POST (PO inserted DRAFT at CUTTING as the Native initial-state guard requires,
then CUTTING as the Native lifecycle derives for a posted, not picked-up cutting); drafts stay in this schema only.
"""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ROLES=('cp7_cutting_write','cp7_cutting_read')
SCHEMA='cp7_cutting_correction'
TABLES=('requests','history','return_requests','return_history','return_reversal_requests','return_reversal_history','pickup_requests','pickup_history','pickup_context','sewing_requests','sewing_history','sewing_wave_history','finish_requests','finish_history','po_reopen_requests','po_reopen_history','auto_po_requests','auto_po_drafts','auto_po_history')
RETURN_COLUMNS=('qty_physically_returned','return_destination','returned_at')
def extension():return '\n'.join((ROOT/'scripts/cp7-src/cutting-correction'/name).read_text()for name in('reopen.sql','return.sql','pickup.sql','sewing.sql','finish.sql','po-reopen.sql','auto-po.sql'))
def verify(cur):
    expected={'access_now':(True,'v',False),'immutable':(False,'v',False),
        'snapshot':(True,'s',True),'workspace':(True,'v',False),'command':(True,'v',False),
        'return_workspace':(True,'v',True),'return_command':(True,'v',True),'post_return_rolls':(True,'v',True),
        'return_reversal_workspace':(True,'v',True),'return_reversal_command':(True,'v',True),
        'pickup_access_now':(True,'v',False),'pickup_reversal_admitted':(True,'s',False),'pickup_group_admitted':(True,'s',False),
        'pickup_post_audit':(True,'s',True),'pickup_snapshot':(True,'s',True),'pickup_workspace':(True,'v',True),'pickup_command':(True,'v',True),
        'sewing_access_now':(True,'v',False),'sewing_wave_at':(True,'s',True),'sewing_snapshot':(True,'s',True),'sewing_event_blocker':(True,'i',False),'sewing_workspace':(True,'v',True),'sewing_command':(True,'v',True),
        'finish_access_now':(True,'v',False),'finish_snapshot':(True,'s',True),'finish_hpp':(True,'i',False),'finish_list':(True,'v',True),
        'finish_workspace':(True,'v',True),'finish_command':(True,'v',True),
        'reopen_po_snapshot':(True,'s',True),'reopen_po_workspace':(True,'v',True),'reopen_po_command':(True,'v',True),
        'auto_po_access_now':(True,'v',False),'auto_po_cutting':(True,'s',False),'auto_po_workspace':(True,'v',True),'auto_po_command':(True,'v',True)}
    rows=cur.execute("select p.oid::regprocedure::text,p.proname,pg_get_userbyid(p.proowner),p.prosecdef,p.provolatile::text,p.proconfig from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname=%s",(SCHEMA,)).fetchall()
    assert {r[1]for r in rows}==set(expected),rows
    for sig,name,owner,secdef,vol,config in rows:
        security,volatility,utc=expected[name]
        assert(owner,secdef,vol,config)==('postgres',security,volatility,['search_path=""']+(['TimeZone=UTC']if utc else[])),sig
        for who in('anon','authenticated','service_role','cp7_capture','cp7_transaction_source_read'):
            assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,sig)).fetchone()[0],(who,sig)
        for who,allowed in(('cp7_cutting_read',('workspace','return_workspace','return_reversal_workspace','pickup_workspace','sewing_workspace','finish_list','finish_workspace','reopen_po_workspace','auto_po_workspace')),('cp7_cutting_write',('command','return_command','return_reversal_command','pickup_command','sewing_command','finish_command','reopen_po_command','auto_po_command'))):
            assert cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,sig)).fetchone()[0]==(name in allowed),(who,sig)
    for who in ROLES:
        assert cur.execute('select rolcanlogin,rolinherit,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls from pg_roles where rolname=%s',(who,)).fetchone()==(False,False,False,False,False,False,False)
        assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp'and c.relkind in('r','p','v')and has_table_privilege(%s,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'))",(who,)).fetchone()[0],who
        assert not cur.execute("select has_function_privilege(%s,'erp.reverse_cutting_material_flow_before_sewing_v2(uuid,text,uuid,bigint)','EXECUTE')",(who,)).fetchone()[0],who
    for table in TABLES:
        relation=SCHEMA+'.'+table
        assert cur.execute('select pg_get_userbyid(relowner),relrowsecurity from pg_class where oid=%s::regclass',(relation,)).fetchone()==('postgres',True)
        assert cur.execute("select count(*)from pg_policy where polrelid=%s::regclass and pg_get_expr(polqual,polrelid)='false'and pg_get_expr(polwithcheck,polrelid)='false'",(relation,)).fetchone()[0]==1
        for who in('anon','authenticated','service_role','cp7_capture','cp7_transaction_source_read')+ROLES:
            assert not cur.execute('select has_table_privilege(%s,%s,\'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER\')',(who,relation)).fetchone()[0],(who,relation)
    for history in('history','return_history','return_reversal_history','pickup_history','sewing_history','sewing_wave_history','finish_history','po_reopen_history','auto_po_history'):
        assert cur.execute('select count(*)from pg_trigger where tgrelid=%s::regclass and tgfoid=%s::regprocedure and not tgisinternal',(SCHEMA+'.'+history,SCHEMA+'.immutable()')).fetchone()[0]==2
    for signature,owner in(('public.erp_cp7_get_cutting_correction_v1(uuid)','cp7_cutting_read'),('public.erp_cp7_reopen_cutting_v1(jsonb,uuid,text)','cp7_cutting_write'),
                           ('public.erp_cp7_get_cutting_return_v1(uuid)','cp7_cutting_read'),('public.erp_cp7_return_cutting_fabric_v1(jsonb,uuid,text)','cp7_cutting_write'),
                           ('public.erp_cp7_get_cutting_return_reversal_v1(uuid)','cp7_cutting_read'),('public.erp_cp7_reverse_cutting_return_v1(jsonb,uuid,text)','cp7_cutting_write'),
                           ('public.erp_cp7_get_pickup_reversal_v1(uuid)','cp7_cutting_read'),('public.erp_cp7_reverse_pickup_v1(jsonb,uuid,text)','cp7_cutting_write'),
                           ('public.erp_cp7_get_sewing_completion_v1(uuid)','cp7_cutting_read'),('public.erp_cp7_save_sewing_completion_v1(jsonb,uuid,text)','cp7_cutting_write'),
                           ('public.erp_cp7_list_po_finish_v1(text,integer)','cp7_cutting_read'),('public.erp_cp7_get_po_finish_v1(uuid)','cp7_cutting_read'),
                           ('public.erp_cp7_finish_po_v1(jsonb,uuid)','cp7_cutting_write'),
                           ('public.erp_cp7_get_po_reopen_v1(uuid)','cp7_cutting_read'),('public.erp_cp7_reopen_po_v1(jsonb,uuid)','cp7_cutting_write'),
                           ('public.erp_cp7_get_cutting_auto_po_v1(jsonb)','cp7_cutting_read'),('public.erp_cp7_save_cutting_auto_po_v1(jsonb,uuid)','cp7_cutting_write')):
        assert cur.execute('select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig from pg_proc where oid=%s::regprocedure',(signature,)).fetchone()==(owner,True,'v',['search_path=""'])
        assert cur.execute('select has_function_privilege(\'authenticated\',%s,\'EXECUTE\')',(signature,)).fetchone()[0]
        for who in('anon','service_role','cp7_capture','cp7_transaction_source_read'):
            assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,signature)).fetchone()[0],(who,signature)
    return dict(current_owner_authority_before_after_waits=True,Native_inverse_unchanged=True,
        closed_private_cutting_facades=True,no_direct_Native_grants=True,immutable_original_source=True,
        reopen_without_ERP_DML=True,fabric_return_DML_only=dict(table='erp.cutting_group_rolls',columns=list(RETURN_COLUMNS)),
        fabric_return_Native_posting_unchanged='erp.post_cutting_material_returns(uuid,uuid)',
        fabric_return_cancel=dict(Native_journal_reversal='erp.reverse_journal(uuid,text)',movement_insert='erp.material_stock_movements REVERSAL (CUTTING_GROUP_RETURN_REVERSAL)',
            reset=dict(table='erp.cutting_group_rolls',columns=list(RETURN_COLUMNS)),flag='erp.cutting_groups.material_return_posted',cost='erp.recalculate_material_cost(uuid)'),
        pickup_reversal=dict(table_DML=['erp.cutting_pickups','erp.cutting_groups','erp.production_orders'],declared_Native_deltas='cp7_pickup_reversal_bundle.py'),
        sewing_completion=dict(table_DML=['erp.work_completion_events (DRAFT insert)','erp.work_completion_lines'],
            Native_writers=['erp.ensure_po_work_component_snapshots_v2(uuid,timestamp with time zone,uuid)','erp.post_work_completion(uuid)',
                'erp.record_sewing_terminal_v1(jsonb,uuid)','erp.reverse_sewing_terminal_v1(uuid,text,uuid,bigint)','erp.reverse_work_completion(uuid,text)'],
            wave_per_SKU='RECORD_WAVE: one completion per SKU on the SKU snapshot (erp.bf_ensure_work_v1 through the same ensure), rates previewed by sewing_wave_at'),
        po_finish=dict(table_DML=[],Native_writers=['erp.finish_production_order(uuid)'],post_conditions=['PO FINISHED','PO WIP balance 0'],
            preflight_includes='erp.guard_finished_po_source_accounting predicate'),
        po_reopen=dict(table_DML=[],Native_writers=['erp.reopen_production_order(uuid,text)'],blockers=['NOT_FINISHED','FG_USED','PERIOD_CLOSED'],
            post_conditions=['PO not FINISHED','no POSTED PO_WIP_RESIDUAL_CLOSE journal left','PO WIP up by the reversed residual']),
        auto_po=dict(table_DML=['erp.production_orders (insert DRAFT at CUTTING, then status CUTTING)'],
            Native_writers=['public.erp_save_cutting_group_before_sewing_v2(jsonb,uuid,bigint) action POST'],
            drafts='cp7_cutting_correction.auto_po_drafts only (no ERP row, stock or journal)',
            post_conditions=['one new PO','its Potongan POSTED with the material issue','pieces = PO target','PO CUTTING']))
