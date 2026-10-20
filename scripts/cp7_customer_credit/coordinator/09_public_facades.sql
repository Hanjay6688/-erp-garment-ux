-- OUTSIDE PRODUCT. Root composes ONLY after all exact Native/copy/reader guards,
-- owning callbacks, role restoration and dependency verifiers are installed.
do $not_an_installer$begin raise exception 'OW04_COORDINATOR_REQUIRES_ATOMIC_NATIVE_COMPOSITION';end $not_an_installer$;

create function cp7_credit.initial_credit_account_eligible_v1(p_id uuid)returns boolean
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
begin
 perform cp7_credit.credit_account_facts_v1(p_id);return true;
exception when raise_exception then
 if sqlerrm in('CP7_CREDIT_LIABILITY_ACCOUNT_INELIGIBLE','CP7_CREDIT_UNTRACKED_LIABILITY_JOURNAL',
  'CP7_CREDIT_LIABILITY_CUSTOMER_MISSING','CP7_CREDIT_LIABILITY_RECONCILIATION_FAILED')then return false;end if;
 raise;
end $$;
create function cp7_credit.initial_cash_account_eligible_v1(p_id uuid)returns boolean
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
begin
 perform cp7_credit.cash_account_facts_v1(p_id);return true;
exception when raise_exception then
 if sqlerrm='CP7_CREDIT_REFUND_CASH_ACCOUNT_INELIGIBLE'then return false;end if;raise;
end $$;

create function cp7_credit.initial_account_options_v1(p_query jsonb)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare h erp.sales_headers;authority jsonb;kind text;off integer;search text;rows jsonb;n bigint;source jsonb;
begin
 if jsonb_typeof(p_query)is distinct from'object'or not p_query?&array['kind','sale_id','expected_version','review_token','account_kind','q','offset','limit']
  or p_query-array['kind','sale_id','expected_version','review_token','account_kind','q','offset','limit']<>'{}'::jsonb
  or p_query->>'kind'<>'ACCOUNT_OPTIONS'or p_query->>'account_kind'not in('CREDIT','CASH')
  or jsonb_typeof(p_query->'q')is distinct from'string'or length(p_query->>'q')>120
  or jsonb_typeof(p_query->'expected_version')is distinct from'string'or p_query->>'expected_version'!~'^[1-9][0-9]{0,18}$'
  or(p_query->>'expected_version')::numeric>9223372036854775807
  or jsonb_typeof(p_query->'review_token')is distinct from'string'or p_query->>'review_token'!~'^[0-9a-f]{32}$'
  or jsonb_typeof(p_query->'sale_id')is distinct from'string'or p_query->>'sale_id'!~*'^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$'
  or p_query->'limit'<>'25'::jsonb or jsonb_typeof(p_query->'offset')is distinct from'number'
  or p_query->>'offset'!~'^[0-9]{1,7}$'or(p_query->>'offset')::integer>1000000 then raise exception 'CP7_CREDIT_ACCOUNT_OPTIONS_FIELDS';end if;
 kind:=p_query->>'account_kind';off:=(p_query->>'offset')::integer;search:=btrim(p_query->>'q');
 authority:=cp7_credit.return_command_access(case when kind='CASH'then'REFUND'end);
 select *into strict h from erp.sales_headers where id=(p_query->>'sale_id')::uuid;
 if h.status not in('POSTED','PARTIAL_PAID','PAID')or h.row_version::text<>p_query->>'expected_version'
  or cp7_sales.review_token(h.id)is distinct from p_query->>'review_token'then raise exception 'CP7_SALES_REVIEW_CHANGED';end if;
 source:=jsonb_build_object('sale_id',h.id,'sale_number',h.sale_number,'customer_id',h.customer_id,
  'customer_name',(select customer_name from erp.customers where id=h.customer_id),'row_version',h.row_version::text,'review_token',p_query->'review_token');
 if kind='CREDIT'then
  with eligible as materialized(select a.*from erp.chart_accounts a where a.account_type='LIABILITY'and a.normal_balance='CREDIT'and a.is_active and a.is_postable
   and(search=''or strpos(lower(a.account_code||' '||a.account_name),lower(search))>0)and cp7_credit.initial_credit_account_eligible_v1(a.id)),
  sliced as(select *from eligible order by account_code,id limit 25 offset off)
  select(select count(*)from eligible),coalesce((select jsonb_agg(jsonb_build_object('id',a.id,'code',a.account_code,'name',a.account_name,
   'facts_sha256',ow04_source_proposal.sha(cp7_credit.credit_account_facts_v1(a.id)))order by a.account_code,a.id)from sliced a),'[]')into n,rows;
 else
  with eligible as materialized(select c.*from erp.cash_accounts c join erp.chart_accounts a on a.id=c.coa_account_id
   where c.is_active and a.is_active and a.is_postable and a.account_type='ASSET'
    and(search=''or strpos(lower(c.cash_account_code||' '||c.cash_account_name),lower(search))>0)and cp7_credit.initial_cash_account_eligible_v1(c.id)),
  sliced as(select *from eligible order by cash_account_code,id limit 25 offset off)
  select(select count(*)from eligible),coalesce((select jsonb_agg(jsonb_build_object('id',c.id,'code',c.cash_account_code,'name',c.cash_account_name,
   'facts_sha256',ow04_source_proposal.sha(cp7_credit.cash_account_facts_v1(c.id)))order by c.cash_account_code,c.id)from sliced c),'[]')into n,rows;
 end if;
 if cp7_credit.return_command_access(case when kind='CASH'then'REFUND'end)is distinct from authority then
  raise exception using errcode='42501',message='CP7_CREDIT_ACCOUNT_OPTIONS_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.sales-return-settlement-options.v1','kind','ACCOUNT_OPTIONS','read_only',true,'business_DML',false,
  'captured_at',statement_timestamp(),'source',source,'account_kind',kind,'q',p_query->'q','rows',rows,'total',n::text,'offset',off,'limit',25,
  'next_offset',case when off+jsonb_array_length(rows)<n then off+jsonb_array_length(rows)end);
end $$;

alter function cp7_credit.initial_credit_account_eligible_v1(uuid)owner to postgres;
alter function cp7_credit.initial_cash_account_eligible_v1(uuid)owner to postgres;
alter function cp7_credit.initial_account_options_v1(jsonb)owner to postgres;
revoke all on function cp7_credit.initial_credit_account_eligible_v1(uuid),cp7_credit.initial_cash_account_eligible_v1(uuid),
 cp7_credit.initial_account_options_v1(jsonb)from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write,cp7_credit_write;

-- Exactly the established sales read/write role split. Authentication and fine
-- owning permission checks run inside the private callbacks on every call and
-- after waits. authenticated gets only these two public entry points.
create function public.erp_cp7_get_sales_return_settlement_quote_v1(p_query jsonb)returns jsonb
language sql volatile security definer set search_path=''set TimeZone='UTC'as $$
 select cp7_credit.get_initial_return_quote_v1(p_query)
$$;
create function public.erp_cp7_settle_sales_return_v1(p_payload jsonb,p_request uuid,p_expected text)returns jsonb
language sql volatile security definer set search_path=''set TimeZone='UTC'as $$
 select cp7_credit.return_settlement_command(p_payload,p_request,p_expected)
$$;
grant usage on schema cp7_credit to cp7_sales_read;
grant execute on function cp7_credit.get_initial_return_quote_v1(jsonb)to cp7_sales_read;
grant create on schema public to cp7_sales_read,cp7_credit_write;
alter function public.erp_cp7_get_sales_return_settlement_quote_v1(jsonb)owner to cp7_sales_read;
alter function public.erp_cp7_settle_sales_return_v1(jsonb,uuid,text)owner to cp7_credit_write;
revoke create on schema public from cp7_sales_read,cp7_credit_write;
revoke all on function public.erp_cp7_get_sales_return_settlement_quote_v1(jsonb),public.erp_cp7_settle_sales_return_v1(jsonb,uuid,text)
 from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write;
grant execute on function public.erp_cp7_get_sales_return_settlement_quote_v1(jsonb),public.erp_cp7_settle_sales_return_v1(jsonb,uuid,text)to authenticated;
