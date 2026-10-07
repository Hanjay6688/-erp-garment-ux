-- Protected bridge to the accepted Native owner report. This is a reader, not
-- another money/HPP calculator. Financial operands never enter an Ops-only run.
-- These Native collections are sets of checks, not chronological events. The
-- accepted report sorts failed_checks by family/code only, leaving ties free to
-- exchange positions. Canonicalize only those collections for the dependency
-- hash; preserve every member, duplicate, field and the raw archived report.
create function cp7_analysis_native.financial_fingerprint(p_report jsonb,p_book text)returns text
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare body jsonb:=p_report-'captured_at';path text[];items jsonb;
begin
 for path in select column1 from(values
  (array['snapshot','data_confidence','failed_checks']),
  (array['snapshot','data_confidence','blockers']),
  (array['close_preflight','blockers']),(array['close_preflight','info']))paths loop
  if jsonb_typeof(body#>path)='array'then
   select coalesce(jsonb_agg(value order by value::text collate "C"),'[]'::jsonb)into items
    from jsonb_array_elements(body#>path);
   body:=jsonb_set(body,path,items,false);
  end if;
 end loop;
 return encode(pg_catalog.sha256(convert_to(jsonb_build_object('report',body,'book_signature',p_book)::text,'UTF8')),'hex');
end $$;

create function cp7_analysis_native.financial_source(q jsonb,p_at timestamptz)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare dates jsonb;report jsonb;signature text;book_signature text;
begin
 dates:=jsonb_build_object('from',q->>'from_date','to',q->>'through_date',
  'as_of',(p_at at time zone 'Asia/Jakarta')::date::text);
 report:=cp7_finance.workspace(dates||jsonb_build_object('offset',0,'limit',25,'filing_id',null));
 -- Preserve provenance even when a posted event and its inverse leave the
 -- same aggregate balances. Existing reader grants suffice; no new writer or
 -- direct Capture-role access to the financial tables is introduced.
 with parts as(
  select 'journal:'||j.id::text key,to_jsonb(j)fact from erp.journal_entries j where j.transaction_date<=(dates->>'as_of')::date
  union all select 'line:'||l.id::text,to_jsonb(l)from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.transaction_date<=(dates->>'as_of')::date
  union all select 'book:'||b.account_id::text||':'||b.balance_date::text,to_jsonb(b)from erp.account_daily_balances b where b.balance_date<=(dates->>'as_of')::date
  union all select 'cash:'||a.id::text,to_jsonb(a)from erp.cash_accounts a)
 select encode(pg_catalog.sha256(convert_to(coalesce(string_agg(key||':'||encode(pg_catalog.sha256(convert_to(fact::text,'UTF8')),'hex'),E'\n'order by key),''),'UTF8')),'hex')into book_signature from parts;
 -- A wall clock is provenance, not a changing financial fact. Keep the shared
 -- capture clock on the saved report. Every remaining Native fact participates
 -- in the hash, with unordered check collections compared as complete multisets.
 signature:=cp7_analysis_native.financial_fingerprint(report,book_signature);
 report:=jsonb_set(report,'{captured_at}',to_jsonb(p_at));
 return jsonb_build_object('contract_version','cp7.native-analysis-finance.v1',
  'dates',dates,'book_signature',book_signature,'source_hash',signature,'report',report);
end $$;
grant usage,create on schema cp7_analysis_native to cp7_finance_read;
alter function cp7_analysis_native.financial_fingerprint(jsonb,text)owner to cp7_finance_read;
alter function cp7_analysis_native.financial_source(jsonb,timestamptz)owner to cp7_finance_read;
revoke create on schema cp7_analysis_native from cp7_finance_read;
revoke all on function cp7_analysis_native.financial_fingerprint(jsonb,text)from public,anon,authenticated,service_role,cp7_capture;
revoke all on function cp7_analysis_native.financial_source(jsonb,timestamptz)from public,anon,authenticated,service_role;
grant execute on function cp7_analysis_native.financial_source(jsonb,timestamptz)to cp7_capture;

create function cp7_analysis_native.source(q jsonb)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare c jsonb;a jsonb;financial jsonb:=null;
begin
 c:=cp7_analysis_native.source();a:=erp.get_my_access_v1();
 if a->'allowed'='true'::jsonb and a->'profile'->>'role_code'in('OWNER','ADMIN')and erp.has_permission('finance.reports.view')then
  financial:=cp7_analysis_native.financial_source(q,(c->>'captured_at')::timestamptz);
 end if;
 return c||jsonb_build_object('financial_source',financial);
end $$;
alter function cp7_analysis_native.source(jsonb)owner to cp7_capture;
-- INCLUDED is the unchanged full source above. DEFERRED never calls the
-- protected owner report and never scans the books: the run carries no
-- financial source, exactly as an operations-only actor's run, plus the mark
-- that keeps every later read on the same operational-only source.
create function cp7_analysis_native.source_for(q jsonb,p_finance text)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
begin
 if p_finance='INCLUDED'then return cp7_analysis_native.source(q);end if;
 if p_finance is distinct from 'DEFERRED'then raise exception 'CP7_ANALYSIS_FINANCE_MODE';end if;
 return cp7_analysis_native.source()||jsonb_build_object('financial_source',null,'financial_capture','DEFERRED');
end $$;
alter function cp7_analysis_native.source_for(jsonb,text)owner to cp7_capture;

alter function cp7_analysis_native.build(jsonb,jsonb,uuid,jsonb)rename to build_operational;
-- The financial overlay of the operational analysis v (without semantic_hash).
-- finance_overlay adds the semantic hash; build and the staged job share both.
create function cp7_analysis_native.finance_apply(v jsonb,c jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare f jsonb:=c->'financial_source';s jsonb;confidence text;readiness text;refs jsonb;metrics jsonb:='[]';
 section text;k text;amount text;part jsonb;recorded boolean;basis text;period_from text;period_to text;
begin
 if f is not null and f<>'null'::jsonb then
  s:=f->'report'->'snapshot';confidence:=s->'data_confidence'->>'status';
  if confidence not in('READY','RECALC_PENDING','BLOCKED')or confidence is null then raise exception 'CP7_ANALYSIS_FINANCE_INCOMPLETE';end if;
  readiness:=case confidence when 'READY'then 'READY'when 'RECALC_PENDING'then 'LIMITED'else 'BLOCKED'end;
  refs:=jsonb_build_array(cp7_wip.ref('NATIVE_OWNER_FINANCIAL_REPORT',f->>'source_hash',f->>'source_hash'));
  for section,part in select key,value from jsonb_each(jsonb_build_object('performance',s->'performance','financial_position',s->'financial_position'))loop
   for k,amount in select key,value#>>'{}'from jsonb_each(part)where jsonb_typeof(value)='string'and key not in('gross_margin_pct','net_margin_pct')loop
    -- Signed GL recordings can be examined under a blocked book. A profit or
    -- inventory valuation cannot be presented as proved when HPP is incomplete.
    recorded:=section='performance'and k in('sales_revenue_gl','cogs_gl','other_income','operating_and_other_expense',
     'gross_sales_before_discount','line_discounts','posted_sales_returns','operational_net_sales','sales_revenue_bridge_delta')
     or section='financial_position'and k in('cash','customer_ar','supplier_final_ap','grni_estimated_liability');
    basis:=case section when 'performance'then s->'basis'->>'performance_lifecycle_basis'else 'RECORDED_GL_BALANCES_AS_OF'end;
    period_from:=case section when 'performance'then f->'dates'->>'from'else f->'dates'->>'as_of'end;
    period_to:=case section when 'performance'then f->'dates'->>'to'else f->'dates'->>'as_of'end;
    metrics:=metrics||jsonb_build_array(jsonb_build_object('metric_id','NATIVE_FINANCE:'||section||':'||k,
     'version','accepted-owner-report-1','value',cp7_analysis_native.fact(case when confidence='READY'or recorded then amount else null end,'IDR',refs),
     'formula_ref',basis||':'||k,'operands',jsonb_build_array(cp7_analysis_native.fact(amount,'IDR',refs)),
     'readiness',readiness,'scope_kind','GLOBAL','scope_key','OWNER_FINANCIAL_REPORT',
     'period_start',period_from,'period_end',period_to,'knowledge_mode','CURRENT'));
   end loop;
  end loop;
  v:=jsonb_set(v,'{metrics}',(v->'metrics')||metrics);
  v:=jsonb_set(v,'{financial_readiness}',to_jsonb(readiness));
  v:=jsonb_set(v,'{quality,financial}',to_jsonb(case when confidence='READY'then 'COMPLETE'else 'PARTIAL'end::text));
  v:=jsonb_set(v,'{snapshot,fact_count}',to_jsonb((v->'snapshot'->>'fact_count')::integer+1));
  v:=jsonb_set(v,'{dependencies}',(v->'dependencies')||jsonb_build_array(jsonb_build_object('domain','native_owner_financial_report',
   'revision',f->'source_hash','source_hash',f->'source_hash','fact_count',1,
   'completeness',case when confidence='READY'then 'COMPLETE'else 'PARTIAL'end)));
  v:=jsonb_set(v,'{generation_warnings}',(select coalesce(jsonb_agg(x),'[]')from jsonb_array_elements(v->'generation_warnings')x
   where x<>'"FINANCIAL_DOMAIN_NOT_CAPTURED"'::jsonb)||case when confidence='READY'then '[]'::jsonb else jsonb_build_array('NATIVE_FINANCIAL_READINESS:'||confidence)end);
 end if;
 return v;
end $$;
create function cp7_analysis_native.finance_overlay(v jsonb,c jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
begin
 v:=cp7_analysis_native.finance_apply(v,c);
 return v||jsonb_build_object('semantic_hash',encode(extensions.digest(convert_to(v::text,'UTF8'),'sha256'),'hex'));
end $$;
create function cp7_analysis_native.build(c jsonb,q jsonb,p_run uuid,a jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
begin
 return cp7_analysis_native.finance_overlay(cp7_analysis_native.build_operational(c,q,p_run,a)-'semantic_hash',c);
end $$;
alter function cp7_analysis_native.finance_apply(jsonb,jsonb)owner to cp7_capture;
alter function cp7_analysis_native.finance_overlay(jsonb,jsonb)owner to cp7_capture;
alter function cp7_analysis_native.build(jsonb,jsonb,uuid,jsonb)owner to cp7_capture;
revoke all on function cp7_analysis_native.source(jsonb),cp7_analysis_native.source_for(jsonb,text),cp7_analysis_native.finance_apply(jsonb,jsonb),cp7_analysis_native.finance_overlay(jsonb,jsonb),cp7_analysis_native.build(jsonb,jsonb,uuid,jsonb)from public,anon,authenticated,service_role;
