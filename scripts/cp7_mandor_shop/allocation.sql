-- Unactivated private allocation owner. No public grants or installer.
-- Payment/reversal hooks must be qualified separately on the final parent.
create function cp7_mandor_shop.access_now(p_action text default null)returns jsonb
language plpgsql stable security definer set search_path=''as $$
declare a_ jsonb;
begin
 if auth.uid()is null or coalesce(auth.jwt()->>'role','')<>'authenticated'then
  raise exception using errcode='42501',message='CP7_MANDOR_SHOP_ACCESS_DENIED';end if;
 a_:=erp.get_my_access_v1();
 if a_->'allowed'is distinct from'true'::jsonb
  or erp.has_permission('finance.payroll.view')is distinct from true
  or erp.has_permission('finance.ar.view')is distinct from true
  or(p_action is not null and(p_action not in('RESERVE','RELEASE')
   or erp.has_permission('finance.payroll.approve')is distinct from true))then
  raise exception using errcode='42501',message='CP7_MANDOR_SHOP_ACCESS_DENIED';end if;
 return a_;
end $$;

create function cp7_mandor_shop.payroll_basis(p_payroll uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare h_ erp.payroll_settlements;attendance_ boolean;net_ numeric;reserved_ numeric;
 rows_ jsonb;
begin
 select *into strict h_ from erp.payroll_settlements where id=p_payroll;
 select attendance_required into strict attendance_ from erp.contractors where id=h_.contractor_id;
 if exists(select 1 from cp7_mandor_shop.deduction_links l
  left join erp.payroll_deductions d on d.id=l.deduction_id
  left join cp7_mandor_shop.allocation_states s on s.allocation_id=l.allocation_id
  where l.payroll_id=p_payroll and(d.id is null or d.payroll_id is distinct from p_payroll
   or d.amount is distinct from l.amount or d.deduction_type is distinct from'OTHER'
   or d.contractor_issue_item_id is not null or d.bs_resolution_id is not null
   or d.opening_cash_advance_balance_id is not null
   or s.state is null or s.state not in('RESERVED','SETTLED')))
  or exists(select 1 from cp7_mandor_shop.allocation_states s
   where s.payroll_id=p_payroll and s.state in('RESERVED','SETTLED')
    and not exists(select 1 from cp7_mandor_shop.deduction_links l
     where l.allocation_id=s.allocation_id))then
  raise exception 'CP7_MANDOR_SHOP_NATIVE_DEDUCTION_BRIDGE_CHANGED';end if;
 -- Match the actual Native recalculation and generated net formula. A draft
 -- header can still contain totals from an earlier source preparation.
 net_:=coalesce((select sum(amount)from erp.payroll_work_items where payroll_id=p_payroll),0)
  +case when attendance_ then coalesce((select sum(amount)from erp.payroll_attendance_items where payroll_id=p_payroll),0)else 0 end
  +coalesce((select sum(amount)from erp.payroll_reimbursements where payroll_id=p_payroll),0)
  -coalesce((select sum(amount)from erp.payroll_deductions where payroll_id=p_payroll),0)+h_.manual_adjustment;
 select coalesce(sum(amount)filter(where state='RESERVED'),0),
  coalesce(jsonb_agg(to_jsonb(s)order by s.allocation_id),'[]'::jsonb)
 into reserved_,rows_ from cp7_mandor_shop.allocation_states s where s.payroll_id=p_payroll;
 return jsonb_build_object('header',to_jsonb(h_),'native_meaning',cp7_installment.meaning(p_payroll),
  'attendance_required',attendance_,'calculated_net',net_::text,
  'reserved_amount',reserved_::text,'allocation_states',rows_);
end $$;

create function cp7_mandor_shop.invoice_basis(p_sale uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare h_ erp.sales_headers;sale_ cp7_mandor_shop.sales;net_ numeric;paid_ numeric;
 reserved_ numeric;rows_ jsonb;
begin
 select *into strict h_ from erp.sales_headers where id=p_sale;
 select *into strict sale_ from cp7_mandor_shop.sales where sale_id=p_sale;
 if h_.customer_id is distinct from sale_.customer_id or not exists(
  select 1 from cp7_mandor_shop.contractor_accounts a
  where a.contractor_id=sale_.contractor_id and a.customer_id=h_.customer_id)then
  raise exception 'CP7_MANDOR_SHOP_POSTED_BUYER_CHANGED';end if;
 net_:=erp.sale_net_total(p_sale);
 -- The final payment integration must include actual unreversed FG offsets
 -- in this SAME authoritative projection. Never add a sales_payments row.
 paid_:=cp7_credit.current_effective_paid(p_sale);
 select coalesce(sum(s.amount)filter(where s.state='RESERVED'),0),
  coalesce(jsonb_agg(jsonb_build_object('allocation',to_jsonb(s),
   'payroll_number',p.payroll_number,'period_start',p.period_start,'period_end',p.period_end,
   'payroll_status',p.status)order by s.payroll_id,s.allocation_id),'[]'::jsonb)
 into reserved_,rows_ from cp7_mandor_shop.allocation_states s
 join erp.payroll_settlements p on p.id=s.payroll_id where s.sale_id=p_sale;
 return jsonb_build_object('header',to_jsonb(h_),'posted_buyer',to_jsonb(sale_),
  'net_invoice',net_::text,'effective_paid',paid_::text,'outstanding',(net_-paid_)::text,
  'reserved_amount',reserved_::text,'available_to_reserve',(net_-paid_-reserved_)::text,
  'allocations',rows_);
end $$;

create function cp7_mandor_shop.review_token(p_access jsonb,p_payroll jsonb,p_invoice jsonb)
returns text language sql immutable set search_path=''as $$
 select encode(extensions.digest(convert_to(jsonb_build_array(
  'cp7.mandor-shop-review.v1',p_access,p_payroll,p_invoice)::text,'UTF8'),'sha256'),'hex')
$$;

create function cp7_mandor_shop.workspace(p_payroll uuid,p_after uuid default null)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare a_ jsonb;payroll_ jsonb;invoice_ jsonb;cards_ jsonb:='[]';r_ record;count_ integer:=0;
 more_ boolean:=false;last_ uuid;
begin
 a_:=cp7_mandor_shop.access_now();payroll_:=cp7_mandor_shop.payroll_basis(p_payroll);
 for r_ in select s.sale_id from cp7_mandor_shop.sales s
  join erp.sales_headers h on h.id=s.sale_id
  where s.contractor_id=(payroll_#>>'{header,contractor_id}')::uuid
   and(h.status in('POSTED','PARTIAL_PAID','PAID')or exists(
    select 1 from cp7_mandor_shop.allocation_states held_
    where held_.sale_id=s.sale_id and held_.payroll_id=p_payroll and held_.state='RESERVED'))
   and(p_after is null or s.sale_id>p_after)
  order by s.sale_id limit 101 loop
  count_:=count_+1;if count_>100 then more_:=true;exit;end if;
  invoice_:=cp7_mandor_shop.invoice_basis(r_.sale_id);last_:=r_.sale_id;
  cards_:=cards_||jsonb_build_array(jsonb_build_object('sale_id',r_.sale_id,
   'number',invoice_#>>'{header,sale_number}','physical_at',invoice_#>>'{header,sale_date}',
   'net_invoice',invoice_->>'net_invoice','paid_amount',invoice_->>'effective_paid',
   'outstanding',invoice_->>'outstanding','allocated_amount',invoice_->>'reserved_amount',
   'available_to_reserve',invoice_->>'available_to_reserve','allocations',invoice_->'allocations',
   'review_token',cp7_mandor_shop.review_token(a_,payroll_,invoice_)));
 end loop;
 return jsonb_build_object('contract_version','cp7.mandor-shop-workspace.v1','payroll_id',p_payroll,
  'contractor_id',payroll_#>>'{header,contractor_id}','status',payroll_#>>'{header,status}',
  'period_start',payroll_#>>'{header,period_start}','period_end',payroll_#>>'{header,period_end}',
  'net_payable_preview',payroll_->>'calculated_net','reserved_amount',payroll_->>'reserved_amount',
  'can_change',erp.has_permission('finance.payroll.approve')and payroll_#>>'{header,status}'in('DRAFT','CALCULATED','REVIEW'),
  'cards',cards_,'has_more',more_,'next_after',case when more_ then last_ else null end);
end $$;

create function cp7_mandor_shop.lock_allocation_sources(p_payroll uuid,p_sale uuid,p_action text,p_access jsonb)
returns void language plpgsql volatile security definer set search_path=''as $$
declare contractor_ uuid;
begin
 -- Fail promptly instead of keeping a stale review while another tab/native
 -- command holds a conflicting row. PostgreSQL owns every lock to COMMIT.
 select contractor_id into strict contractor_ from erp.payroll_settlements
  where id=p_payroll for update nowait;
 if not pg_try_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))
  or not pg_try_advisory_xact_lock(hashtextextended('CP7_MANDOR_SHOP|'||contractor_::text,0))then
  raise exception using errcode='55P03',message='CP7_MANDOR_SHOP_SOURCE_BUSY_REVIEW_AGAIN';end if;
 lock table erp.app_permissions,erp.app_role_permissions,erp.app_roles,erp.app_users in share mode nowait;
 perform 1 from erp.contractors where id=contractor_ for share nowait;
 perform 1 from erp.sales_headers where id=p_sale for update nowait;
 perform 1 from erp.payroll_work_items where payroll_id=p_payroll order by id for update nowait;
 perform 1 from erp.payroll_attendance_items where payroll_id=p_payroll order by id for update nowait;
 perform 1 from erp.payroll_reimbursements where payroll_id=p_payroll order by id for update nowait;
 perform 1 from erp.payroll_deductions where payroll_id=p_payroll order by id for update nowait;
 if cp7_mandor_shop.access_now(p_action)is distinct from p_access then
  raise exception using errcode='42501',message='CP7_MANDOR_SHOP_ACCESS_CHANGED';end if;
end $$;

create function cp7_mandor_shop.allocation_command(p_action text,p jsonb,p_request uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a_ jsonb;actor_ uuid;payroll_ uuid;sale_ uuid;amount_ numeric;payroll_basis_ jsonb;invoice_ jsonb;
 old_ cp7_mandor_shop.requests;state_ cp7_mandor_shop.allocation_states;hash_ text;
 allocation_ uuid;deduction_ uuid;result_ jsonb;net_ numeric;contractor_ uuid;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a_:=cp7_mandor_shop.access_now(p_action);actor_:=auth.uid();
 if p_action is null or p_action not in('RESERVE','RELEASE')or p_request is null
  or jsonb_typeof(p)is distinct from'object'
  or p->>'contract_version'is distinct from'cp7.mandor-shop-allocation-command.v1'
  or not p?&array['contract_version','payroll_id','sale_id','review_token']
  or coalesce(p->>'review_token','')!~'^[0-9a-f]{64}$'
  or exists(select 1 from jsonb_each(p)e where jsonb_typeof(e.value)<>'string'
   or e.key<>all(case p_action when'RESERVE'then array['contract_version','payroll_id','sale_id','review_token','amount']
    else array['contract_version','payroll_id','sale_id','review_token','allocation_id']end))then
  raise exception 'CP7_MANDOR_SHOP_COMMAND_FIELDS';end if;
 payroll_:=(p->>'payroll_id')::uuid;sale_:=(p->>'sale_id')::uuid;
 if payroll_::text is distinct from p->>'payroll_id'or sale_::text is distinct from p->>'sale_id'then
  raise exception 'CP7_MANDOR_SHOP_CANONICAL_UUID_REQUIRED';end if;
 if p_action='RESERVE'then
  if coalesce(p->>'amount','')!~'^(0|[1-9][0-9]{0,17})(\.[0-9]{1,2})?$'then
   raise exception 'CP7_MANDOR_SHOP_EXACT_POSITIVE_CENTS_REQUIRED';end if;
  amount_:=(p->>'amount')::numeric;
  if amount_<=0 or amount_>=1000000000000000000 then raise exception 'CP7_MANDOR_SHOP_EXACT_POSITIVE_CENTS_REQUIRED';end if;
 else
  allocation_:=(p->>'allocation_id')::uuid;
  if allocation_ is null or allocation_::text is distinct from p->>'allocation_id'then
   raise exception 'CP7_MANDOR_SHOP_CANONICAL_UUID_REQUIRED';end if;
 end if;
 hash_:=encode(extensions.digest(convert_to(jsonb_build_array(p_action,p)::text,'UTF8'),'sha256'),'hex');
 if not pg_try_advisory_xact_lock(hashtextextended('CP7_MANDOR_SHOP_REQUEST|'||actor_::text||'|'||p_request::text,0))then
  raise exception using errcode='55P03',message='CP7_MANDOR_SHOP_REQUEST_BUSY';end if;
 select *into old_ from cp7_mandor_shop.requests where actor=actor_ and request_id=p_request;
 if old_.actor is not null then
  if old_.action is distinct from p_action or old_.payload is distinct from p or old_.payload_sha256 is distinct from hash_ then
   raise exception 'CP7_MANDOR_SHOP_REQUEST_CHANGED';end if;
  return old_.response;
 end if;
 perform cp7_mandor_shop.lock_allocation_sources(payroll_,sale_,p_action,a_);
 payroll_basis_:=cp7_mandor_shop.payroll_basis(payroll_);invoice_:=cp7_mandor_shop.invoice_basis(sale_);
 contractor_:=(payroll_basis_#>>'{header,contractor_id}')::uuid;
 if payroll_basis_#>>'{header,status}'not in('DRAFT','CALCULATED','REVIEW')then
  raise exception 'CP7_MANDOR_SHOP_EDITABLE_PAYROLL_REQUIRED';end if;
 if contractor_ is distinct from(invoice_#>>'{posted_buyer,contractor_id}')::uuid then
  raise exception 'CP7_MANDOR_SHOP_WRONG_MANDOR';end if;
 if cp7_mandor_shop.review_token(a_,payroll_basis_,invoice_)is distinct from p->>'review_token'then
  raise exception 'CP7_MANDOR_SHOP_REVIEW_CHANGED';end if;
 net_:=(payroll_basis_->>'calculated_net')::numeric;
 insert into cp7_mandor_shop.command_context values(pg_backend_pid(),txid_current(),actor_,p_request,p_action,hash_);
 if p_action='RESERVE'then
  if invoice_#>>'{header,status}'not in('POSTED','PARTIAL_PAID')
   or amount_>(invoice_->>'available_to_reserve')::numeric then
   raise exception 'CP7_MANDOR_SHOP_INVOICE_CAPACITY_CHANGED';end if;
  if amount_>net_ then raise exception 'CP7_MANDOR_SHOP_PAYROLL_CAPACITY_CHANGED';end if;
  insert into cp7_mandor_shop.payroll_identities(payroll_id,contractor_id,created_by)
   values(payroll_,contractor_,actor_)on conflict(payroll_id)do nothing;
  allocation_:=gen_random_uuid();deduction_:=gen_random_uuid();
  insert into cp7_mandor_shop.allocations(id,sale_id,payroll_id,contractor_id,amount,actor,request_id)
   values(allocation_,sale_,payroll_,contractor_,amount_,actor_,p_request);
  insert into cp7_mandor_shop.allocation_events(id,allocation_id,ordinal,kind,actor,request_id)
   values(gen_random_uuid(),allocation_,1,'RESERVE',actor_,p_request);
  insert into erp.payroll_deductions(id,payroll_id,deduction_type,amount,notes)
   values(deduction_,payroll_,'OTHER',amount_,'Belanja FG: '||(invoice_#>>'{header,sale_number}'));
  insert into cp7_mandor_shop.deduction_links(allocation_id,sale_id,payroll_id,contractor_id,amount,deduction_id)
   values(allocation_,sale_,payroll_,contractor_,amount_,deduction_);
  net_:=net_-amount_;
 else
  select *into state_ from cp7_mandor_shop.allocation_states where allocation_id=allocation_ for update;
  if state_.state is distinct from'RESERVED'or(state_.sale_id,state_.payroll_id,state_.contractor_id)
   is distinct from(sale_,payroll_,contractor_)then raise exception 'CP7_MANDOR_SHOP_EXACT_RESERVED_CARD_REQUIRED';end if;
  select deduction_id into strict deduction_ from cp7_mandor_shop.deduction_links where allocation_id=allocation_;
  delete from cp7_mandor_shop.deduction_links where allocation_id=allocation_;
  delete from erp.payroll_deductions where id=deduction_;
  insert into cp7_mandor_shop.allocation_events(id,allocation_id,ordinal,predecessor_id,kind,actor,request_id)
   values(gen_random_uuid(),allocation_,state_.last_ordinal+1,state_.last_event_id,'RELEASE',actor_,p_request);
  net_:=net_+state_.amount;
 end if;
 -- Use the actual existing preparation admission; never add a general bypass.
 insert into cp7_payroll.settlement_context values(pg_backend_pid(),txid_current(),actor_,payroll_,'PREPARE');
 perform erp.recalculate_payroll(payroll_);
 delete from cp7_payroll.settlement_context where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 if(select net_payable from erp.payroll_settlements where id=payroll_)is distinct from net_ then
  raise exception 'CP7_MANDOR_SHOP_NATIVE_NET_MISMATCH';end if;
 delete from cp7_mandor_shop.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 if cp7_mandor_shop.access_now(p_action)is distinct from a_ then
  raise exception using errcode='42501',message='CP7_MANDOR_SHOP_ACCESS_CHANGED';end if;
 result_:=jsonb_build_object('contract_version','cp7.mandor-shop-allocation-outcome.v1',
  'kind','COMMITTED_OUTCOME','action',p_action,'request_id',p_request,'payroll_id',payroll_,
  'sale_id',sale_,'allocation_id',allocation_,'net_payable',net_::text,'invoice_settled_by_this_command',false);
 insert into cp7_mandor_shop.requests(actor,request_id,action,payload,payload_sha256,response)
  values(actor_,p_request,p_action,p,hash_,result_);
 return result_;
end $$;

alter function cp7_mandor_shop.access_now(text)owner to postgres;
alter function cp7_mandor_shop.payroll_basis(uuid)owner to postgres;
alter function cp7_mandor_shop.invoice_basis(uuid)owner to postgres;
alter function cp7_mandor_shop.review_token(jsonb,jsonb,jsonb)owner to postgres;
alter function cp7_mandor_shop.workspace(uuid,uuid)owner to postgres;
alter function cp7_mandor_shop.lock_allocation_sources(uuid,uuid,text,jsonb)owner to postgres;
alter function cp7_mandor_shop.allocation_command(text,jsonb,uuid)owner to postgres;
revoke all on function cp7_mandor_shop.access_now(text),cp7_mandor_shop.payroll_basis(uuid),
 cp7_mandor_shop.invoice_basis(uuid),cp7_mandor_shop.review_token(jsonb,jsonb,jsonb),
 cp7_mandor_shop.workspace(uuid,uuid),cp7_mandor_shop.lock_allocation_sources(uuid,uuid,text,jsonb),
 cp7_mandor_shop.allocation_command(text,jsonb,uuid)from public,anon,authenticated,service_role;
