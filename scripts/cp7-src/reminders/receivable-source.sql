-- A current observation, separate from immutable original analysis and review.
-- Copy the accepted P11 receivables reader; never calculate another AR balance.
grant execute on function public.erp_cp7_get_sales_v1(jsonb)to cp7_reminder;
create function cp7_reminder_native.receivable_source()returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare native jsonb;pages jsonb:='[]';rows jsonb:='[]';conditions jsonb;total bigint;off integer:=0;
 next_off integer;at date:=(statement_timestamp()at time zone'Asia/Jakarta')::date;source_hash text;
begin
 if not erp.has_permission('finance.ar.view')then raise exception using errcode='42501',message='CP7_REMINDER_AR_ACCESS_DENIED';end if;
 loop
  native:=public.erp_cp7_get_sales_v1(jsonb_build_object('q','','status',null,'sale_id',null,'offset',off,'limit',25));
  if native->>'contract_version'<>'cp7.sales-workspace.v1'or native->'financial_captured'is distinct from'true'::jsonb
   or native->'read_only'is distinct from'true'::jsonb or jsonb_typeof(native->'page'->'rows')is distinct from'array'
   or native->'detail'is distinct from'null'::jsonb then raise exception 'CP7_REMINDER_AR_SOURCE_INCOMPLETE';end if;
  if off=0 then total:=(native->'page'->>'total')::bigint;end if;
  if total>5000 or total<0 or(native->'page'->>'total')::bigint<>total
   or(native->'page'->>'offset')::integer<>off or(native->'page'->>'limit')::integer<>25
   or jsonb_array_length(native->'page'->'rows')>25 then raise exception 'CP7_REMINDER_AR_SOURCE_INCOMPLETE';end if;
  pages:=pages||jsonb_build_array(native);rows:=rows||(native->'page'->'rows');
  next_off:=(native->'page'->>'next_offset')::integer;
  if next_off is null then exit;end if;
  if next_off<>off+jsonb_array_length(native->'page'->'rows')or next_off<=off or next_off>=total then raise exception 'CP7_REMINDER_AR_SOURCE_INCOMPLETE';end if;
  off:=next_off;
 end loop;
 if jsonb_array_length(rows)<>total or(select count(distinct x->>'id')from jsonb_array_elements(rows)x)<>total
  or octet_length(pages::text)>4000000 then raise exception 'CP7_REMINDER_AR_SOURCE_INCOMPLETE';end if;
 -- All pages run in this STABLE function's statement snapshot. Due dates are
 -- Native document dates; null remains unrecorded. Negative credit is a review
 -- condition, never an invented refund/carry policy or a zero balance.
 select coalesce(jsonb_agg(jsonb_build_object('key','AR:'||(x->>'id'),'source_id',x->>'id',
  'source_revision',x->>'row_version',
  'native_source_hash',encode(pg_catalog.sha256(convert_to(x::text,'UTF8')),'hex'),
  'state',case when x->'financial'->>'state'='DRAFT_PREVIEW'then'DRAFT_ONLY'
   when x->'financial'->>'state'<>'ACTIVE_RECEIVABLE'then'INACTIVE_DOCUMENT'
   when x->'financial'->>'open_balance'is null then'UNKNOWN_BALANCE'
   when(x->'financial'->>'open_balance')::numeric<0 then'CREDIT_REVIEW'
   when(x->'financial'->>'open_balance')::numeric=0 then'ZERO_BALANCE'
   when x->>'due_date'is null then'MISSING_DUE_DATE'
   when(x->>'due_date')::date<at then'OVERDUE'
   when(x->>'due_date')::date=at then'DUE_TODAY'else'NOT_DUE_YET'end,
  'business_resolved',coalesce(x->'financial'->>'state'='ACTIVE_RECEIVABLE'and(x->'financial'->>'open_balance')::numeric=0,false))
  order by n),'[]')into conditions from jsonb_array_elements(rows)with ordinality e(x,n);
 source_hash:=encode(pg_catalog.sha256(convert_to(jsonb_build_object('as_of',at,'rows',rows)::text,'UTF8')),'hex');
 return jsonb_build_object('contract_version','cp7.native-ar-source.v1','basis','ACCEPTED_P11_CURRENT_NATIVE_DOCUMENT',
  'as_of',at,'read_at',statement_timestamp(),'source_hash',source_hash,'pages',pages,'conditions',conditions,'page_complete',true,'total',total::text);
end $$;
create function cp7_reminder_native.receivable_conditions(p_run uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb:=cp7_reminder_native.access_now(p_run);source jsonb;
begin
 source:=cp7_reminder_native.receivable_source();
 if erp.get_my_access_v1()is distinct from a->'access'or not erp.has_permission('finance.ar.view')then
  raise exception using errcode='42501',message='CP7_REMINDER_AR_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.native-ar-conditions.v1','actor_scope_id',auth.uid(),
  'analysis',a->'analysis','source',source);
end $$;
alter function cp7_reminder_native.receivable_source()owner to cp7_reminder;
alter function cp7_reminder_native.receivable_conditions(uuid)owner to cp7_reminder;
revoke all on function cp7_reminder_native.receivable_source(),cp7_reminder_native.receivable_conditions(uuid)from public,anon,authenticated,service_role;
grant create on schema public to cp7_reminder;
create function public.erp_cp7_get_analysis_receivable_conditions_v1(p_run uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.receivable_conditions(p_run)$$;
alter function public.erp_cp7_get_analysis_receivable_conditions_v1(uuid)owner to cp7_reminder;
revoke create on schema public from cp7_reminder;
revoke all on function public.erp_cp7_get_analysis_receivable_conditions_v1(uuid)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_get_analysis_receivable_conditions_v1(uuid)to authenticated;
