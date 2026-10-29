-- D17-19C. Source links and choices only; Native journals and HPP own money.
create schema cp7_attendance_choice authorization postgres;
revoke all on schema cp7_attendance_choice from public,anon,authenticated,service_role;

create table cp7_attendance_choice.decisions_v1(
 id uuid primary key,period_start date not null,period_end date not null,
 choice text not null check(choice in('CARRY','EXPENSE')),
 source_binding text not null check(source_binding~'^[a-f0-9]{64}$'),
 source_capture jsonb not null,amount_cents bigint not null check(amount_cents>0),
 journal_id uuid unique,correction_of uuid references cp7_attendance_choice.decisions_v1,
 reason text not null check(length(btrim(reason))between 5 and 1000),
 actor uuid not null,app_user uuid not null,recorded_at timestamptz not null default clock_timestamp(),
 check(period_end>=period_start and period_end-period_start<=366),
 check((choice='CARRY'and journal_id is null)or(choice='EXPENSE'and journal_id is not null))
);
create index decisions_v1_period on cp7_attendance_choice.decisions_v1(period_start,period_end);
create table cp7_attendance_choice.sources_v1(
 decision_id uuid not null references cp7_attendance_choice.decisions_v1,
 payroll_id uuid not null,contractor_id uuid not null,policy_version_id uuid not null,
 original_debit_journal_line_id uuid not null,original_journal_id uuid not null,
 amount_cents bigint not null check(amount_cents>0),expense_credit_line_id uuid,
 primary key(decision_id,payroll_id),unique(decision_id,original_debit_journal_line_id)
);
create table cp7_attendance_choice.reversals_v1(
 decision_id uuid primary key references cp7_attendance_choice.decisions_v1,
 id uuid not null unique,journal_id uuid unique,
 reason text not null check(length(btrim(reason))between 5 and 1000),actor uuid not null,app_user uuid not null,
 recorded_at timestamptz not null default clock_timestamp()
);
create table cp7_attendance_choice.allocations_v1(
 id uuid primary key,decision_id uuid not null references cp7_attendance_choice.decisions_v1,
 pool_id uuid not null unique,output_start date not null,output_end date not null,
 manifest_sha256 text not null check(manifest_sha256~'^[a-f0-9]{64}$'),
 output_native_provenance jsonb not null,
 reason text not null check(length(btrim(reason))between 5 and 1000),actor uuid not null,app_user uuid not null,
 recorded_at timestamptz not null default clock_timestamp(),
 check(output_end>=output_start and output_end-output_start<=366)
);
create index allocations_v1_decision on cp7_attendance_choice.allocations_v1(decision_id);
create table cp7_attendance_choice.allocation_reversals_v1(
 allocation_id uuid primary key references cp7_attendance_choice.allocations_v1,
 id uuid not null unique,journal_id uuid not null unique,
 reason text not null check(length(btrim(reason))between 5 and 1000),actor uuid not null,app_user uuid not null,
 recorded_at timestamptz not null default clock_timestamp()
);
create table cp7_attendance_choice.requests_v1(
 actor uuid not null,request_id uuid not null,action text not null,payload jsonb not null,response jsonb not null,
 app_user uuid not null,recorded_at timestamptz not null default clock_timestamp(),primary key(actor,request_id)
);
-- An exact owning Native CANCEL call, tied to actor/backend/transaction/args.
-- It cannot authorize a different journal, pool, request, reason or version.
create table cp7_attendance_choice.cancel_context_v1(
 backend_pid integer not null,transaction_id bigint not null,actor uuid not null,
 pool_id uuid not null,request_id uuid not null,expected_version bigint not null,reason text not null,
 primary key(backend_pid,transaction_id,actor,pool_id,request_id)
);

create function cp7_attendance_choice.immutable_v1()returns trigger
language plpgsql volatile security invoker set search_path=''as $$
begin raise exception 'CP7_S03_APPEND_ONLY';end $$;
do $$declare n text;begin
 foreach n in array array['decisions_v1','sources_v1','reversals_v1','allocations_v1','allocation_reversals_v1','requests_v1','cancel_context_v1']loop
  execute format('alter table cp7_attendance_choice.%I enable row level security',n);
  execute format('create policy private_rows on cp7_attendance_choice.%I for all using(false)with check(false)',n);
  execute format('create trigger immutable_row before update or delete on cp7_attendance_choice.%I for each row execute function cp7_attendance_choice.immutable_v1()',n);
  execute format('create trigger immutable_truncate before truncate on cp7_attendance_choice.%I for each statement execute function cp7_attendance_choice.immutable_v1()',n);
 end loop;
end $$;

create function cp7_attendance_choice.blockers_v1(p_through date)
returns table(family text,code text,severity text,scope text,impact_date date,reference jsonb,reason text)
language plpgsql stable security definer set search_path=''set timezone='UTC'as $$
declare r record;d cp7_attendance_choice.decisions_v1;c jsonb;problem text;
begin
 for r in select*from cp7_hpp_close.blockers_v1(p_through)loop
  if r.code<>'ATTENDANCE_POOL_ZERO_OUTPUT'then
   return query select r.family,r.code,r.severity,r.scope,r.impact_date,r.reference,r.reason;continue;
  end if;
  select*into d from cp7_attendance_choice.decisions_v1 where id=cp7_attendance_choice.current_v1(
   (r.reference->>'period_start')::date,(r.reference->>'period_end')::date);
  if d.id is null then
   return query select r.family,'ATTENDANCE_ZERO_CHOICE_REQUIRED'::text,'POLICY'::text,r.scope,r.impact_date,r.reference,
    'Biaya absensi tanpa hasil jahit belum mendapat pilihan Owner. Pilih menunggu hasil berikutnya atau beban periode, dengan alasan dan tinjauan sumber.'::text;
  else
   problem:=null;
   begin
    c:=cp7_attendance_choice.capture_v1(d.period_start,d.period_end,true);
    if c->>'source_binding'<>d.source_binding then problem:='Sumber biaya absensi berubah; pilihan perlu dibetulkan melalui alurnya.';end if;
    perform cp7_attendance_choice.wip_check_v1(c,'[]'::jsonb);
    if d.choice='EXPENSE'and not exists(select 1 from erp.journal_entries j where j.id=d.journal_id and j.status='POSTED'
     and j.source_type='CP7_ATTENDANCE_PERIOD_EXPENSE'and j.source_id=d.id)then problem:='Jurnal beban tidak cocok dengan pilihan aktif.';end if;
   exception when others then problem:=sqlerrm;
   end;
   if problem is not null then
    return query select r.family,'ATTENDANCE_ZERO_CHOICE_STALE'::text,'POLICY'::text,r.scope,r.impact_date,
     r.reference||jsonb_build_object('decision_id',d.id),problem;
   else
    return query select r.family,case when d.choice='CARRY'then'ATTENDANCE_ZERO_CARRY_WAITING'else'ATTENDANCE_ZERO_PERIOD_EXPENSE'end,
     'INFO'::text,r.scope,r.impact_date,r.reference||jsonb_build_object('decision_id',d.id,'choice',d.choice,'journal_id',d.journal_id,'reason',d.reason),
     case when d.choice='CARRY'then'Owner memilih biaya absensi ini menunggu hasil jahit berikutnya. Sumber yang sama tetap di WIP, belum dibebankan ke barang.'
      else'Owner memilih beban periode. Hanya WIP absensi yang tertaut dipindahkan ke beban melalui jurnal Native; payroll tidak diakui ulang.'end;
   end if;
  end if;
 end loop;
end $$;

create function cp7_attendance_choice.workspace_v1(p_start date,p_end date,p_offset integer,p_limit integer)returns jsonb
language plpgsql volatile security definer set search_path=''set timezone='UTC'as $$
declare access jsonb;d cp7_attendance_choice.decisions_v1;a cp7_attendance_choice.allocations_v1;c jsonb;history jsonb;closed date;problem text;total bigint;
begin
 access:=cp7_attendance_choice.access_v1(false);
 if p_start is null or p_end is null or p_end<p_start or p_end-p_start>366 then raise exception 'CP7_S03_PERIOD';end if;
 if p_offset is null or p_limit is null or p_offset not between 0 and 100000 or p_limit not between 1 and 50 then raise exception 'CP7_S03_PAGE';end if;
 select*into d from cp7_attendance_choice.decisions_v1 where id=cp7_attendance_choice.current_v1(p_start,p_end);
 if d.id is not null then select*into a from cp7_attendance_choice.allocations_v1 where id=cp7_attendance_choice.current_allocation_v1(d.id);end if;
 select closed_through into closed from erp.accounting_period_control where singleton_id=1;
 begin c:=cp7_attendance_choice.capture_v1(p_start,p_end,false);exception when others then problem:=sqlerrm;end;
 with events as(
  select x.id,x.recorded_at,jsonb_build_object('event_id',x.id,'event','CHOOSE','decision_id',x.id,'choice',x.choice,
   'amount_cents',x.amount_cents::text,'reason',x.reason,'recorded_at',x.recorded_at,'actor',x.actor,'journal_id',x.journal_id,'correction_of',x.correction_of)body
  from cp7_attendance_choice.decisions_v1 x where x.period_start=p_start and x.period_end=p_end
  union all select r.id,r.recorded_at,jsonb_build_object('event_id',r.id,'event','REVERSE','decision_id',r.decision_id,
   'reason',r.reason,'recorded_at',r.recorded_at,'actor',r.actor,'journal_id',r.journal_id)
  from cp7_attendance_choice.reversals_v1 r join cp7_attendance_choice.decisions_v1 x on x.id=r.decision_id where x.period_start=p_start and x.period_end=p_end
  union all select allocation.id,allocation.recorded_at,jsonb_build_object('event_id',allocation.id,'event','ALLOCATE','decision_id',allocation.decision_id,
   'allocation_id',allocation.id,'pool_id',allocation.pool_id,'output_start',allocation.output_start,'output_end',allocation.output_end,'reason',allocation.reason,'recorded_at',allocation.recorded_at,'actor',allocation.actor)
  from cp7_attendance_choice.allocations_v1 allocation join cp7_attendance_choice.decisions_v1 x on x.id=allocation.decision_id where x.period_start=p_start and x.period_end=p_end
  union all select r.id,r.recorded_at,jsonb_build_object('event_id',r.id,'event','CANCEL_ALLOCATION','decision_id',allocation.decision_id,
   'allocation_id',allocation.id,'pool_id',allocation.pool_id,'reason',r.reason,'recorded_at',r.recorded_at,'actor',r.actor,'journal_id',r.journal_id)
  from cp7_attendance_choice.allocation_reversals_v1 r join cp7_attendance_choice.allocations_v1 allocation on allocation.id=r.allocation_id
  join cp7_attendance_choice.decisions_v1 x on x.id=allocation.decision_id where x.period_start=p_start and x.period_end=p_end
 ),page as(select*from events order by recorded_at desc,id desc offset p_offset limit p_limit)
 select(select count(*)from events),coalesce(jsonb_agg(body order by recorded_at desc,id desc),'[]'::jsonb)into total,history from page;
 return jsonb_build_object('contract_version','cp7.attendance-period-choice-workspace.v1','period_start',p_start,'period_end',p_end,
  'amount_cents',c->>'amount_cents','source_binding',c->>'source_binding',
  'original_period_sewing_qty',c->'native_manifest'->>'denominator_qty','source_problem',problem,'closed_through',closed,
  'current_choice',case when d.id is not null then jsonb_build_object('decision_id',d.id,'choice',d.choice,'reason',d.reason,'journal_id',d.journal_id)end,
  'current_allocation',case when a.id is not null then jsonb_build_object('allocation_id',a.id,'pool_id',a.pool_id,'output_start',a.output_start,'output_end',a.output_end)end,
  'history',history,'history_total',total::text,'offset',p_offset,'limit',p_limit,
  'next_offset',case when p_offset+jsonb_array_length(history)<total then p_offset+jsonb_array_length(history)end,
  'can_manage',(access->>'manage')::boolean,'business_DML',false);
end $$;

create function cp7_attendance_choice.parse_v1(p_action text,p_payload jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''as $$
declare f date;t date;ofrom date;oto date;ch text;why text;
begin
 if p_action is null or p_action not in('CHOOSE','CORRECT','REVERSE','ALLOCATE','CANCEL_ALLOCATION')then raise exception 'CP7_S03_ACTION';end if;
 perform erp._cp3_assert_closed_json_object(p_payload,
  array['period_start','period_end','reason'],
  array['period_start','period_end','choice','output_start','output_end','reason'],'S03 period choice');
 if not(p_payload?&array['period_start','period_end','choice','output_start','output_end','reason'])then raise exception 'CP7_S03_FIELDS';end if;
 if jsonb_typeof(p_payload->'period_start')is distinct from'string'or jsonb_typeof(p_payload->'period_end')is distinct from'string'
  or jsonb_typeof(p_payload->'reason')is distinct from'string'then raise exception 'CP7_S03_FIELDS';end if;
 f:=erp._cp3_parse_canonical_date(p_payload->>'period_start','source period_start');
 t:=erp._cp3_parse_canonical_date(p_payload->>'period_end','source period_end');
 why:=btrim(p_payload->>'reason');ch:=p_payload->>'choice';
 if t<f or t-f>366 or length(why)not between 5 and 1000 then raise exception 'CP7_S03_FIELDS';end if;
 if p_action in('CHOOSE','CORRECT')then
  if jsonb_typeof(p_payload->'choice')is distinct from'string'or ch not in('CARRY','EXPENSE')then raise exception 'CP7_S03_CHOICE';end if;
 elsif p_payload->'choice'is distinct from'null'::jsonb then raise exception 'CP7_S03_CHOICE_NOT_USED';end if;
 if p_action='ALLOCATE'then
  if jsonb_typeof(p_payload->'output_start')is distinct from'string'or jsonb_typeof(p_payload->'output_end')is distinct from'string'then raise exception 'CP7_S03_OUTPUT_PERIOD';end if;
  ofrom:=erp._cp3_parse_canonical_date(p_payload->>'output_start','output_start');oto:=erp._cp3_parse_canonical_date(p_payload->>'output_end','output_end');
  if ofrom<=t or oto<ofrom or oto-ofrom>366 then raise exception 'CP7_S03_SEPARATE_LATER_OUTPUT_PERIOD_REQUIRED';end if;
 elsif p_payload->'output_start'is distinct from'null'::jsonb or p_payload->'output_end'is distinct from'null'::jsonb then raise exception 'CP7_S03_OUTPUT_PERIOD_NOT_USED';end if;
 return jsonb_build_object('period_start',f,'period_end',t,'choice',ch,'output_start',ofrom,'output_end',oto,'reason',why);
end $$;

create function cp7_attendance_choice.planned_v1(p_capture jsonb,p_sign integer,p_economic date,p_book date)returns jsonb
language sql immutable security invoker set search_path=''as $$
 select coalesce(jsonb_agg(jsonb_build_object('line_id',s->>'original_debit_journal_line_id',
  'cents',((s->>'attendance_amount_cents')::bigint*p_sign)::text,'economic_date',p_economic,'book_date',p_book)
  order by s->>'original_debit_journal_line_id'),'[]'::jsonb)
 from jsonb_array_elements(p_capture->'native_manifest'->'sources')s
$$;

create function cp7_attendance_choice.review_v1(p_action text,p_payload jsonb)returns jsonb
language plpgsql volatile security definer set search_path=''set timezone='UTC'as $$
declare access jsonb;p jsonb;f date;t date;today date;closed date;c jsonb;d cp7_attendance_choice.decisions_v1;
 a cp7_attendance_choice.allocations_v1;pool erp.attendance_hpp_pools;carry jsonb;planned jsonb:='[]'::jsonb;
 eco date;book date;inverse_eco date;inverse_book date;proof jsonb;context jsonb;target_date date;accounts jsonb;expense_account jsonb;
begin
 access:=cp7_attendance_choice.access_v1(false);p:=cp7_attendance_choice.parse_v1(p_action,p_payload);
 f:=(p->>'period_start')::date;t:=(p->>'period_end')::date;today:=erp.bb_business_today_v1();
 if t>today then raise exception 'CP7_S03_PERIOD_FUTURE';end if;
 select closed_through into closed from erp.accounting_period_control where singleton_id=1;
 select*into d from cp7_attendance_choice.decisions_v1 where id=cp7_attendance_choice.current_v1(f,t);
 if p_action='CHOOSE'and d.id is not null then raise exception 'CP7_S03_CHOICE_EXISTS';end if;
 if p_action<>'CHOOSE'and d.id is null then raise exception 'CP7_S03_CHOICE_NOT_FOUND';end if;
 if d.id is not null then
  select*into a from cp7_attendance_choice.allocations_v1 where id=cp7_attendance_choice.current_allocation_v1(d.id);
  if a.id is not null then select*into strict pool from erp.attendance_hpp_pools where id=a.pool_id;end if;
 end if;
 if p_action in('REVERSE','CORRECT','ALLOCATE')and a.id is not null then raise exception 'CP7_S03_CANCEL_CARRY_FIRST';end if;
 if p_action in('ALLOCATE','CANCEL_ALLOCATION')and d.choice<>'CARRY'then raise exception 'CP7_S03_CURRENT_CARRY_REQUIRED';end if;
 if p_action='CANCEL_ALLOCATION'and(a.id is null or pool.status<>'ACTIVE')then raise exception 'CP7_S03_ACTIVE_CARRY_ALLOCATION_REQUIRED';end if;
 c:=cp7_attendance_choice.capture_v1(f,t,p_action in('CHOOSE','CORRECT','ALLOCATE'));
 if d.id is not null and d.source_binding<>c->>'source_binding'then raise exception 'CP7_S03_SOURCE_CHANGED';end if;
 if p_action<>'CANCEL_ALLOCATION'and exists(select 1 from erp.attendance_hpp_pools hp
  where hp.period_start=f and hp.period_end=t and hp.status in('DRAFT','ACTIVE'))then raise exception 'CP7_S03_NATIVE_POOL_OWNS_PERIOD';end if;
 if exists(select 1 from jsonb_array_elements(c->'native_manifest'->'sources')s
  join erp.attendance_hpp_pool_sources x on x.payroll_id=(s->>'payroll_id')::uuid or x.original_debit_journal_line_id=(s->>'original_debit_journal_line_id')::uuid
  join erp.attendance_hpp_pools hp on hp.id=x.pool_id and hp.status='ACTIVE'
  where p_action<>'CANCEL_ALLOCATION'or hp.id<>a.pool_id)then raise exception 'CP7_S03_SOURCE_OWNED_BY_NATIVE_POOL';end if;
 if exists(select 1 from jsonb_array_elements(c->'native_manifest'->'sources')s
  join cp7_attendance_choice.sources_v1 x on x.original_debit_journal_line_id=(s->>'original_debit_journal_line_id')::uuid
  where x.decision_id is distinct from d.id and not exists(select 1 from cp7_attendance_choice.reversals_v1 r where r.decision_id=x.decision_id))then raise exception 'CP7_S03_SOURCE_ALREADY_CLAIMED';end if;
 target_date:=case when p_action='ALLOCATE'then(p->>'output_end')::date when p_action='CANCEL_ALLOCATION'then a.output_end else t end;
 if closed is not null and target_date<=closed then raise exception 'CP7_S03_PERIOD_CLOSED: buka kembali periode terkait melalui alur tutup buku sebelum membetulkannya.';end if;
 if p_action in('REVERSE','CORRECT')and d.choice='EXPENSE'then
  inverse_eco:=today;inverse_book:=erp.resolve_accounting_transaction_date(today);
  planned:=planned||cp7_attendance_choice.planned_v1(c,1,inverse_eco,inverse_book);
 end if;
 if p_action in('CHOOSE','CORRECT')and p->>'choice'='EXPENSE'then
  eco:=t;book:=erp.resolve_accounting_transaction_date(eco);
  if eco<(c->>'max_source_economic_date')::date or book<(c->>'max_source_book_date')::date then
   raise exception 'CP7_S03_EXPENSE_BEFORE_WIP_AVAILABLE: jurnal beban akan mendahului pengakuan atau pemulihan WIP pada tanggal ekonomi atau buku.';end if;
  planned:=planned||cp7_attendance_choice.planned_v1(c,-1,eco,book);
 end if;
 if p_action='ALLOCATE'then
  carry:=cp7_attendance_choice.carry_preview_v1(d.id,(p->>'output_start')::date,(p->>'output_end')::date);
  eco:=(p->>'output_end')::date;book:=erp.resolve_accounting_transaction_date(eco);
  planned:=planned||cp7_attendance_choice.planned_v1(c,-1,eco,book);
 elsif p_action='CANCEL_ALLOCATION'then
  inverse_eco:=today;inverse_book:=erp.resolve_accounting_transaction_date(today);
  planned:=planned||cp7_attendance_choice.planned_v1(c,1,inverse_eco,inverse_book);
 end if;
 proof:=cp7_attendance_choice.wip_check_v1(c,planned);
 -- The account used for an expense is a reviewed fact. Locking it only during
 -- save would otherwise silently accept a mapping changed since preview.
 select jsonb_agg(jsonb_build_object('mapping',to_jsonb(m),'account',to_jsonb(acct))order by m.mapping_key)into accounts
 from erp.accounting_account_mappings m join erp.chart_accounts acct on acct.id=m.account_id where m.mapping_key in('WIP','OTHER_EXPENSE');
 select to_jsonb(acct)into expense_account from erp.chart_accounts acct where acct.id=erp.account_id('OTHER_EXPENSE');
 if p_action in('CHOOSE','CORRECT')and p->>'choice'='EXPENSE'and not exists(
  select 1 from erp.chart_accounts acct where acct.id=erp.account_id('OTHER_EXPENSE')and acct.is_active and acct.is_postable and acct.account_type='EXPENSE'and acct.normal_balance='DEBIT')then
  raise exception 'CP7_S03_EXPENSE_ACCOUNT_REQUIRED';end if;
 context:=jsonb_build_object('action',p_action,'payload',p,'source',c,
  'current_choice',case when d.id is not null then to_jsonb(d)end,
  'current_allocation',case when a.id is not null then to_jsonb(a)end,
  'current_pool',case when pool.id is not null then to_jsonb(pool)end,
  'carry_manifest',carry->'manifest','closed_through',closed,'economic_date',eco,'book_date',book,
  'inverse_economic_date',inverse_eco,'inverse_book_date',inverse_book,'prospective_WIP',proof,'reviewed_accounts',accounts);
 -- Full later Native payroll is provenance, not live carry identity. All
 -- destination events/eligibility/quantity remain in carry_manifest.
 return jsonb_build_object('contract_version','cp7.attendance-period-choice.v1','action',p_action,'payload',p,
  'amount',((c->>'amount_cents')::numeric/100)::numeric(20,2)::text,'amount_cents',c->>'amount_cents',
  'source_count',jsonb_array_length(c->'native_manifest'->'sources')::text,
  'denominator_qty',carry->>'denominator_qty','economic_date',eco,'book_date',book,
  'inverse_economic_date',inverse_eco,'inverse_book_date',inverse_book,
  'decision_id',d.id,'allocation_id',a.id,'pool_id',pool.id,'source_binding',c->>'source_binding',
  'expense_account',case when p_action in('CHOOSE','CORRECT')and p->>'choice'='EXPENSE'then
   jsonb_build_object('id',expense_account->>'id','code',expense_account->>'account_code','name',expense_account->>'account_name')end,
  'review_token',erp._cp3_manifest_sha256(context),'context',context,'can_apply',true,'business_DML',false);
end $$;

create function cp7_attendance_choice.inner_uuid_v1(p_actor uuid,p_request uuid,p_kind text)returns uuid
language sql immutable security invoker set search_path=''as $$
 select md5('CP7:S03:'||p_actor::text||':'||p_request::text||':'||p_kind)::uuid
$$;

create function cp7_attendance_choice.choose_v1(p_period_start date,p_period_end date,p_choice text,p_reason text,p_id uuid,p_capture jsonb,p_correction uuid)returns uuid
language plpgsql volatile security definer set search_path=''set timezone='UTC'as $$
declare j uuid;lines jsonb:='[]'::jsonb;s jsonb;l erp.journal_lines;credit_id uuid;other uuid;check_rows bigint;
begin
 perform cp7_attendance_choice.access_v1(true);
 perform cp7_attendance_choice.assert_period_unclaimed_v1(p_period_start,p_period_end);
 if p_choice not in('CARRY','EXPENSE')or p_choice is null then raise exception 'CP7_S03_CHOICE';end if;
 if p_choice='EXPENSE'then
  if p_period_end<(p_capture->>'max_source_economic_date')::date
   or erp.resolve_accounting_transaction_date(p_period_end)<(p_capture->>'max_source_book_date')::date then raise exception 'CP7_S03_EXPENSE_BEFORE_WIP_AVAILABLE';end if;
  other:=erp.account_id('OTHER_EXPENSE');
  if not exists(select 1 from erp.chart_accounts a where a.id=other and a.is_active and a.is_postable and a.account_type='EXPENSE'and a.normal_balance='DEBIT')then
   raise exception 'CP7_S03_EXPENSE_ACCOUNT_REQUIRED';end if;
  for s in select value from jsonb_array_elements(p_capture->'native_manifest'->'sources')loop
   select*into strict l from erp.journal_lines where id=(s->>'original_debit_journal_line_id')::uuid;
   lines:=lines||jsonb_build_array(
    jsonb_build_object('account_id',other,'debit',(s->>'attendance_amount_cents')::numeric/100,'credit',0,
     'contractor_id',s->>'contractor_id','description','S03 period expense for payroll '||(s->>'payroll_id')),
    jsonb_build_object('account_id',l.account_id,'debit',0,'credit',(s->>'attendance_amount_cents')::numeric/100,
     'contractor_id',s->>'contractor_id','description','S03 WIP source '||(s->>'original_debit_journal_line_id')));
  end loop;
  j:=erp.post_journal('CP7_ATTENDANCE_PERIOD_EXPENSE',p_id,p_period_end,p_reason,lines);
  if not exists(select 1 from erp.journal_entries x where x.id=j and x.status='POSTED'and x.source_id=p_id
   and x.source_type='CP7_ATTENDANCE_PERIOD_EXPENSE'and x.economic_date=p_period_end
   and x.transaction_date=erp.resolve_accounting_transaction_date(p_period_end))then raise exception 'CP7_S03_NATIVE_EXPENSE_DATES';end if;
 end if;
 insert into cp7_attendance_choice.decisions_v1(id,period_start,period_end,choice,source_binding,source_capture,amount_cents,journal_id,correction_of,reason,actor,app_user)
 values(p_id,p_period_start,p_period_end,p_choice,p_capture->>'source_binding',p_capture,(p_capture->>'amount_cents')::bigint,j,p_correction,p_reason,auth.uid(),erp.current_app_user_id());
 for s in select value from jsonb_array_elements(p_capture->'native_manifest'->'sources')loop
  select*into strict l from erp.journal_lines where id=(s->>'original_debit_journal_line_id')::uuid;
  credit_id:=null;
  if j is not null then
   select count(*),min(x.id::text)::uuid into check_rows,credit_id from erp.journal_lines x
   where x.journal_entry_id=j and x.account_id=l.account_id and x.debit=0
    and x.credit=(s->>'attendance_amount_cents')::numeric/100 and x.contractor_id=(s->>'contractor_id')::uuid
    and x.po_id is null and x.vendor_id is null and x.customer_id is null and x.product_id is null
    and x.description='S03 WIP source '||(s->>'original_debit_journal_line_id');
   if check_rows<>1 then raise exception 'CP7_S03_EXACT_SOURCE_CREDIT_REQUIRED';end if;
  end if;
  insert into cp7_attendance_choice.sources_v1(decision_id,payroll_id,contractor_id,policy_version_id,
   original_debit_journal_line_id,original_journal_id,amount_cents,expense_credit_line_id)
  values(p_id,(s->>'payroll_id')::uuid,(s->>'contractor_id')::uuid,(s->>'policy_version_id')::uuid,
   l.id,l.journal_entry_id,(s->>'attendance_amount_cents')::bigint,credit_id);
 end loop;
 insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
 values('cp7_attendance_choice',p_id,'INSERT',jsonb_build_object('lifecycle_action','CHOOSE','choice',p_choice,
  'source_period_start',p_period_start,'source_period_end',p_period_end,'source_binding',p_capture->>'source_binding',
  'amount_cents',p_capture->>'amount_cents','journal_id',j,'correction_of',p_correction),erp.current_app_user_id(),p_reason);
 perform cp7_attendance_choice.wip_check_v1(p_capture,'[]'::jsonb);
 return p_id;
end $$;

create function cp7_attendance_choice.reverse_choice_v1(p_decision uuid,p_reason text,p_id uuid,p_capture jsonb)returns uuid
language plpgsql volatile security definer set search_path=''set timezone='UTC'as $$
declare d cp7_attendance_choice.decisions_v1;j uuid;original erp.journal_entries;inverse erp.journal_entries;
begin
 perform cp7_attendance_choice.access_v1(true);
 select*into strict d from cp7_attendance_choice.decisions_v1 where id=p_decision;
 if cp7_attendance_choice.current_v1(d.period_start,d.period_end)is distinct from d.id then raise exception 'CP7_S03_CHOICE_NOT_CURRENT';end if;
 if cp7_attendance_choice.current_allocation_v1(d.id)is not null then raise exception 'CP7_S03_CANCEL_CARRY_FIRST';end if;
 if d.source_binding is distinct from p_capture->>'source_binding'then raise exception 'CP7_S03_SOURCE_CHANGED';end if;
 if d.choice='EXPENSE'then
  select*into strict original from erp.journal_entries where id=d.journal_id;
  if original.status<>'POSTED'or original.source_type<>'CP7_ATTENDANCE_PERIOD_EXPENSE'or original.source_id<>d.id then raise exception 'CP7_S03_OWNED_EXPENSE_JOURNAL_REQUIRED';end if;
  -- Only this exact immutable decision's journal is accepted. No session flag
  -- broadens generic reverse_journal or payroll reversal authority.
  j:=erp._cp3_r4_reverse_journal_internal(d.journal_id,p_reason);
  select*into strict inverse from erp.journal_entries where id=j;
  if inverse.reversal_of_id is distinct from original.id or inverse.source_type<>'JOURNAL_REVERSAL'
   or inverse.economic_date<>erp.bb_business_today_v1()or inverse.transaction_date<>erp.resolve_accounting_transaction_date(inverse.economic_date)
   or inverse.economic_date<original.economic_date or inverse.transaction_date<original.transaction_date then raise exception 'CP7_S03_OWNED_INVERSE_DATES';end if;
 end if;
 insert into cp7_attendance_choice.reversals_v1(decision_id,id,journal_id,reason,actor,app_user)
 values(d.id,p_id,j,p_reason,auth.uid(),erp.current_app_user_id());
 insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
 values('cp7_attendance_choice',d.id,'REVERSE',jsonb_build_object('lifecycle_action','REVERSE_CHOICE','reversal_id',p_id,'journal_id',j),erp.current_app_user_id(),p_reason);
 perform cp7_attendance_choice.wip_check_v1(p_capture,'[]'::jsonb);
 return j;
end $$;

create function cp7_attendance_choice.access_v1(p_write boolean)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare a jsonb;v boolean;m boolean;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 if auth.uid()is null or coalesce(auth.jwt()->>'role','')<>'authenticated'then
  raise exception using errcode='42501',message='CP7_S03_OWNER_REQUIRED: masuk sebagai Owner untuk memilih pembebanan biaya absensi.';end if;
 a:=erp.get_my_access_v1();v:=coalesce(erp.has_permission('finance.hpp.view'),false);m:=coalesce(erp.has_permission('finance.hpp.manage'),false);
 if a->'allowed'is distinct from'true'::jsonb or a->'profile'->>'role_code'is distinct from'OWNER'or not v or(p_write and not m)then
  raise exception using errcode='42501',message='CP7_S03_OWNER_REQUIRED: pilihan per periode memerlukan Owner dengan izin HPP dan Rekalkulasi saat ini.';end if;
 if erp.current_app_user_id()is null then raise exception using errcode='42501',message='CP7_S03_USER_INACTIVE';end if;
 return jsonb_build_object('profile',a->'profile','view',v,'manage',m);
end $$;

create function cp7_attendance_choice.current_v1(p_start date,p_end date)returns uuid
language sql stable security definer set search_path=''as $$
 select d.id from cp7_attendance_choice.decisions_v1 d
 where d.period_start=p_start and d.period_end=p_end
 and not exists(select 1 from cp7_attendance_choice.reversals_v1 r where r.decision_id=d.id)
 order by d.recorded_at,d.id limit 1
$$;
create function cp7_attendance_choice.current_allocation_v1(p_decision uuid)returns uuid
language sql stable security definer set search_path=''as $$
 select a.id from cp7_attendance_choice.allocations_v1 a where a.decision_id=p_decision
 and not exists(select 1 from cp7_attendance_choice.allocation_reversals_v1 r where r.allocation_id=a.id)
 order by a.recorded_at,a.id limit 1
$$;

-- The exact Native source manifest deliberately does not bind PAID settlement
-- fields: its original accrual, items and policy remain identical after payment.
create function cp7_attendance_choice.capture_v1(p_start date,p_end date,p_zero boolean)returns jsonb
language plpgsql volatile security definer set search_path=''set timezone='UTC'as $$
declare m jsonb;known_zero boolean:=false;journals jsonb;items jsonb;binding jsonb;restored jsonb;
begin
 if p_start is null or p_end is null or p_end<p_start or p_end-p_start>366 then raise exception 'CP7_S03_PERIOD';end if;
 begin
  perform erp.preview_attendance_hpp_pool_v1(p_start,p_end);
 exception when raise_exception then
  if sqlerrm like 'POSITIVE_POOL_ZERO_SEWING_OUTPUT:%'then known_zero:=true;else raise;end if;
 end;
 m:=erp._build_attendance_hpp_manifest_v1(p_start,p_end);perform erp._assert_attendance_hpp_manifest_v1(m);
 if (m->>'numerator_cents')::bigint<=0 or jsonb_array_length(m->'sources')=0 then raise exception 'CP7_S03_NO_ELIGIBLE_COST';end if;
 if p_zero and(not known_zero or(m->>'denominator_qty')::bigint<>0)then
  raise exception 'CP7_S03_OUTPUT_EXISTS: hasil jahit periode sumber sudah tersedia; gunakan pool HPP Native untuk periode itu.';end if;
 if exists(select 1 from jsonb_array_elements(m->'sources')s join erp.payroll_settlements p on p.id=(s->>'payroll_id')::uuid
  where p.attendance_total is distinct from(select coalesce(sum(i.amount),0)from erp.payroll_attendance_items i where i.payroll_id=p.id))then
  raise exception 'CP7_S03_ATTENDANCE_EXACT_CENTS_REQUIRED';end if;
 select jsonb_agg(jsonb_build_object('payroll_id',s->>'payroll_id','line',to_jsonb(l),'journal',to_jsonb(j))order by s->>'payroll_id')
 into journals from jsonb_array_elements(m->'sources')s
 join erp.journal_lines l on l.id=(s->>'original_debit_journal_line_id')::uuid
 join erp.journal_entries j on j.id=l.journal_entry_id;
 if jsonb_array_length(journals)is distinct from jsonb_array_length(m->'sources')or exists(
  select 1 from jsonb_array_elements(m->'sources')s join erp.journal_lines l on l.id=(s->>'original_debit_journal_line_id')::uuid
  join erp.journal_entries j on j.id=l.journal_entry_id
  where j.status<>'POSTED'or j.source_type<>'PAYROLL_ATTENDANCE_ACCRUAL'or j.source_id<>(s->>'payroll_id')::uuid
   or l.account_id<>erp.account_id('WIP')or l.po_id is not null or l.credit<>0 or l.contractor_id is distinct from(s->>'contractor_id')::uuid
   or l.debit*100<(s->>'attendance_amount_cents')::bigint)then raise exception 'CP7_S03_ORIGINAL_UNASSIGNED_WIP_REQUIRED';end if;
 select coalesce(jsonb_agg(to_jsonb(i)order by i.payroll_id,i.id),'[]'::jsonb)into items
 from erp.payroll_attendance_items i where i.payroll_id in(select(s->>'payroll_id')::uuid from jsonb_array_elements(m->'sources')s);
 binding:=jsonb_build_object('period_start',p_start,'period_end',p_end,'sources',m->'sources','numerator_cents',m->'numerator_cents',
  'original_journals',journals,'attendance_items',items);
 -- Native reversals restore WIP on their own economic/book dates. A later
 -- allocation may not consume that restored WIP on an earlier date.
 with related as(
  select distinct r.journal_id from cp7_attendance_choice.reversals_v1 r
  join cp7_attendance_choice.sources_v1 s on s.decision_id=r.decision_id
  where s.original_debit_journal_line_id in(select(x->>'original_debit_journal_line_id')::uuid from jsonb_array_elements(m->'sources')x)
   and r.journal_id is not null
  union
  select distinct p.cancellation_journal_entry_id from erp.attendance_hpp_pools p
  join erp.attendance_hpp_pool_sources s on s.pool_id=p.id
  where p.status='CANCELLED'and p.cancellation_journal_entry_id is not null
   and s.original_debit_journal_line_id in(select(x->>'original_debit_journal_line_id')::uuid from jsonb_array_elements(m->'sources')x)
 )select coalesce(jsonb_agg(to_jsonb(j)order by j.id),'[]'::jsonb)into restored from related r join erp.journal_entries j on j.id=r.journal_id;
 return jsonb_build_object('native_manifest',m,'source_facts',binding,'source_binding',erp._cp3_manifest_sha256(binding),
  'availability_facts',restored,'amount_cents',(m->>'numerator_cents')::text,
  'max_source_economic_date',(select max(d)from(select(x->'journal'->>'economic_date')::date d from jsonb_array_elements(journals)x
   union all select(x->>'economic_date')::date from jsonb_array_elements(restored)x)z),
  'max_source_book_date',(select max(d)from(select(x->'journal'->>'transaction_date')::date d from jsonb_array_elements(journals)x
   union all select(x->>'transaction_date')::date from jsonb_array_elements(restored)x)z));
end $$;

create function cp7_attendance_choice.command_v1(p_action text,p_payload jsonb,p_request uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set timezone='UTC'as $$
declare initial_access jsonb;actor_id uuid;app_user_id uuid;p jsonb;old_request cp7_attendance_choice.requests_v1;
 reviewed jsonb;c jsonb;d uuid;event_uuid uuid;inverse uuid;f date;t date;ofrom date;oto date;why text;
 a cp7_attendance_choice.allocations_v1;pool erp.attendance_hpp_pools;created jsonb;made jsonb;carry jsonb;
 child uuid;previous_pool uuid;j erp.journal_entries;answer jsonb;proof jsonb;
begin
 initial_access:=cp7_attendance_choice.access_v1(true);actor_id:=auth.uid();app_user_id:=erp.current_app_user_id();
 if p_request is null then raise exception 'CP7_S03_REQUEST_REQUIRED';end if;
 if jsonb_typeof(p_payload)is distinct from'object'or not(p_payload?'review_token')
  or jsonb_typeof(p_payload->'review_token')is distinct from'string'or(p_payload->>'review_token')!~'^[a-f0-9]{64}$'then raise exception 'CP7_S03_REVIEW_REQUIRED';end if;
 p:=cp7_attendance_choice.parse_v1(p_action,p_payload-'review_token');f:=(p->>'period_start')::date;t:=(p->>'period_end')::date;
 ofrom:=(p->>'output_start')::date;oto:=(p->>'output_end')::date;why:=p->>'reason';
 perform pg_advisory_xact_lock(hashtextextended('CP7:S03:REQUEST:'||actor_id::text||':'||p_request::text,0));
 if cp7_attendance_choice.access_v1(true)is distinct from initial_access then raise exception using errcode='42501',message='CP7_S03_ACCESS_CHANGED';end if;
 select*into old_request from cp7_attendance_choice.requests_v1 r where r.actor=actor_id and r.request_id=p_request;
 if old_request.request_id is not null then
  if old_request.action<>p_action or old_request.payload<>p_payload then raise exception 'CP7_S03_REQUEST_CHANGED';end if;
  return old_request.response;
 end if;
 perform erp.pocket_period_lock_v1();
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 perform 1 from erp.accounting_period_control where singleton_id=1 for share;
 perform erp._cp3_lock_business_period(f,t);
 if ofrom is not null then perform erp._cp3_lock_business_period(ofrom,oto);end if;
 if p_action='CANCEL_ALLOCATION'then
  select*into a from cp7_attendance_choice.allocations_v1 where id=cp7_attendance_choice.current_allocation_v1(cp7_attendance_choice.current_v1(f,t));
  if a.id is not null then perform erp._cp3_lock_business_period(a.output_start,a.output_end);end if;
 end if;
 perform erp._cp3_lock_manifest_contractors(f,t);
 if ofrom is not null then perform erp._cp3_lock_manifest_contractors(ofrom,oto);end if;
 -- Do not take a payroll row lock after the period: Native payroll writers
 -- lock that row first. Their period/claim hook fences correction after waits.
 perform 1 from erp.accounting_account_mappings where mapping_key in('WIP','OTHER_EXPENSE')order by mapping_key for share;
 perform 1 from erp.chart_accounts where id in(erp.account_id('WIP'),erp.account_id('OTHER_EXPENSE'))order by id for share;
 if cp7_attendance_choice.access_v1(true)is distinct from initial_access then raise exception using errcode='42501',message='CP7_S03_ACCESS_CHANGED';end if;
 reviewed:=cp7_attendance_choice.review_v1(p_action,p);
 if reviewed->>'review_token'<>p_payload->>'review_token'then raise exception 'CP7_S03_STALE_REVIEW: sumber, pilihan, periode atau hak sudah berubah; tinjau ulang.';end if;
 c:=reviewed->'context'->'source';d:=(reviewed->>'decision_id')::uuid;
 event_uuid:=cp7_attendance_choice.inner_uuid_v1(actor_id,p_request,'EVENT');
 if p_action in('REVERSE','CORRECT')then
  inverse:=cp7_attendance_choice.reverse_choice_v1(d,why,
   case when p_action='REVERSE'then event_uuid else cp7_attendance_choice.inner_uuid_v1(actor_id,p_request,'CHOICE_REVERSE')end,c);
 end if;
 if p_action in('CHOOSE','CORRECT')then
  -- Owning reversal is our own new fact; re-capture its availability dates.
  c:=cp7_attendance_choice.capture_v1(f,t,true);
  d:=cp7_attendance_choice.choose_v1(f,t,p->>'choice',why,event_uuid,c,case when p_action='CORRECT'then d end);
 elsif p_action='ALLOCATE'then
  carry:=cp7_attendance_choice.carry_preview_v1(d,ofrom,oto);
  select hp.id into previous_pool from erp.attendance_hpp_pools hp where hp.period_start=f and hp.period_end=t and hp.status='CANCELLED'
   order by hp.created_at desc,hp.id desc limit 1;
  created:=cp7_attendance_choice.native_create_carry_pool_v1(jsonb_build_object('period_start',f,'period_end',t,'reason',why,
   'correction_of_pool_id',previous_pool,'decision_id',d,'output_start',ofrom,'output_end',oto),
   cp7_attendance_choice.inner_uuid_v1(actor_id,p_request,'NATIVE_CREATE'));
  select*into strict pool from erp.attendance_hpp_pools where id=(created->>'pool_id')::uuid;
  insert into cp7_attendance_choice.allocations_v1(id,decision_id,pool_id,output_start,output_end,manifest_sha256,output_native_provenance,reason,actor,app_user)
  values(event_uuid,d,pool.id,ofrom,oto,pool.source_manifest_sha256,carry->'output_native_provenance',why,actor_id,app_user_id);
  made:=erp.activate_attendance_hpp_pool_v1(pool.id,why,cp7_attendance_choice.inner_uuid_v1(actor_id,p_request,'NATIVE_ACTIVATE'),pool.row_version);
 elsif p_action='CANCEL_ALLOCATION'then
  select*into strict a from cp7_attendance_choice.allocations_v1 where id=(reviewed->>'allocation_id')::uuid;
  select*into strict pool from erp.attendance_hpp_pools where id=a.pool_id;
  child:=cp7_attendance_choice.inner_uuid_v1(actor_id,p_request,'NATIVE_CANCEL');
  insert into cp7_attendance_choice.cancel_context_v1(backend_pid,transaction_id,actor,pool_id,request_id,expected_version,reason)
  values(pg_backend_pid(),txid_current(),actor_id,pool.id,child,pool.row_version,why);
  made:=erp.cancel_attendance_hpp_pool_v1(pool.id,why,child,pool.row_version);
  select*into strict pool from erp.attendance_hpp_pools hp where hp.id=a.pool_id;
  select*into strict j from erp.journal_entries where id=pool.cancellation_journal_entry_id;
  if pool.status<>'CANCELLED'or j.reversal_of_id is distinct from pool.post_journal_entry_id
   or j.economic_date<>erp.bb_business_today_v1()or j.transaction_date<>erp.resolve_accounting_transaction_date(j.economic_date)then
   raise exception 'CP7_S03_NATIVE_CANCEL_DATES';end if;
  insert into cp7_attendance_choice.allocation_reversals_v1(allocation_id,id,journal_id,reason,actor,app_user)
  values(a.id,event_uuid,j.id,why,actor_id,app_user_id);
 end if;
 if p_action='ALLOCATE'then
  select*into strict a from cp7_attendance_choice.allocations_v1 x where x.id=event_uuid;
  select*into strict pool from erp.attendance_hpp_pools hp where hp.id=a.pool_id;
  select*into strict j from erp.journal_entries where id=pool.post_journal_entry_id;
  if pool.status<>'ACTIVE'or pool.source_manifest_sha256 is distinct from carry->>'manifest_sha256'
   or j.economic_date<>oto or j.transaction_date<>erp.resolve_accounting_transaction_date(oto)then raise exception 'CP7_S03_NATIVE_ALLOCATION_DATES';end if;
  perform erp.validate_attendance_hpp_pool_v1(pool.id);
 end if;
 proof:=cp7_attendance_choice.wip_check_v1(c,'[]'::jsonb);
 if cp7_attendance_choice.access_v1(true)is distinct from initial_access then raise exception using errcode='42501',message='CP7_S03_ACCESS_CHANGED';end if;
 answer:=jsonb_build_object('contract_version','cp7.attendance-period-choice-command.v1','action',p_action,'request_id',p_request,
  'period_start',f,'period_end',t,'decision_id',d,'event_id',event_uuid,'amount_cents',c->>'amount_cents',
  'pool_id',pool.id,'native_result',made,'inverse_journal_id',inverse,'dated_WIP',proof,'status','COMMITTED');
 insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
 values('cp7_attendance_choice',d,'POST',jsonb_build_object('lifecycle_action',p_action,'request_id',p_request,'event_id',event_uuid,
  'pool_id',pool.id,'original_source_binding',c->>'source_binding'),app_user_id,why);
 insert into cp7_attendance_choice.requests_v1(actor,request_id,action,payload,response,app_user)
 values(actor_id,p_request,p_action,p_payload,answer,app_user_id);
 return answer;
end $$;

create function cp7_attendance_choice.wip_check_v1(p_capture jsonb,p_planned jsonb)returns jsonb
language plpgsql stable security definer set search_path=''as $$
declare proof jsonb;
begin
 -- One budget per original payroll debit, not a fungible contractor balance.
 -- Originals and linked inverses both remain at their own Native dates.
 with source as(
  select(x->>'original_debit_journal_line_id')::uuid line_id,(x->>'attendance_amount_cents')::bigint cents
  from jsonb_array_elements(p_capture->'native_manifest'->'sources')x
 ),events as(
  select s.line_id,s.cents,j.economic_date,j.transaction_date book_date
  from source s join erp.journal_lines l on l.id=s.line_id join erp.journal_entries j on j.id=l.journal_entry_id
  union all
  select s.line_id,-round(x.attendance_amount*100)::bigint,j.economic_date,j.transaction_date
  from source s join erp.attendance_hpp_pool_sources x on x.original_debit_journal_line_id=s.line_id
  join erp.attendance_hpp_pools p on p.id=x.pool_id and p.status in('ACTIVE','CANCELLED')
  join erp.journal_entries j on j.id=p.post_journal_entry_id
  union all
  select s.line_id,round(x.attendance_amount*100)::bigint,j.economic_date,j.transaction_date
  from source s join erp.attendance_hpp_pool_sources x on x.original_debit_journal_line_id=s.line_id
  join erp.attendance_hpp_pools p on p.id=x.pool_id and p.status='CANCELLED'
  join erp.journal_entries j on j.id=p.cancellation_journal_entry_id
  union all
  select s.line_id,-x.amount_cents,j.economic_date,j.transaction_date
  from source s join cp7_attendance_choice.sources_v1 x on x.original_debit_journal_line_id=s.line_id
  join cp7_attendance_choice.decisions_v1 d on d.id=x.decision_id and d.choice='EXPENSE'
  join erp.journal_entries j on j.id=d.journal_id
  union all
  select s.line_id,x.amount_cents,j.economic_date,j.transaction_date
  from source s join cp7_attendance_choice.sources_v1 x on x.original_debit_journal_line_id=s.line_id
  join cp7_attendance_choice.reversals_v1 r on r.decision_id=x.decision_id and r.journal_id is not null
  join erp.journal_entries j on j.id=r.journal_id
  union all
  select(x->>'line_id')::uuid,(x->>'cents')::bigint,(x->>'economic_date')::date,(x->>'book_date')::date
  from jsonb_array_elements(p_planned)x
 ),dated as(
  select line_id,'ECONOMIC'::text axis,economic_date d,sum(cents)delta from events group by line_id,economic_date
  union all select line_id,'BOOK',book_date,sum(cents)from events group by line_id,book_date
 ),running as(
  select line_id,axis,d,sum(delta)over(partition by line_id,axis order by d)balance from dated
 )select coalesce(jsonb_agg(jsonb_build_object('line_id',line_id,'axis',axis,'date',d,'available_cents',balance::text)
  order by line_id,axis,d),'[]'::jsonb)into proof from running;
 if exists(select 1 from jsonb_array_elements(proof)x where(x->>'available_cents')::numeric<0)then
  raise exception 'CP7_S03_WIP_NEGATIVE_DATED: pilihan ini memakai WIP sebelum tersedia pada tanggal ekonomi atau buku.';end if;
 return jsonb_build_object('all_original_debits_nonnegative_on_every_economic_and_book_cutoff',true,'dated_available_WIP',proof);
end $$;

create function cp7_attendance_choice.assert_period_unclaimed_v1(p_start date,p_end date)returns void
language plpgsql stable security definer set search_path=''as $$
begin
 if cp7_attendance_choice.current_v1(p_start,p_end)is not null then
  raise exception 'CP7_S03_PERIOD_CLAIMED: batalkan pilihan biaya absensi yang aktif melalui alurnya sebelum membuat pool atau menyetujui sumber payroll tambahan.';end if;
end $$;
create function cp7_attendance_choice.assert_payroll_unclaimed_v1(p_payroll uuid)returns void
language plpgsql stable security definer set search_path=''as $$
begin
 if exists(select 1 from cp7_attendance_choice.sources_v1 s join cp7_attendance_choice.decisions_v1 d on d.id=s.decision_id
  where s.payroll_id=p_payroll and not exists(select 1 from cp7_attendance_choice.reversals_v1 r where r.decision_id=d.id))then
  raise exception 'CP7_S03_PAYROLL_CLAIMED: batalkan alokasi carry dan pilihan absensi terkait sebelum membalik payroll sumber.';end if;
end $$;
create function cp7_attendance_choice.assert_journal_unowned_v1(p_journal uuid)returns void
language plpgsql stable security definer set search_path=''as $$
begin
 if exists(select 1 from cp7_attendance_choice.decisions_v1 d where d.journal_id=p_journal)then
  raise exception 'CP7_S03_OWNING_INVERSE_REQUIRED: jurnal beban absensi hanya dibalik melalui pilihan periode yang memilikinya.';end if;
 -- E05 whole-payroll reversal visits cash journals before its original Native
 -- payroll inverse. Fence the first such effect, not only the later cost leg.
 -- An individual payment correction (including PAID->APPROVED reopening)
 -- remains settlement and deliberately does not match this exact context.
 if exists(select 1 from cp7_installment.payments payment
  join erp.journal_entries j on j.id=payment.journal_id and j.source_type='PAYROLL_INSTALLMENT'and j.source_id=payment.id
  join cp7_installment.command_context context on context.backend_pid=pg_backend_pid()and context.transaction_id=txid_current()
   and context.actor=auth.uid()and context.action='REVERSE_PAYROLL'and context.payload->>'payroll_id'=payment.payroll_id::text
  join cp7_attendance_choice.sources_v1 s on s.payroll_id=payment.payroll_id
  where j.id=p_journal and payment.reversal_journal_id is null
   and not exists(select 1 from cp7_attendance_choice.reversals_v1 r where r.decision_id=s.decision_id))then
  raise exception 'CP7_S03_PAYROLL_CLAIMED: lepaskan sumber payroll melalui pilihan biaya absensi yang memilikinya sebelum membalik seluruh payroll.';end if;
end $$;
create function cp7_attendance_choice.assert_cancel_context_v1(p_pool uuid,p_reason text,p_request uuid,p_expected bigint)returns void
language plpgsql volatile security definer set search_path=''as $$
begin
 if exists(select 1 from cp7_attendance_choice.allocations_v1 a where a.pool_id=p_pool)then
  perform cp7_attendance_choice.access_v1(true);
  if not exists(select 1 from cp7_attendance_choice.cancel_context_v1 c
   where c.backend_pid=pg_backend_pid()and c.transaction_id=txid_current()and c.actor=auth.uid()
    and c.pool_id=p_pool and c.request_id=p_request and c.reason=btrim(p_reason)and c.expected_version=p_expected)then
   raise exception 'CP7_S03_OWNING_CARRY_CANCEL_REQUIRED: batalkan alokasi carry melalui pilihan periode yang memilikinya.';end if;
 end if;
end $$;
create function cp7_attendance_choice.assert_output_unclaimed_v1(p_at timestamptz)returns void
language plpgsql stable security definer set search_path=''as $$
begin
 if exists(select 1 from cp7_attendance_choice.allocations_v1 a
  join erp.attendance_hpp_pools p on p.id=a.pool_id and p.status='ACTIVE'
  where erp._cp3_business_date(p_at)between a.output_start and a.output_end)then
  raise exception 'CP7_S03_ACTIVE_CARRY_OUTPUT_LOCKED: batalkan alokasi carry terkait sebelum mencatat hasil jahit baru pada periode tujuannya.';end if;
end $$;
create function cp7_attendance_choice.policy_consumed_v1(p_contractor uuid,p_from date,p_next date)returns boolean
language sql stable security definer set search_path=''as $$
 select exists(
  select 1 from cp7_attendance_choice.sources_v1 s join cp7_attendance_choice.decisions_v1 d on d.id=s.decision_id
  where s.contractor_id=p_contractor and d.period_end>=p_from and(p_next is null or d.period_start<p_next)
   and not exists(select 1 from cp7_attendance_choice.reversals_v1 r where r.decision_id=d.id)
  union all
  select 1 from cp7_attendance_choice.allocations_v1 a join erp.attendance_hpp_pools p on p.id=a.pool_id and p.status='ACTIVE'
  join erp.attendance_hpp_pool_allocations x on x.pool_id=p.id
  where x.contractor_id=p_contractor and a.output_end>=p_from and(p_next is null or a.output_start<p_next)
 )
$$;

create function cp7_attendance_choice.assert_held_bindings_v1(p_contractor uuid)returns void
language plpgsql volatile security definer set search_path=''as $$
declare d record;c jsonb;
begin
 -- A future version can truncate effective_to on an earlier held policy even
 -- when the new version's own interval does not overlap the source period.
 for d in select distinct h.id,h.period_start,h.period_end,h.source_binding
  from cp7_attendance_choice.decisions_v1 h join cp7_attendance_choice.sources_v1 s on s.decision_id=h.id
  where s.contractor_id=p_contractor and not exists(select 1 from cp7_attendance_choice.reversals_v1 r where r.decision_id=h.id)
  order by h.id
 loop
  c:=cp7_attendance_choice.capture_v1(d.period_start,d.period_end,false);
  if c->>'source_binding'<>d.source_binding then raise exception 'CP7_S03_HELD_POLICY_CHANGED: batalkan pilihan absensi yang memakai versi kebijakan ini sebelum mengubah batas versinya.';end if;
 end loop;
end $$;

create function cp7_attendance_choice.assert_policy_mutation_v1(p_contractor uuid,p_from date,p_next date)returns void
language plpgsql stable security definer set search_path=''as $$
begin
 if cp7_attendance_choice.policy_consumed_v1(p_contractor,p_from,p_next)or exists(
  select 1 from cp7_attendance_choice.sources_v1 s join cp7_attendance_choice.decisions_v1 d on d.id=s.decision_id
  join erp.contractor_hpp_policy_versions p on p.id=s.policy_version_id
  where s.contractor_id=p_contractor and not exists(select 1 from cp7_attendance_choice.reversals_v1 r where r.decision_id=d.id)
   and p.effective_from<p_from and(p.effective_to is null or p.effective_to>=p_from))then
  raise exception 'CP7_S03_HELD_POLICY_CHANGED: batalkan alokasi carry dan pilihan absensi yang memakai versi kebijakan ini sebelum mengubahnya.';end if;
end $$;

create function cp7_attendance_choice.assert_active_carry_bindings_v1(p_contractor uuid)returns void
language plpgsql volatile security definer set search_path=''set timezone='UTC'as $$
declare p record;current_manifest jsonb;
begin
 -- Native HPP01 uses the header/source period. A previously excluded P2
 -- contractor has no child allocation yet and must still be considered.
 -- This hook runs immediately after policy INSERT, before its audit sequence.
 for p in select hp.id,hp.source_manifest,hp.source_manifest_sha256
  from cp7_attendance_choice.allocations_v1 a join erp.attendance_hpp_pools hp on hp.id=a.pool_id and hp.status='ACTIVE'
  where jsonb_path_exists(hp.source_manifest,'$.**.contractor_id ? (@ == $c)',jsonb_build_object('c',p_contractor))
   or exists(select 1 from erp.sewing_terminal_events e where e.contractor_id=p_contractor
    and erp._cp3_business_date(e.physical_at)between a.output_start and a.output_end)
  order by hp.id
 loop
  begin
   current_manifest:=cp7_attendance_choice.pool_manifest_v1(p.id);
   if current_manifest is distinct from p.source_manifest
    or erp._cp3_manifest_sha256(current_manifest)is distinct from p.source_manifest_sha256 then
    raise exception 'destination/source facts or policy metadata changed';end if;
  exception when others then
   raise exception 'CP7_S03_ACTIVE_CARRY_POLICY_CHANGED: kebijakan mengubah dasar alokasi carry aktif; batalkan alokasi terkait sebelum mengubah kebijakan. %',sqlerrm;
  end;
 end loop;
end $$;

create function cp7_attendance_choice.pool_date_v1(p_pool uuid,p_original date)returns date
language sql stable security definer set search_path=''as $$
 select coalesce((select a.output_end from cp7_attendance_choice.allocations_v1 a where a.pool_id=p_pool),p_original)
$$;

create function cp7_attendance_choice.carry_preview_v1(p_decision uuid,p_output_start date,p_output_end date)returns jsonb
language plpgsql volatile security definer set search_path=''set timezone='UTC'as $$
declare d cp7_attendance_choice.decisions_v1;c jsonb;dest jsonb;m jsonb;n bigint;q bigint;
begin
 select*into strict d from cp7_attendance_choice.decisions_v1 where id=p_decision;
 if d.choice<>'CARRY'or exists(select 1 from cp7_attendance_choice.reversals_v1 r where r.decision_id=d.id)then raise exception 'CP7_S03_CURRENT_CARRY_REQUIRED';end if;
 if p_output_start is null or p_output_end is null or p_output_end<p_output_start or p_output_end-p_output_start>366
  or p_output_start<=d.period_end or p_output_end>erp.bb_business_today_v1()then raise exception 'CP7_S03_SEPARATE_LATER_OUTPUT_PERIOD_REQUIRED';end if;
 c:=cp7_attendance_choice.capture_v1(d.period_start,d.period_end,true);
 if c->>'source_binding'<>d.source_binding then raise exception 'CP7_S03_SOURCE_CHANGED';end if;
 if p_output_end<(c->>'max_source_book_date')::date or p_output_end<(c->>'max_source_economic_date')::date then
  raise exception 'CP7_S03_ALLOCATION_BEFORE_WIP_AVAILABLE: tanggal alokasi mendahului pengakuan atau pemulihan WIP pada tanggal ekonomi atau buku.';end if;
 dest:=erp._build_attendance_hpp_manifest_v1(p_output_start,p_output_end);perform erp._assert_attendance_hpp_manifest_v1(dest);
 q:=(dest->>'denominator_qty')::bigint;n:=d.amount_cents;
 if q<=0 then raise exception 'CP7_S03_LATER_OUTPUT_NOT_AVAILABLE: hasil jahit mandor biasa pada periode tujuan belum tersedia; biaya tetap menunggu di WIP.';end if;
 m:=jsonb_build_object('contract_version','CP7_ATTENDANCE_CARRY_TWO_EXACT_PERIODS_V1',
  'period_start',d.period_start,'period_end',d.period_end,'output_start',p_output_start,'output_end',p_output_end,
  'decision_id',d.id,'source_binding',d.source_binding,'availability_facts',c->'availability_facts',
  'source_native_manifest',c->'native_manifest','output_destination_facts',jsonb_build_object(
   'contract_version','CP7_NATIVE_SEWING_DESTINATIONS_ONLY_V1','period_start',dest->'period_start','period_end',dest->'period_end',
   'denominator_qty',dest->'denominator_qty','destinations',dest->'destinations'),
  'sources',c->'native_manifest'->'sources','destinations',dest->'destinations','numerator_cents',n,'denominator_qty',q);
 return jsonb_build_object('status','READY','manifest',m,'manifest_sha256',erp._cp3_manifest_sha256(m),
  'numerator_amount',n/100.0,'denominator_qty',q,'unit_cost_per_sewn_pcs',(n/100.0)/q,
  'output_native_provenance',dest);
end $$;

create function cp7_attendance_choice.pool_manifest_v1(p_pool uuid)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare a cp7_attendance_choice.allocations_v1;
begin
 select*into strict a from cp7_attendance_choice.allocations_v1 where pool_id=p_pool;
 return cp7_attendance_choice.carry_preview_v1(a.decision_id,a.output_start,a.output_end)->'manifest';
end $$;
create function cp7_attendance_choice.assert_carry_manifest_v1(p_manifest jsonb)returns void
language plpgsql immutable security invoker set search_path=''as $$
begin
 perform erp._cp3_assert_closed_json_object(p_manifest,
  array['contract_version','period_start','period_end','output_start','output_end','decision_id','source_binding','availability_facts','source_native_manifest','output_destination_facts','sources','destinations','numerator_cents','denominator_qty'],
  array['contract_version','period_start','period_end','output_start','output_end','decision_id','source_binding','availability_facts','source_native_manifest','output_destination_facts','sources','destinations','numerator_cents','denominator_qty'],'S03 carry manifest');
 perform erp._assert_attendance_hpp_manifest_v1(p_manifest->'source_native_manifest');
 perform erp._cp3_assert_closed_json_object(p_manifest->'output_destination_facts',
  array['contract_version','period_start','period_end','denominator_qty','destinations'],
  array['contract_version','period_start','period_end','denominator_qty','destinations'],'S03 destination-only facts');
 if p_manifest->'output_destination_facts'->>'contract_version'<>'CP7_NATIVE_SEWING_DESTINATIONS_ONLY_V1'
  or jsonb_typeof(p_manifest->'output_destination_facts'->'destinations')is distinct from'array'
  or jsonb_typeof(p_manifest->'output_destination_facts'->'denominator_qty')is distinct from'number'then raise exception 'CP7_S03_DESTINATION_SCOPE';end if;
 if p_manifest->>'contract_version'<>'CP7_ATTENDANCE_CARRY_TWO_EXACT_PERIODS_V1'
  or p_manifest->'sources'is distinct from p_manifest->'source_native_manifest'->'sources'
  or p_manifest->'destinations'is distinct from p_manifest->'output_destination_facts'->'destinations'
  or p_manifest->'numerator_cents'is distinct from p_manifest->'source_native_manifest'->'numerator_cents'
  or p_manifest->'denominator_qty'is distinct from p_manifest->'output_destination_facts'->'denominator_qty'
  or(p_manifest->'source_native_manifest'->>'denominator_qty')::bigint<>0
  or(p_manifest->>'output_start')::date<=(p_manifest->>'period_end')::date
  or p_manifest->>'period_start'is distinct from p_manifest->'source_native_manifest'->>'period_start'
  or p_manifest->>'period_end'is distinct from p_manifest->'source_native_manifest'->>'period_end'
  or p_manifest->>'output_start'is distinct from p_manifest->'output_destination_facts'->>'period_start'
  or p_manifest->>'output_end'is distinct from p_manifest->'output_destination_facts'->>'period_end'then raise exception 'CP7_S03_CARRY_MANIFEST';end if;
end $$;

create function public.erp_cp7_get_attendance_choice_v1(p_period_start date,p_period_end date,p_offset integer default 0,p_limit integer default 25)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_attendance_choice.workspace_v1(p_period_start,p_period_end,p_offset,p_limit)$$;
create function public.erp_cp7_preview_attendance_choice_v1(p_action text,p_payload jsonb)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_attendance_choice.review_v1(p_action,p_payload)-'context'$$;
create function public.erp_cp7_save_attendance_choice_v1(p_action text,p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_attendance_choice.command_v1(p_action,p_payload,p_request)$$;

revoke all on all tables in schema cp7_attendance_choice from public,anon,authenticated,service_role;
revoke all on all functions in schema cp7_attendance_choice from public,anon,authenticated,service_role;
revoke all on function public.erp_cp7_get_attendance_choice_v1(date,date,integer,integer),public.erp_cp7_preview_attendance_choice_v1(text,jsonb),public.erp_cp7_save_attendance_choice_v1(text,jsonb,uuid)
 from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_get_attendance_choice_v1(date,date,integer,integer),public.erp_cp7_preview_attendance_choice_v1(text,jsonb),public.erp_cp7_save_attendance_choice_v1(text,jsonb,uuid)to authenticated;

