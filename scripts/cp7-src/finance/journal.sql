-- Complete posted journal source. Read-only, with current native authority.
create role cp7_journal_read nologin noinherit nosuperuser nocreatedb nocreaterole noreplication bypassrls;
create schema cp7_journal authorization cp7_journal_read;
revoke all on schema cp7_journal from public,anon,authenticated,service_role,cp7_capture;
grant usage on schema erp,auth to cp7_journal_read;
grant execute on function auth.uid(),auth.jwt(),erp.get_my_access_v1(),erp.has_permission(text) to cp7_journal_read;
grant select on erp.journal_entries,erp.journal_lines,erp.chart_accounts to cp7_journal_read;

create function cp7_journal.access_now() returns void
language plpgsql stable security invoker set search_path='' as $$
declare a jsonb;
begin
 if auth.uid() is null or coalesce(auth.jwt()->>'role','')<>'authenticated' then raise exception using errcode='42501',message='CP7_JOURNAL_ACCESS_DENIED';end if;
 a:=erp.get_my_access_v1();
 if a->'allowed' is distinct from 'true'::jsonb or not erp.has_permission('finance.journal.view') then raise exception using errcode='42501',message='CP7_JOURNAL_ACCESS_DENIED';end if;
 if coalesce(a->'profile'->>'role_code','') not in('OWNER','ADMIN') then raise exception using errcode='42501',message='CP7_JOURNAL_OWNER_ADMIN_REQUIRED';end if;
end $$;

create function cp7_journal.header(h erp.journal_entries) returns jsonb
language sql stable security invoker set search_path='' as $$
 select jsonb_build_object('id',h.id,'number',h.journal_number,'source_type',h.source_type,'source_id',h.source_id,
  'status',h.status,'reversal_of_id',h.reversal_of_id,'description',h.description,'economic_date',h.economic_date,
  'transaction_date',h.transaction_date,'posting_at',h.posting_at,'period_shifted',h.period_shifted,
  'line_count',count(l.id)::text,'debit',coalesce(sum(l.debit),0)::text,'credit',coalesce(sum(l.credit),0)::text,
  'balanced',count(l.id)>0 and coalesce(sum(l.debit),0)=coalesce(sum(l.credit),0))
 from erp.journal_lines l where l.journal_entry_id=h.id
$$;

create function cp7_journal.workspace(p_query jsonb) returns jsonb
language plpgsql stable security invoker set search_path='' set TimeZone='UTC' as $$
declare f date;t date;q text;chosen uuid;off integer;n integer;total bigint;rows jsonb;detail jsonb:=null;
 h erp.journal_entries;lines jsonb;debits numeric;credits numeric;line_count bigint;unbalanced bigint;
begin
 perform cp7_journal.access_now();
 if jsonb_typeof(p_query) is distinct from 'object' or not p_query ?& array['from','to']
  or exists(select 1 from jsonb_object_keys(p_query)k where k not in('from','to','q','journal_id','offset','limit'))
  or exists(select 1 from jsonb_each(p_query)e where e.key in('from','to') and(jsonb_typeof(e.value)<>'string' or(e.value#>>'{}')!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$'))
  or exists(select 1 from jsonb_each(p_query)e where e.key in('q','journal_id') and jsonb_typeof(e.value) not in('string','null'))
  or exists(select 1 from jsonb_each(p_query)e where e.key in('offset','limit') and(jsonb_typeof(e.value)<>'number' or e.value::text!~'^[0-9]{1,7}$')) then raise exception 'CP7_JOURNAL_QUERY';end if;
 begin f:=(p_query->>'from')::date;t:=(p_query->>'to')::date;chosen:=(p_query->>'journal_id')::uuid;
 exception when invalid_text_representation or datetime_field_overflow then raise exception 'CP7_JOURNAL_QUERY';end;
 q:=btrim(coalesce(p_query->>'q',''));off:=coalesce((p_query->>'offset')::integer,0);n:=coalesce((p_query->>'limit')::integer,25);
 if f is null or t is null or f>t or t>(statement_timestamp() at time zone 'Asia/Jakarta')::date or length(q)>120 or off not between 0 and 1000000 or n not between 1 and 25 then raise exception 'CP7_JOURNAL_QUERY';end if;
 -- Full filtered totals and both source/detail reads share one stable snapshot.
 -- Reversed originals remain at their accounting date alongside linked inverses.
 with sources as(
  select j.id,count(l.id) native_line_count,coalesce(sum(l.debit),0) d,coalesce(sum(l.credit),0) c
  from erp.journal_entries j left join erp.journal_lines l on l.journal_entry_id=j.id
  where j.status in('POSTED','REVERSED') and j.transaction_date between f and t
   and(q='' or strpos(lower(concat_ws(' ',j.journal_number,j.source_type,j.description)),lower(q))>0)
  group by j.id
 ) select count(*),coalesce(sum(s.native_line_count),0),coalesce(sum(s.d),0),coalesce(sum(s.c),0),count(*)filter(where s.native_line_count=0 or s.d<>s.c)
 into total,line_count,debits,credits,unbalanced from sources s;
 select coalesce(jsonb_agg(cp7_journal.header(x) order by x.transaction_date,x.posting_at,x.id),'[]') into rows
 from(select j.* from erp.journal_entries j where j.status in('POSTED','REVERSED') and j.transaction_date between f and t
  and(q='' or strpos(lower(concat_ws(' ',j.journal_number,j.source_type,j.description)),lower(q))>0)
  order by j.transaction_date,j.posting_at,j.id limit n offset off)x;
 if chosen is not null then
  select * into h from erp.journal_entries where id=chosen and status in('POSTED','REVERSED') and transaction_date between f and t;
  if h.id is null then raise exception 'CP7_JOURNAL_SOURCE_NOT_IN_PERIOD';end if;
  if(select count(*) from erp.journal_lines where journal_entry_id=h.id)>250 then raise exception 'CP7_JOURNAL_DETAIL_TOO_LARGE';end if;
  select coalesce(jsonb_agg(jsonb_build_object('id',l.id,'account_id',l.account_id,'account_code',a.account_code,
   'account_name',a.account_name,'description',l.description,'debit',l.debit::text,'credit',l.credit::text,
   'customer_id',l.customer_id,'vendor_id',l.vendor_id,'contractor_id',l.contractor_id,'po_id',l.po_id,'product_id',l.product_id) order by l.id),'[]')
  into lines from erp.journal_lines l join erp.chart_accounts a on a.id=l.account_id where l.journal_entry_id=h.id;
  if jsonb_array_length(lines)<>(select count(*) from erp.journal_lines where journal_entry_id=h.id) then raise exception 'CP7_JOURNAL_DETAIL_INCOMPLETE';end if;
  detail:=cp7_journal.header(h)||jsonb_build_object('lines',lines);
 end if;
 return jsonb_build_object('contract_version','cp7.journal-read.v1','captured_at',statement_timestamp(),
  'knowledge_basis','CURRENT_RECORDED_KNOWLEDGE','historical_knowledge','NOT_RECONSTRUCTED',
  'basis',jsonb_build_object('from',f,'to',t,'q',q,'scope','POSTED_AND_REVERSED_JOURNALS_BY_ACCOUNTING_DATE'),
  'totals',jsonb_build_object('journal_count',total::text,'line_count',line_count::text,'debit',debits::text,'credit',credits::text,'unbalanced_journal_count',unbalanced::text),
  'page',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',n,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows)else null end),
  'detail',detail);
end $$;
create function public.erp_cp7_get_journal_book_v1(p_query jsonb) returns jsonb
language sql stable security definer set search_path='' as $$select cp7_journal.workspace(p_query)$$;
alter function cp7_journal.access_now() owner to cp7_journal_read;
alter function cp7_journal.header(erp.journal_entries) owner to cp7_journal_read;
alter function cp7_journal.workspace(jsonb) owner to cp7_journal_read;
grant create on schema public to cp7_journal_read;
alter function public.erp_cp7_get_journal_book_v1(jsonb) owner to cp7_journal_read;
revoke create on schema public from cp7_journal_read;
revoke all on all functions in schema cp7_journal from public,anon,authenticated,service_role,cp7_capture;
revoke all on function public.erp_cp7_get_journal_book_v1(jsonb) from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_journal_book_v1(jsonb) to authenticated;
