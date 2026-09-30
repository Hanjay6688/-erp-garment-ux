-- Reviewed native miscellaneous income/expense. No new accounting engine or
-- admission delta. Browser callers never acquire ERP DML or native writer EXEC.
create role cp7_misc_read nologin noinherit nosuperuser nocreatedb nocreaterole noreplication bypassrls;
create role cp7_misc_write nologin noinherit nosuperuser nocreatedb nocreaterole noreplication;
create schema cp7_misc authorization cp7_misc_read;
revoke all on schema cp7_misc from public,anon,authenticated,service_role,cp7_capture;
grant usage,create on schema cp7_misc to cp7_misc_write;
grant usage on schema erp,auth to cp7_misc_read;
grant usage on schema auth to cp7_misc_write;
grant execute on function auth.uid(),auth.jwt(),erp.get_my_access_v1(),erp.has_permission(text) to cp7_misc_read;
grant execute on function auth.uid() to cp7_misc_write;
grant select on erp.misc_finance_transactions,erp.misc_finance_categories,erp.cash_accounts,erp.chart_accounts,erp.accounting_account_mappings,erp.journal_entries,erp.journal_lines to cp7_misc_read;
create table cp7_misc.requests(actor uuid not null,request_id uuid not null,action text not null,payload jsonb not null,response jsonb,primary key(actor,request_id));
create table cp7_misc.command_context(backend_pid integer not null,transaction_id bigint not null,actor uuid not null,request_id uuid not null,action text not null,payload jsonb not null,primary key(backend_pid,transaction_id));
alter table cp7_misc.requests owner to cp7_misc_write;
alter table cp7_misc.command_context owner to cp7_misc_write;
alter table cp7_misc.requests enable row level security;
alter table cp7_misc.command_context enable row level security;
create policy cp7_misc_requests_deny on cp7_misc.requests for all to public using(false)with check(false);
create policy cp7_misc_context_deny on cp7_misc.command_context for all to public using(false)with check(false);
revoke all on cp7_misc.requests,cp7_misc.command_context from public,anon,authenticated,service_role,cp7_capture,cp7_misc_read;

create function cp7_misc.access_now() returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare a jsonb;
begin
 if auth.uid() is null or coalesce(auth.jwt()->>'role','')<>'authenticated' then raise exception using errcode='42501',message='CP7_MISC_ACCESS_DENIED';end if;
 a:=erp.get_my_access_v1();
 if a->'allowed' is distinct from 'true'::jsonb or not erp.has_permission('finance.journal.view') or not erp.has_permission('finance.cash.view') then raise exception using errcode='42501',message='CP7_MISC_ACCESS_DENIED';end if;
 -- The accepted native writer is OWNER/ADMIN only. View permissions cannot
 -- turn a custom role into a financial writer.
 if coalesce(a->'profile'->>'role_code','') not in('OWNER','ADMIN') then raise exception using errcode='42501',message='CP7_MISC_OWNER_ADMIN_REQUIRED';end if;
 return a;
end $$;

create function cp7_misc.category(p_id uuid) returns jsonb
language sql stable security definer set search_path='' as $$
 select jsonb_build_object('id',c.id,'code',c.category_code,'name',c.category_name,'type',c.category_type,
  'account_id',a.id,'account_code',a.account_code,'account_name',a.account_name,
  'eligible',c.is_active and a.is_active and a.is_postable and a.account_type=case c.category_type when 'OTHER_INCOME' then 'REVENUE' when 'OTHER_EXPENSE' then 'EXPENSE' end
   and not exists(select 1 from erp.accounting_account_mappings m where m.account_id=a.id and m.mapping_key not in('OTHER_INCOME','OTHER_EXPENSE')),
  'review_token',md5(jsonb_build_object('category',to_jsonb(c),'account',to_jsonb(a),'mappings',coalesce((select jsonb_agg(to_jsonb(m) order by m.mapping_key)from erp.accounting_account_mappings m where m.account_id=a.id),'[]'))::text))
 from erp.misc_finance_categories c join erp.chart_accounts a on a.id=c.default_account_id where c.id=p_id
$$;
create function cp7_misc.cash(p_id uuid) returns jsonb
language sql stable security definer set search_path='' as $$
 select jsonb_build_object('id',c.id,'code',c.cash_account_code,'name',c.cash_account_name,'kind',c.account_kind,
  'account_id',a.id,'account_code',a.account_code,'account_name',a.account_name,
  'eligible',c.is_active and a.is_active and a.is_postable and a.account_type='ASSET'
   and not exists(select 1 from erp.accounting_account_mappings m where m.account_id=a.id and m.mapping_key not in('CASH','BANK')),
  'review_token',md5(jsonb_build_object('cash',to_jsonb(c),'account',to_jsonb(a),'mappings',coalesce((select jsonb_agg(to_jsonb(m) order by m.mapping_key)from erp.accounting_account_mappings m where m.account_id=a.id),'[]'))::text))
 from erp.cash_accounts c join erp.chart_accounts a on a.id=c.coa_account_id where c.id=p_id
$$;
create function cp7_misc.source(p_id uuid) returns jsonb
language plpgsql stable security definer set search_path='' set TimeZone='UTC' as $$
declare t erp.misc_finance_transactions;c jsonb;cash jsonb;journals jsonb;fingerprint jsonb;
begin
 select * into t from erp.misc_finance_transactions where id=p_id;if t.id is null then return null;end if;
 c:=cp7_misc.category(t.category_id);cash:=cp7_misc.cash(t.cash_account_id);
 select coalesce(jsonb_agg(jsonb_build_object('id',j.id,'number',j.journal_number,'status',j.status,'reversal_of_id',j.reversal_of_id,
  'economic_date',j.economic_date,'transaction_date',j.transaction_date,'posting_at',j.posting_at,'period_shifted',j.period_shifted,
  'debit',(select coalesce(sum(l.debit),0)::text from erp.journal_lines l where l.journal_entry_id=j.id),
  'credit',(select coalesce(sum(l.credit),0)::text from erp.journal_lines l where l.journal_entry_id=j.id))order by j.posting_at,j.id),'[]')into journals
 from erp.journal_entries j where(j.source_type='MISC_FINANCE' and j.source_id=t.id)
  or j.reversal_of_id in(select id from erp.journal_entries where source_type='MISC_FINANCE' and source_id=t.id);
 select jsonb_build_object('transaction',to_jsonb(t),'category',c,'cash',cash,'journals',journals,
  'lines',coalesce(jsonb_agg(to_jsonb(l)order by l.id),'[]'))into fingerprint
 from erp.journal_lines l where l.journal_entry_id in(select (x->>'id')::uuid from jsonb_array_elements(journals)x);
 return jsonb_build_object('id',t.id,'number',t.transaction_number,'type',t.transaction_type,'category_id',t.category_id,
  'category_name',c->>'name','category_eligible',coalesce((c->>'eligible')::boolean,false),'cash_account_id',t.cash_account_id,
  'cash_account_name',cash->>'name','cash_eligible',coalesce((cash->>'eligible')::boolean,false),'physical_at',t.physical_at,
  'amount',t.amount::text,'counterparty_name',t.counterparty_name,'reference_number',t.reference_number,'notes',t.notes,
  'status',t.status,'review_token',md5(fingerprint::text),'category_source',c,'cash_source',cash,'journals',journals);
end $$;

create function cp7_misc.workspace(p_query jsonb) returns jsonb
language plpgsql stable security invoker set search_path='' set TimeZone='UTC' as $$
declare q text;st text;selected uuid;off integer;coff integer;boff integer;cats jsonb;banks jsonb;rows jsonb;detail jsonb;total bigint;ct bigint;bt bigint;
begin
 perform cp7_misc.access_now();
 if jsonb_typeof(p_query)is distinct from 'object'
  or exists(select 1 from jsonb_object_keys(p_query)k where k not in('q','status','transaction_id','offset','category_offset','cash_offset'))
  or exists(select 1 from jsonb_each(p_query)e where e.key in('q','status','transaction_id')and jsonb_typeof(e.value)not in('string','null'))
  or exists(select 1 from jsonb_each(p_query)e where e.key in('offset','category_offset','cash_offset')and(jsonb_typeof(e.value)<>'number'or e.value::text!~'^[0-9]{1,7}$'))then raise exception 'CP7_MISC_QUERY';end if;
 begin selected:=(p_query->>'transaction_id')::uuid;exception when invalid_text_representation then raise exception 'CP7_MISC_QUERY';end;
 q:=btrim(coalesce(p_query->>'q',''));st:=p_query->>'status';off:=coalesce((p_query->>'offset')::integer,0);coff:=coalesce((p_query->>'category_offset')::integer,0);boff:=coalesce((p_query->>'cash_offset')::integer,0);
 if length(q)>120 or(st is not null and st not in('DRAFT','POSTED','REVERSED'))or off not between 0 and 1000000 or coff not between 0 and 1000000 or boff not between 0 and 1000000 then raise exception 'CP7_MISC_QUERY';end if;
 select count(*)into total from erp.misc_finance_transactions t where(st is null or t.status=st)and(q=''or strpos(lower(concat_ws(' ',t.transaction_number,t.counterparty_name,t.reference_number,t.notes)),lower(q))>0);
 select coalesce(jsonb_agg(cp7_misc.source(t.id)order by t.physical_at desc,t.id),'[]')into rows from(select * from erp.misc_finance_transactions t where(st is null or t.status=st)and(q=''or strpos(lower(concat_ws(' ',t.transaction_number,t.counterparty_name,t.reference_number,t.notes)),lower(q))>0)order by t.physical_at desc,t.id limit 25 offset off)t;
 with eligible as materialized(select cp7_misc.category(c.id)value from erp.misc_finance_categories c),all_rows as materialized(select value from eligible where value->'eligible'='true'::jsonb),slice as(select value from all_rows order by value->>'code',value->>'id' limit 25 offset coff)
 select(select count(*)from all_rows),coalesce((select jsonb_agg(value order by value->>'code',value->>'id')from slice),'[]')into ct,cats;
 with eligible as materialized(select cp7_misc.cash(c.id)value from erp.cash_accounts c),all_rows as materialized(select value from eligible where value->'eligible'='true'::jsonb),slice as(select value from all_rows order by value->>'code',value->>'id' limit 25 offset boff)
 select(select count(*)from all_rows),coalesce((select jsonb_agg(value order by value->>'code',value->>'id')from slice),'[]')into bt,banks;
 if selected is not null then detail:=cp7_misc.source(selected);if detail is null then raise exception 'CP7_MISC_NOT_FOUND';end if;end if;
 return jsonb_build_object('contract_version','cp7.misc-read.v1','captured_at',statement_timestamp(),'scope','CURRENT_NATIVE_MISC_FINANCE_DOCUMENTS',
  'query',jsonb_build_object('q',q,'status',st,'transaction_id',selected),
  'page',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',25,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows)end),
  'categories',jsonb_build_object('rows',cats,'total',ct::text,'offset',coff,'limit',25,'next_offset',case when coff+jsonb_array_length(cats)<ct then coff+jsonb_array_length(cats)end),
  'cash_accounts',jsonb_build_object('rows',banks,'total',bt::text,'offset',boff,'limit',25,'next_offset',case when boff+jsonb_array_length(banks)<bt then boff+jsonb_array_length(banks)end),'detail',detail);
end $$;

create function cp7_misc.validate(p_action text,p jsonb) returns void
language plpgsql immutable security invoker set search_path='' as $$
declare allowed text[];k text;
begin
 allowed:=array['transaction_id','review_token','change_reason'];
 if p_action='SAVE'then allowed:=allowed||array['transaction_number','transaction_type','category_id','category_review_token','cash_account_id','cash_review_token','physical_at','amount','counterparty_name','reference_number','notes'];
 elsif p_action not in('POST','REVERSE')or p_action is null then raise exception 'CP7_MISC_ACTION';end if;
 if jsonb_typeof(p)is distinct from 'object'or not p ?& allowed or exists(select 1 from jsonb_object_keys(p)as x(field)where not x.field=any(allowed))then raise exception 'CP7_MISC_FIELDS';end if;
 foreach k in array allowed loop
  if k in('counterparty_name','reference_number','notes')or(p_action='SAVE'and k in('transaction_id','review_token'))then
   if jsonb_typeof(p->k)not in('string','null')then raise exception 'CP7_MISC_FIELDS';end if;
  elsif jsonb_typeof(p->k)is distinct from 'string'then raise exception 'CP7_MISC_FIELDS';end if;
 end loop;
 if(p->>'transaction_id'is not null and(p->>'transaction_id')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
  or(p->>'review_token'is not null and(p->>'review_token')!~'^[a-f0-9]{32}$')
  or(p_action='SAVE'and(p->>'transaction_id'is null)is distinct from(p->>'review_token'is null))
  or length(btrim(p->>'change_reason'))not between 5 and 1000 then raise exception 'CP7_MISC_FIELDS';end if;
 if p_action='SAVE'then
  if length(btrim(p->>'transaction_number'))not between 1 and 60 or(p->>'transaction_type')not in('OTHER_INCOME','OTHER_EXPENSE')
   or(p->>'category_id')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'or(p->>'cash_account_id')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
   or(p->>'category_review_token')!~'^[a-f0-9]{32}$'or(p->>'cash_review_token')!~'^[a-f0-9]{32}$'
   or(p->>'amount')!~'^(0|[1-9][0-9]{0,17})(\.[0-9]{1,2})?$'or(p->>'amount')::numeric<=0
   or(p->>'physical_at')!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?(Z|[+-][0-9]{2}:[0-9]{2})$'
   or length(p->>'counterparty_name')>150 or length(p->>'reference_number')>100 or length(p->>'notes')>2000 then raise exception 'CP7_MISC_FIELDS';end if;
 end if;
end $$;

create function cp7_misc.apply_command(p_action text,p jsonb,p_request uuid) returns jsonb
language plpgsql volatile security definer set search_path='' set TimeZone='UTC' as $$
declare a jsonb;t erp.misc_finance_transactions;ident uuid:=(p->>'transaction_id')::uuid;cat uuid;bank uuid;c jsonb;cash jsonb;physical timestamptz;
begin
 a:=cp7_misc.access_now();perform cp7_misc.validate(p_action,p);
 if not exists(select 1 from cp7_misc.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid()and request_id=p_request and action=p_action and payload=p)then raise exception using errcode='42501',message='CP7_MISC_PRIVATE_CONTEXT_REQUIRED';end if;
 if ident is not null then select * into t from erp.misc_finance_transactions where id=ident for update;if t.id is null then raise exception 'CP7_MISC_NOT_FOUND';end if;end if;
 -- Lock mutable category/cash/account identities and mapping insertions before
 -- comparing the reviewed source. Native journal posting retains its own close
 -- lock and determines the accounting date; no caller can bypass either guard.
 lock table erp.accounting_account_mappings in share mode;
 cat:=case when p_action='SAVE'then(p->>'category_id')::uuid else t.category_id end;
 bank:=case when p_action='SAVE'then(p->>'cash_account_id')::uuid else t.cash_account_id end;
 perform 1 from erp.misc_finance_categories where id=cat for share;
 perform 1 from erp.cash_accounts where id=bank for share;
 perform 1 from erp.chart_accounts where id in(select default_account_id from erp.misc_finance_categories where id=cat union select coa_account_id from erp.cash_accounts where id=bank)order by id for share;
 if ident is not null then
  perform 1 from erp.journal_entries j where(j.source_type='MISC_FINANCE'and j.source_id=ident)or j.reversal_of_id in(select id from erp.journal_entries where source_type='MISC_FINANCE'and source_id=ident)order by j.id for update;
  perform 1 from erp.journal_lines l where l.journal_entry_id in(select id from erp.journal_entries where source_type='MISC_FINANCE'and source_id=ident)order by l.id for update;
 end if;
 if cp7_misc.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_MISC_ACCESS_CHANGED';end if;
 if ident is not null and cp7_misc.source(ident)->>'review_token'is distinct from p->>'review_token'then raise exception 'CP7_MISC_REVIEW_CHANGED';end if;
 c:=cp7_misc.category(cat);cash:=cp7_misc.cash(bank);
 if p_action in('SAVE','POST')then
  if c is null or c->'eligible'is distinct from 'true'::jsonb or cash is null or cash->'eligible'is distinct from 'true'::jsonb then raise exception 'CP7_MISC_SOURCE_UNAVAILABLE';end if;
  if p_action='SAVE'then
   if c->>'type'is distinct from p->>'transaction_type'or c->>'review_token'is distinct from p->>'category_review_token'or cash->>'review_token'is distinct from p->>'cash_review_token'then raise exception 'CP7_MISC_OPTIONS_CHANGED';end if;
   begin physical:=(p->>'physical_at')::timestamptz;exception when invalid_datetime_format or datetime_field_overflow then raise exception 'CP7_MISC_PHYSICAL_DATE';end;
   if physical>statement_timestamp()then raise exception 'CP7_MISC_FUTURE_DATE';end if;
  end if;
 end if;
 perform set_config('app.change_reason',btrim(p->>'change_reason'),true);
 if p_action='SAVE'then
  if ident is null then
   insert into erp.misc_finance_transactions(transaction_number,transaction_type,category_id,physical_at,amount,cash_account_id,counterparty_name,reference_number,notes,created_by)
   values(btrim(p->>'transaction_number'),p->>'transaction_type',cat,physical,(p->>'amount')::numeric,bank,p->>'counterparty_name',p->>'reference_number',p->>'notes',erp.current_app_user_id())returning id into ident;
  else
   if t.status<>'DRAFT'then raise exception 'CP7_MISC_DRAFT_ONLY';end if;
   update erp.misc_finance_transactions set transaction_number=btrim(p->>'transaction_number'),transaction_type=p->>'transaction_type',category_id=cat,physical_at=physical,amount=(p->>'amount')::numeric,cash_account_id=bank,counterparty_name=p->>'counterparty_name',reference_number=p->>'reference_number',notes=p->>'notes',updated_at=clock_timestamp()where id=ident;
  end if;
  -- Native trg_audit_misc_finance_transactions records INSERT/UPDATE with the
  -- app.change_reason already set above. Do not duplicate it with a new action.
 elsif p_action='POST'then
  if t.status<>'DRAFT'then raise exception 'CP7_MISC_DRAFT_ONLY';end if;
  if t.physical_at>statement_timestamp()then raise exception 'CP7_MISC_FUTURE_DATE';end if;
  perform erp.post_misc_finance(ident);
 else
  if t.status<>'POSTED'then raise exception 'CP7_MISC_POSTED_ONLY';end if;
  perform erp.reverse_misc_finance(ident,btrim(p->>'change_reason'));
 end if;
 if cp7_misc.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_MISC_ACCESS_CHANGED';end if;
 return jsonb_build_object('transaction_id',ident,'document',cp7_misc.source(ident));
end $$;

create function cp7_misc.command(p_action text,p_payload jsonb,p_request uuid,p_expected text) returns jsonb
language plpgsql volatile security invoker set search_path='' as $$
declare a jsonb;saved cp7_misc.requests;r jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_misc.access_now();perform cp7_misc.validate(p_action,p_payload);
 -- This native relation has no row_version. The complete reviewed source token
 -- is mandatory on updates/post/inverse; never invent a frontend revision.
 if p_request is null or p_expected is not null then raise exception 'CP7_MISC_COMMAND_FIELDS';end if;
 insert into cp7_misc.requests(actor,request_id,action,payload)values(auth.uid(),p_request,p_action,p_payload)on conflict do nothing;
 select * into saved from cp7_misc.requests where actor=auth.uid()and request_id=p_request for update;
 if cp7_misc.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_MISC_ACCESS_CHANGED';end if;
 if saved.action<>p_action or saved.payload is distinct from p_payload then raise exception 'CP7_MISC_REQUEST_CHANGED';end if;
 if saved.response is not null then return saved.response;end if;
 insert into cp7_misc.command_context values(pg_backend_pid(),txid_current(),auth.uid(),p_request,p_action,p_payload);
 r:=cp7_misc.apply_command(p_action,p_payload,p_request);
 delete from cp7_misc.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 if cp7_misc.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_MISC_ACCESS_CHANGED';end if;
 r:=r||jsonb_build_object('contract_version','cp7.misc-outcome.v1','kind','COMMITTED_OUTCOME','action',p_action,'request_id',p_request);
 update cp7_misc.requests set response=r where actor=auth.uid()and request_id=p_request;
 return r;
end $$;
create function public.erp_cp7_get_misc_finance_v1(p_query jsonb) returns jsonb
language sql stable security definer set search_path='' as $$select cp7_misc.workspace(p_query)$$;
create function public.erp_cp7_save_misc_finance_v1(p_action text,p_payload jsonb,p_request uuid,p_expected text) returns jsonb
language sql volatile security definer set search_path='' as $$select cp7_misc.command(p_action,p_payload,p_request,p_expected)$$;
alter function cp7_misc.access_now()owner to cp7_misc_read;
alter function cp7_misc.category(uuid)owner to cp7_misc_read;
alter function cp7_misc.cash(uuid)owner to cp7_misc_read;
alter function cp7_misc.source(uuid)owner to cp7_misc_read;
alter function cp7_misc.workspace(jsonb)owner to cp7_misc_read;
alter function cp7_misc.validate(text,jsonb)owner to cp7_misc_read;
alter function cp7_misc.apply_command(text,jsonb,uuid)owner to postgres;
alter function cp7_misc.command(text,jsonb,uuid,text)owner to cp7_misc_write;
grant create on schema public to cp7_misc_read,cp7_misc_write;
alter function public.erp_cp7_get_misc_finance_v1(jsonb)owner to cp7_misc_read;
alter function public.erp_cp7_save_misc_finance_v1(text,jsonb,uuid,text)owner to cp7_misc_write;
revoke create on schema public,cp7_misc from cp7_misc_read,cp7_misc_write;
revoke all on all functions in schema cp7_misc from public,anon,authenticated,service_role,cp7_capture;
grant execute on function cp7_misc.access_now(),cp7_misc.validate(text,jsonb),cp7_misc.apply_command(text,jsonb,uuid)to cp7_misc_write;
grant usage on schema cp7_misc to postgres;
grant select on cp7_misc.command_context to postgres;
grant execute on function cp7_misc.access_now(),cp7_misc.validate(text,jsonb),cp7_misc.category(uuid),cp7_misc.cash(uuid),cp7_misc.source(uuid)to postgres;
revoke all on function public.erp_cp7_get_misc_finance_v1(jsonb),public.erp_cp7_save_misc_finance_v1(text,jsonb,uuid,text)from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_misc_finance_v1(jsonb),public.erp_cp7_save_misc_finance_v1(text,jsonb,uuid,text)to authenticated;
