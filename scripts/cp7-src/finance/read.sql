-- P13 source reader: accepted owner report, dated readiness and immutable filings.
-- It cannot close, reopen, recost or post a financial document.
create role cp7_finance_read nologin noinherit nosuperuser nocreatedb nocreaterole noreplication bypassrls;
create schema cp7_finance authorization cp7_finance_read;
revoke all on schema cp7_finance from public,anon,authenticated,service_role,cp7_capture;
grant usage on schema erp,auth to cp7_finance_read;
grant execute on function auth.uid(),auth.jwt(),erp.get_my_access_v1(),erp.has_permission(text),erp.get_owner_financial_snapshot_v2(date,date,date),erp.accounting_close_preflight_v1(date) to cp7_finance_read;
grant select on erp.accounting_close_filings_v1 to cp7_finance_read;

create function cp7_finance.access_now() returns void
language plpgsql stable security invoker set search_path='' as $$
declare a jsonb;
begin
 if auth.uid() is null or coalesce(auth.jwt()->>'role','')<>'authenticated' then raise exception using errcode='42501',message='CP7_FINANCE_ACCESS_DENIED';end if;
 a:=erp.get_my_access_v1();
 if a->'allowed' is distinct from 'true'::jsonb or not erp.has_permission('finance.reports.view') then raise exception using errcode='42501',message='CP7_FINANCE_ACCESS_DENIED';end if;
 -- Preserve the accepted owner report's native role boundary. This reader does
 -- not silently broaden it to a custom role or modify either native guard.
 if coalesce(a->'profile'->>'role_code','') not in('OWNER','ADMIN') then raise exception using errcode='42501',message='CP7_FINANCE_OWNER_ADMIN_REQUIRED';end if;
end $$;

create function cp7_finance.exact_numbers(p jsonb) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare r jsonb;
begin
 case jsonb_typeof(p)
 when 'number' then return to_jsonb(p::text);
 when 'object' then select coalesce(jsonb_object_agg(k,cp7_finance.exact_numbers(v)),'{}') into r from jsonb_each(p) e(k,v);return r;
 when 'array' then select coalesce(jsonb_agg(cp7_finance.exact_numbers(v) order by n),'[]') into r from jsonb_array_elements(p) with ordinality e(v,n);return r;
 else return p;
 end case;
end $$;

create function cp7_finance.workspace(p_query jsonb) returns jsonb
language plpgsql stable security invoker set search_path='' set TimeZone='UTC' as $$
declare from_day date;to_day date;as_of date;chosen uuid;off integer;n integer;total bigint;rows jsonb;f erp.accounting_close_filings_v1;detail jsonb:=null;snapshot jsonb;preflight jsonb:=null;
begin
 perform cp7_finance.access_now();
 if jsonb_typeof(p_query) is distinct from 'object' or not p_query ?& array['from','to','as_of']
  or exists(select 1 from jsonb_object_keys(p_query) k where k not in('from','to','as_of','filing_id','offset','limit'))
  or exists(select 1 from jsonb_each(p_query) e where e.key in('from','to','as_of') and(jsonb_typeof(e.value)<>'string' or (e.value#>>'{}')!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$'))
  or(p_query ? 'filing_id' and jsonb_typeof(p_query->'filing_id') not in('string','null'))
  or exists(select 1 from jsonb_each(p_query) e where e.key in('offset','limit') and(jsonb_typeof(e.value)<>'number' or e.value::text!~'^[0-9]{1,7}$')) then raise exception 'CP7_FINANCE_QUERY';end if;
 from_day:=(p_query->>'from')::date;to_day:=(p_query->>'to')::date;as_of:=(p_query->>'as_of')::date;chosen:=(p_query->>'filing_id')::uuid;off:=coalesce((p_query->>'offset')::integer,0);n:=coalesce((p_query->>'limit')::integer,25);
 if from_day is null or to_day is null or as_of is null or from_day>to_day or to_day>as_of or as_of>(statement_timestamp() at time zone 'Asia/Jakarta')::date or off not between 0 and 1000000 or n not between 1 and 100 then raise exception 'CP7_FINANCE_QUERY';end if;
 snapshot:=erp.get_owner_financial_snapshot_v2(from_day,to_day,as_of);
 -- Bound the complete native payload; never truncate blockers into a false READY.
 if snapshot is null or jsonb_typeof(snapshot) is distinct from 'object' or octet_length(snapshot::text)>1000000 then raise exception 'CP7_FINANCE_REPORT_INCOMPLETE';end if;
 if erp.has_permission('finance.period_close.manage') then preflight:=erp.accounting_close_preflight_v1(as_of);end if;
 select count(*) into total from erp.accounting_close_filings_v1;
 select coalesce(jsonb_agg(jsonb_build_object('id',x.id,'closed_through',x.closed_through,'previous_closed_through',x.previous_closed_through,'filed_at',x.filed_at,'reason',x.reason,'filed_status',x.readiness->>'status') order by x.filed_at desc,x.id),'[]') into rows
 from(select * from erp.accounting_close_filings_v1 order by filed_at desc,id limit n offset off)x;
 if chosen is not null then
  select * into f from erp.accounting_close_filings_v1 where id=chosen;
  if f.id is null then raise exception 'CP7_FINANCE_FILING_NOT_FOUND';end if;
  if f.closed_through<>as_of then raise exception 'CP7_FINANCE_FILING_DATE_MISMATCH';end if;
  if octet_length(f.gl_balances::text)+octet_length(f.readiness::text)>1000000 then raise exception 'CP7_FINANCE_FILING_INCOMPLETE';end if;
  detail:=jsonb_build_object('id',f.id,'closed_through',f.closed_through,'previous_closed_through',f.previous_closed_through,'filed_at',f.filed_at,'reason',f.reason,'basis','IMMUTABLE_AS_FILED_GL_BALANCES','readiness',cp7_finance.exact_numbers(f.readiness),'gl_balances',cp7_finance.exact_numbers(f.gl_balances),'source_hash',md5(to_jsonb(f)::text));
 end if;
 return jsonb_build_object('contract_version','cp7.finance-report.v1','captured_at',statement_timestamp(),'knowledge_basis','CURRENT_RECORDED_KNOWLEDGE','historical_knowledge','NOT_RECONSTRUCTED','snapshot',cp7_finance.exact_numbers(snapshot),'close_preflight',cp7_finance.exact_numbers(preflight),'filings',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',n,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows) else null end),'filing',detail);
end $$;
create function public.erp_cp7_get_finance_report_v1(p_query jsonb) returns jsonb
language sql stable security definer set search_path='' as $$select cp7_finance.workspace(p_query)$$;
alter function cp7_finance.access_now() owner to cp7_finance_read;
alter function cp7_finance.exact_numbers(jsonb) owner to cp7_finance_read;
alter function cp7_finance.workspace(jsonb) owner to cp7_finance_read;
grant create on schema public to cp7_finance_read;
alter function public.erp_cp7_get_finance_report_v1(jsonb) owner to cp7_finance_read;
revoke create on schema public from cp7_finance_read;
revoke all on function cp7_finance.access_now(),cp7_finance.exact_numbers(jsonb),cp7_finance.workspace(jsonb),public.erp_cp7_get_finance_report_v1(jsonb) from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_finance_report_v1(jsonb) to authenticated;
