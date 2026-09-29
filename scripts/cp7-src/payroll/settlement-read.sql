-- P12 finance-owned payroll review. Not included in Nota/source bundles.
-- Financial amounts are native snapshots. This reader never populates, approves,
-- pays, or recalculates a payroll as a read side effect.
grant select on erp.payroll_attendance_items,erp.payroll_reimbursements,
 erp.payroll_deductions,erp.cash_accounts to cp7_payroll_read;

create function cp7_payroll.settlement_token(p_id uuid) returns text
language sql stable security invoker set search_path='' as $$
 select md5(jsonb_build_array(
  p.id,p.xmin::text,p.row_version,
  (select coalesce(jsonb_agg(jsonb_build_array(i.id,i.xmin::text) order by i.id),'[]') from erp.payroll_work_items i where i.payroll_id=p.id),
  (select coalesce(jsonb_agg(jsonb_build_array(i.id,i.xmin::text) order by i.id),'[]') from erp.payroll_attendance_items i where i.payroll_id=p.id),
  (select coalesce(jsonb_agg(jsonb_build_array(i.id,i.xmin::text) order by i.id),'[]') from erp.payroll_reimbursements i where i.payroll_id=p.id),
  (select coalesce(jsonb_agg(jsonb_build_array(i.id,i.xmin::text) order by i.id),'[]') from erp.payroll_deductions i where i.payroll_id=p.id),
  (select coalesce(jsonb_agg(jsonb_build_array(n.id,n.row_version) order by n.id),'[]') from cp7_payroll.notes n where n.posted_payroll_id=p.id)
 )::text) from erp.payroll_settlements p where p.id=p_id
$$;

create function cp7_payroll.settlement_document(p_id uuid) returns jsonb
language sql stable security invoker set search_path='' as $$
 select jsonb_build_object('id',p.id,'payroll_number',p.payroll_number,'contractor_id',p.contractor_id,'contractor_name',c.contractor_name,
  'attendance_required',c.attendance_required,'period_start',p.period_start,'period_end',p.period_end,'status',p.status,'row_version',p.row_version::text,
  'review_token',cp7_payroll.settlement_token(p.id),'notes',p.notes,'labor_total',p.labor_total::text,'attendance_total',p.attendance_total::text,
  'reimburse_total',p.reimburse_total::text,'deduction_total',p.deduction_total::text,'manual_adjustment',p.manual_adjustment::text,'net_payable',p.net_payable::text,
  'payment_cash_account_id',p.payment_cash_account_id,'payment_cash_account_name',a.cash_account_name,'payment_date',p.payment_date,
  'settled_at',to_char(p.settled_at at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
  'created_at',to_char(p.created_at at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
  'updated_at',to_char(p.updated_at at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
  'totals_match_items',p.labor_total=(select coalesce(sum(i.amount),0) from erp.payroll_work_items i where i.payroll_id=p.id)
   and p.attendance_total=case when c.attendance_required then(select coalesce(sum(i.amount),0) from erp.payroll_attendance_items i where i.payroll_id=p.id) else 0 end
   and p.reimburse_total=(select coalesce(sum(i.amount),0) from erp.payroll_reimbursements i where i.payroll_id=p.id)
   and p.deduction_total=(select coalesce(sum(i.amount),0) from erp.payroll_deductions i where i.payroll_id=p.id),
  'counts',jsonb_build_object(
   'work',(select count(*)::text from erp.payroll_work_items i where i.payroll_id=p.id),
   'attendance',(select count(*)::text from erp.payroll_attendance_items i where i.payroll_id=p.id),
   'reimbursements',(select count(*)::text from erp.payroll_reimbursements i where i.payroll_id=p.id),
   'deductions',(select count(*)::text from erp.payroll_deductions i where i.payroll_id=p.id),
   'notes',(select count(*)::text from cp7_payroll.notes n where n.posted_payroll_id=p.id)))
 from erp.payroll_settlements p join erp.contractors c on c.id=p.contractor_id
 left join erp.cash_accounts a on a.id=p.payment_cash_account_id where p.id=p_id
$$;

create function cp7_payroll.settlement_rows(p_section text,p_id uuid) returns table(id uuid,ordering text,data jsonb)
language sql stable security invoker set search_path='' as $$
 select i.id,concat_ws(':',i.source_type,i.id),jsonb_build_object('id',i.id,'po_id',i.po_id,'po_number',p.po_number,
  'component_id',i.work_component_id,'component_code',c.component_code,'component_name',c.component_name,
  'source_type',i.source_type,'source_id',i.source_id,'qty',i.qty_payable::text,'rate',i.rate_snapshot::text,'amount',i.amount::text)
 from erp.payroll_work_items i join erp.work_components c on c.id=i.work_component_id left join erp.production_orders p on p.id=i.po_id
 where p_section='WORK' and i.payroll_id=p_id
 union all
 select i.id,concat_ws(':',i.attendance_date_snapshot,i.worker_id,i.id),jsonb_build_object('id',i.id,'worker_id',i.worker_id,
  'attendance_record_id',i.attendance_record_id,'date',i.attendance_date_snapshot,'worker_name',i.worker_name_snapshot,
  'job_description',i.job_description_snapshot,'paid_fraction',i.paid_fraction_snapshot::text,'daily_rate',i.daily_rate_snapshot::text,
  'rate_version_id',i.worker_rate_version_id,'amount',i.amount::text)
 from erp.payroll_attendance_items i where p_section='ATTENDANCE' and i.payroll_id=p_id
 union all
 select i.id,i.id::text,jsonb_build_object('id',i.id,'amount',i.amount::text,'description',i.description,'source_type',i.source_type,
  'source_id',i.source_id,'po_id',i.po_id,'opening_payable_balance_id',i.opening_payable_balance_id,
  'opening_carry_entitlement_id',i.opening_carry_entitlement_id,'opening_carry_qty',i.opening_carry_qty::text,'bc_credit_event_id',i.bc_credit_event_id)
 from erp.payroll_reimbursements i where p_section='REIMBURSEMENTS' and i.payroll_id=p_id
 union all
 select i.id,i.id::text,jsonb_build_object('id',i.id,'type',i.deduction_type,'amount',i.amount::text,'notes',i.notes,
  'contractor_issue_item_id',i.contractor_issue_item_id,'bs_resolution_id',i.bs_resolution_id,'opening_cash_advance_balance_id',i.opening_cash_advance_balance_id)
 from erp.payroll_deductions i where p_section='DEDUCTIONS' and i.payroll_id=p_id
 union all
 select n.id,concat_ws(':',n.note_date,n.id),cp7_payroll.note_document(n,true)
 from cp7_payroll.notes n where p_section='NOTES' and n.posted_payroll_id=p_id
$$;

create function cp7_payroll.settlement_workspace(p_section text,p_query jsonb) returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare a jsonb;q text;pid uuid;contractor uuid;filter_status text;n integer;off integer;rows jsonb;total bigint;doc jsonb;
begin
 a:=cp7_payroll.access_now('PAYROLL');
 if p_section is null or p_section not in('PAYROLLS','WORK','ATTENDANCE','REIMBURSEMENTS','DEDUCTIONS','NOTES','CASH_ACCOUNTS')
  or jsonb_typeof(p_query) is distinct from 'object'
  or exists(select 1 from jsonb_object_keys(p_query) k where k not in('q','id','contractor_id','status','limit','offset'))
  or exists(select 1 from jsonb_each(p_query) e where e.key in('q','id','contractor_id','status') and jsonb_typeof(e.value) not in('string','null'))
  or (p_query?'limit' and (jsonb_typeof(p_query->'limit')<>'number' or(p_query->>'limit')!~'^[0-9]{1,3}$'))
  or (p_query?'offset' and (jsonb_typeof(p_query->'offset')<>'number' or(p_query->>'offset')!~'^[0-9]{1,7}$')) then raise exception 'CP7_PAYROLL_QUERY';end if;
 q:=btrim(coalesce(p_query->>'q',''));pid:=(p_query->>'id')::uuid;contractor:=(p_query->>'contractor_id')::uuid;filter_status:=p_query->>'status';n:=coalesce((p_query->>'limit')::integer,25);off:=coalesce((p_query->>'offset')::integer,0);
 if length(q)>120 or n not between 1 and 100 or off not between 0 and 1000000
  or(filter_status is not null and filter_status not in('DRAFT','CALCULATED','REVIEW','APPROVED','PAID','REVERSED'))
  or(p_section not in('PAYROLLS','CASH_ACCOUNTS') and(pid is null or q<>'' or contractor is not null or filter_status is not null))
  or(p_section='CASH_ACCOUNTS' and(pid is not null or contractor is not null or filter_status is not null)) then raise exception 'CP7_PAYROLL_QUERY';end if;
 if p_section='PAYROLLS' then
  with filtered as materialized(select p.id,p.period_end,p.created_at from erp.payroll_settlements p join erp.contractors c on c.id=p.contractor_id
   where (pid is null or p.id=pid) and(contractor is null or p.contractor_id=contractor) and(filter_status is null or p.status=filter_status)
    and(q='' or strpos(lower(concat_ws(' ',p.payroll_number,c.contractor_name,p.notes)),lower(q))>0)),
  page as(select * from filtered order by period_end desc,created_at desc,id limit n offset off)
  select(select count(*) from filtered),coalesce(jsonb_agg(cp7_payroll.settlement_document(id) order by period_end desc,created_at desc,id),'[]') into total,rows from page;
 elsif p_section='CASH_ACCOUNTS' then
  with filtered as materialized(select * from erp.cash_accounts c where c.is_active and(q='' or strpos(lower(concat_ws(' ',c.cash_account_code,c.cash_account_name)),lower(q))>0)),
  page as(select * from filtered order by cash_account_code,id limit n offset off)
  select(select count(*) from filtered),coalesce(jsonb_agg(jsonb_build_object('id',id,'code',cash_account_code,'name',cash_account_name,'kind',account_kind) order by cash_account_code,id),'[]') into total,rows from page;
 else
  doc:=cp7_payroll.settlement_document(pid);if doc is null then raise exception 'CP7_PAYROLL_MISSING';end if;
  with filtered as materialized(select * from cp7_payroll.settlement_rows(p_section,pid)),page as(select * from filtered order by ordering,id limit n offset off)
  select(select count(*) from filtered),coalesce(jsonb_agg(data order by ordering,id),'[]') into total,rows from page;
 end if;
 return jsonb_build_object('contract_version','cp7.payroll-workspace.v1','section',p_section,'read_at',statement_timestamp(),
  'capabilities',jsonb_build_object('approve',erp.has_permission('finance.payroll.approve'),'pay',erp.has_permission('finance.payroll.pay')),
  'document',doc,'page',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',n,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows) else null end));
end $$;

create function public.erp_cp7_get_payroll_workspace_v1(p_section text,p_query jsonb) returns jsonb
language sql stable security definer set search_path='' as $$select cp7_payroll.settlement_workspace(p_section,p_query)$$;
grant create on schema public to cp7_payroll_read;
alter function cp7_payroll.settlement_token(uuid) owner to cp7_payroll_read;
alter function cp7_payroll.settlement_document(uuid) owner to cp7_payroll_read;
alter function cp7_payroll.settlement_rows(text,uuid) owner to cp7_payroll_read;
alter function cp7_payroll.settlement_workspace(text,jsonb) owner to cp7_payroll_read;
alter function public.erp_cp7_get_payroll_workspace_v1(text,jsonb) owner to cp7_payroll_read;
revoke create on schema public from cp7_payroll_read;
revoke all on function cp7_payroll.settlement_token(uuid),cp7_payroll.settlement_document(uuid),cp7_payroll.settlement_rows(text,uuid),cp7_payroll.settlement_workspace(text,jsonb) from public,anon,authenticated,service_role,cp7_capture,cp7_nota_write,cp7_payroll_header;
revoke all on function public.erp_cp7_get_payroll_workspace_v1(text,jsonb) from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_payroll_workspace_v1(text,jsonb) to authenticated;
