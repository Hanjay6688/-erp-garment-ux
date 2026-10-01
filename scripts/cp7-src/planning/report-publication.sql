-- P15: immutable ERP publications of one currently authorized Native Original.
-- Rendering uses existing typed facts. It never recalculates stock, money or HPP.
create table cp7_analysis_native.publications(
 id uuid primary key default gen_random_uuid(),actor uuid not null,series_id uuid not null,
 revision bigint not null check(revision>0),run_id uuid not null references cp7_analysis_native.runs(id),
 kind text not null check(kind in('DAILY','PERIOD','EXCEPTIONS','ARCHIVE')),
 period_query jsonb not null,title text not null,reason text not null,
 template_version text not null,body text not null,body_sha256 text not null,
 source_hash text not null,semantic_hash text not null,
 published_at timestamptz not null default clock_timestamp(),request_id uuid not null,
 unique(actor,series_id,revision),unique(actor,request_id)
);
create table cp7_analysis_native.report_requests(
 actor uuid not null,request_id uuid not null,payload jsonb not null,
 publication_id uuid references cp7_analysis_native.publications(id),status text not null check(status in('COMMITTED','CLOSED_UNCOMMITTED')),
 primary key(actor,request_id),check((status='COMMITTED')=(publication_id is not null))
);
alter table cp7_analysis_native.publications owner to cp7_capture;
alter table cp7_analysis_native.report_requests owner to cp7_capture;
alter table cp7_analysis_native.publications enable row level security;
alter table cp7_analysis_native.report_requests enable row level security;
create policy cp7_report_no_access on cp7_analysis_native.publications for all to public using(false)with check(false);
create policy cp7_report_request_no_access on cp7_analysis_native.report_requests for all to public using(false)with check(false);
revoke all on cp7_analysis_native.publications,cp7_analysis_native.report_requests from public,anon,authenticated,service_role;
create trigger immutable_report_publication before update or delete on cp7_analysis_native.publications
 for each row execute function cp7_private.immutable_run();
create trigger immutable_report_request before update or delete on cp7_analysis_native.report_requests
 for each row execute function cp7_private.immutable_run();
create index cp7_report_actor_time on cp7_analysis_native.publications(actor,published_at desc,id desc);

create function cp7_analysis_native.report_fact(v jsonb)returns text
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select case when v->>'state'='UNKNOWN'then 'Belum diketahui ('||coalesce(v->>'reason','sumber belum terbukti')||')'
  else coalesce(v->>'value','Belum diketahui')||' '||coalesce(v->>'unit','')||
   case when v->>'state'='ASSUMED'then ' [asumsi]'else ''end end
$$;

create function cp7_analysis_native.report_render(e jsonb,p_kind text,p_title text)returns text
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare x jsonb:=e->'analysis';r jsonb;s jsonb;m jsonb;a jsonb;label jsonb;lines text[];name text;metric_label text;financial_labels jsonb:='{"sales_revenue_gl": "Pendapatan penjualan tercatat", "cogs_gl": "HPP penjualan tercatat", "gross_profit": "Laba kotor", "other_income": "Pendapatan lain tercatat", "operating_and_other_expense": "Beban tercatat", "net_profit": "Laba bersih", "gross_sales_before_discount": "Penjualan sebelum diskon", "line_discounts": "Diskon penjualan", "posted_sales_returns": "Retur penjualan tercatat", "operational_net_sales": "Penjualan bersih operasional", "sales_revenue_bridge_delta": "Selisih penjualan operasional dan jurnal", "assets": "Aset", "cash": "Saldo kas tercatat", "customer_ar": "Piutang pelanggan tercatat", "material_inventory": "Nilai persediaan bahan", "wip_inventory": "Nilai barang dalam proses", "fg_inventory": "Nilai persediaan barang jadi", "liabilities": "Kewajiban", "supplier_final_ap": "Utang pemasok final tercatat", "grni_estimated_liability": "Kewajiban penerimaan belum ditagih tercatat", "recorded_equity": "Ekuitas tercatat", "current_earnings": "Laba berjalan", "liabilities_plus_equity": "Kewajiban dan ekuitas", "balance_difference": "Selisih neraca"}'::jsonb;
begin
 lines:=array[p_title,case p_kind when'DAILY'then'BRIEFING HARIAN'when'PERIOD'then'REVIEW PERIODE'
  when'EXCEPTIONS'then'ANALISIS DAN PENGECUALIAN'else'ARSIP LAPORAN'end,
  'Periode riwayat: '||(e->'query'->>'from_date')||' sampai '||(e->'query'->>'through_date')||
   '; pengelompokan '||(e->'query'->>'group_mode')||'.',
  'Fakta per '||to_char((x->'snapshot'->>'effective_as_of')::timestamptz at time zone'Asia/Jakarta','YYYY-MM-DD HH24:MI:SS')||
   ' WIB; diketahui '||to_char((x->'snapshot'->>'known_as_of')::timestamptz at time zone'Asia/Jakarta','YYYY-MM-DD HH24:MI:SS')||' WIB.',
  'Kesiapan keuangan: '||(x->>'financial_readiness')||'; analisis '||(e->>'run_id')||'.',
  'KONDISI PRODUK DAN SIZE'];
 for r in select value from jsonb_array_elements(x->'recommendations')order by value->'target'->>'key'loop
  label:=(select value from jsonb_array_elements(e->'product_labels')where value->>'target_key'=r->'target'->>'key');
  name:=coalesce(label->>'sku',r->'target'->>'key')||' · '||coalesce(label->>'product_name','')||
   ' · size '||(r->'target'->>'size_id');
  lines:=array_append(lines,name||' · '||case r->>'production_state'when'ACTIVE'then'Aktif'when'PAUSED'then'Ditunda'else'Dihentikan'end||': FG '||cp7_analysis_native.report_fact(r->'actual_fg')||
   '; target '||cp7_analysis_native.report_fact(r->'target_qty')||'; gap dasar '||cp7_analysis_native.report_fact(r->'q_base')||
   '; gap bersyarat '||cp7_analysis_native.report_fact(r->'q_conditional')||
   '; produksi baru layak '||cp7_analysis_native.report_fact(r->'feasible_new')||
   '; belum tertutup '||cp7_analysis_native.report_fact(r->'unresolved_qty')||'.');
  lines:=array_append(lines,'Identitas produk, size dan membership: '||(r->'target')::text||
   '; referensi gap '||(r->'q_base'->'refs')::text||'; alokasi bersyarat '||(r->'q_conditional'->'refs')::text||'.');
 end loop;
 lines:=array_append(lines,'TINDAKAN DAN ALASAN');
 for a in select value from jsonb_array_elements(x->'actions')
  order by(value->'display_priority'->>'rank')::numeric nulls first,value->>'key'loop
  lines:=array_append(lines,(a->>'intent')||' · '||(a->>'key')||': '||
   (select string_agg(value,'; 'order by ord)from jsonb_array_elements_text(a->'display_priority'->'basis')with ordinality b(value,ord))||
   '; alasan '||(a->>'primary_reason')||'; sumber '||(a->'source_links')::text||'.');
 end loop;
 lines:=array_append(lines,'STOK PROSES, BAHAN DAN KAPASITAS');
 for s in select value from jsonb_array_elements(x->'sources')order by value->>'source_key'loop
  lines:=array_append(lines,(s->>'source_key')||': fisik '||cp7_analysis_native.report_fact(s->'physical_remaining')||
   '; proyeksi '||cp7_analysis_native.report_fact(s->'eligible_projected')||'; dibagi '||cp7_analysis_native.report_fact(s->'allocated')||
   '; siap '||coalesce(s->>'eta','Belum diketahui')||' ('||(s->>'eta_basis')||').');
 end loop;
 for m in select value from jsonb_array_elements(x->'material_needs')order by value->>'target_key',value->>'material_key'loop
  lines:=array_append(lines,(m->>'target_key')||' · bahan '||coalesce(m->>'material_key','belum tertaut')||
   ': kebutuhan '||cp7_analysis_native.report_fact(m->'gross')||'; terpasang terbukti '||cp7_analysis_native.report_fact(m->'installed_proven')||
   '; sisa layak teralokasi '||cp7_analysis_native.report_fact(m->'unused_allocated_proven')||
   '; tambahan eksternal '||cp7_analysis_native.report_fact(m->'additional_external')||'. '||(m->>'reason'));
 end loop;
 lines:=array_append(lines,'Issue bukan bukti pemasangan. Barang proses tetap terpisah dari stok jadi. Kelayakan yang belum terbukti tidak mengizinkan produksi baru.');
 lines:=array_append(lines,'ANGKA, PERIODE DAN SUMBER');
 for m in select value from jsonb_array_elements(x->'metrics')order by value->>'metric_id',value->>'scope_key'loop
  metric_label:=case when m->>'metric_id'like'NATIVE_FINANCE:%'then coalesce(financial_labels->>split_part(m->>'metric_id',':',3),m->>'metric_id')when m->>'metric_id'like'AVAILABLE_FG_PCS:%'then'Stok jadi tersedia'else m->>'metric_id'end;
  lines:=array_append(lines,metric_label||' · '||(m->>'scope_key')||': '||cp7_analysis_native.report_fact(m->'value')||
   '; periode '||(m->>'period_start')||' sampai '||(m->>'period_end')||'; kesiapan '||(m->>'readiness')||
   '; pengetahuan '||(m->>'knowledge_mode')||'; sumber '||(m->'value'->'refs')::text||'.');
  lines:=array_append(lines,'Definisi metrik '||(m->>'version')||'; rumus '||(m->>'formula_ref')||
   '; operand '||(m->'operands')::text||'.');
 end loop;
 if coalesce(e->'financial_source','null')='null'::jsonb then
  lines:=array_append(lines,'Keuangan dan HPP tidak tercakup dalam izin/sumber analisis ini. Tidak ada angka pengganti.');
 else
  lines:=array_append(lines,'Angka keuangan berasal dari laporan Native ERP, memakai catatan yang diketahui sekarang. Laba dan penilaian yang belum siap tetap belum diketahui.');
  for r in select value from jsonb_array_elements(e->'financial_source'->'report'->'snapshot'->'data_confidence'->'blockers')loop
   lines:=array_append(lines,'PENGHALANG KEUANGAN: '||(r->>'reason')||'; cakupan '||(r->>'scope')||
    '; tanggal '||coalesce(r->>'impact_date','keadaan sekarang')||'; sumber '||(r->'reference')::text||'.');
  end loop;
 end if;
 lines:=array_append(lines,'ASUMSI DAN DATA YANG MASIH KURANG');
 for a in select value from jsonb_array_elements(x->'assumptions')order by value->>'id'loop
  lines:=array_append(lines,(a->>'id')||': '||(a->>'label')||'; '||
   case when a->'confirmed_for_operation'='true'::jsonb then'dikonfirmasi untuk operasi'else'belum dikonfirmasi untuk operasi'end||'.');
 end loop;
 for s in select value from jsonb_array_elements(x->'generation_warnings')loop lines:=array_append(lines,'PERLU DIPERIKSA: '||(s#>>'{}'));end loop;
 lines:=array_append(lines,'Sumber '||(x->'snapshot'->>'source_hash')||'; hasil '||(x->>'semantic_hash')||
  '; template native-report-1. Laporan ini tidak memposting transaksi atau menerapkan produksi.');
 return array_to_string(lines,E'\n\n');
end $$;

create function cp7_analysis_native.report_document(p_id uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;r cp7_analysis_native.publications%rowtype;e jsonb;
begin
 a:=cp7_schedule_native.access_now(false);
 select *into r from cp7_analysis_native.publications where id=p_id and actor=(a->>'actor')::uuid;
 if r.id is null then raise exception using errcode='42501',message='CP7_REPORT_UNAVAILABLE';end if;
 e:=cp7_analysis_native.serve(r.run_id);
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_REPORT_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.report-publication.v1','actor_scope_id',r.actor,
  'id',r.id,'series_id',r.series_id,'revision',r.revision::text,'run_id',r.run_id,'request_id',r.request_id,
  'kind',r.kind,'period_query',r.period_query,'title',r.title,'reason',r.reason,'template_version',r.template_version,
  'body',r.body,'body_sha256',r.body_sha256,'source_hash',r.source_hash,'semantic_hash',r.semantic_hash,
  'published_at',r.published_at,'is_latest',r.revision=(select max(revision)from cp7_analysis_native.publications where actor=r.actor and series_id=r.series_id),
  'source_state',e->'source_state','analysis',e,'production_go',false);
end $$;

create function cp7_analysis_native.report_command(p jsonb,p_request uuid,p_lookup boolean)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;e jsonb;old cp7_analysis_native.report_requests%rowtype;r cp7_analysis_native.publications%rowtype;
 prior cp7_analysis_native.publications%rowtype;series uuid;revision bigint;body text;
begin
 a:=cp7_schedule_native.access_now(false);
 perform cp7_wip.fields(p,array['run_id','source_hash','semantic_hash','kind','series_id','expected_revision','title','reason','explicit_review']);
 if p_request is null or jsonb_typeof(p->'run_id')<>'string'or jsonb_typeof(p->'kind')<>'string'
  or p->>'run_id'!~'^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
  or p->>'kind'not in('DAILY','PERIOD','EXCEPTIONS','ARCHIVE')or p->'explicit_review'is distinct from'true'::jsonb
  or jsonb_typeof(p->'source_hash')<>'string'or p->>'source_hash'!~'^[0-9a-f]{64}$'
  or jsonb_typeof(p->'semantic_hash')<>'string'or p->>'semantic_hash'!~'^[0-9a-f]{64}$'
  or jsonb_typeof(p->'title')<>'string'or length(btrim(p->>'title'))not between 1 and 200
  or jsonb_typeof(p->'reason')<>'string'or length(btrim(p->>'reason'))not between 1 and 1000
  or jsonb_typeof(p->'series_id')not in('null','string')then raise exception 'CP7_REPORT_REVIEW';end if;
 if p->'series_id'='null'::jsonb then
  if p->'expected_revision'<>'null'::jsonb then raise exception 'CP7_REPORT_REVISION';end if;
 else
  if p->>'series_id'!~'^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
   or jsonb_typeof(p->'expected_revision')<>'string'or p->>'expected_revision'!~'^[1-9][0-9]{0,18}$'then raise exception 'CP7_REPORT_REVISION';end if;
  if(p->>'expected_revision')::numeric>9223372036854775807 then raise exception 'CP7_REPORT_REVISION';end if;
 end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:REPORT_REQUEST:'||(a->>'actor')||':'||p_request::text,0));
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_REPORT_ACCESS_CHANGED';end if;
 e:=cp7_analysis_native.serve((p->>'run_id')::uuid);
 if p->>'source_hash'<>e->'analysis'->'snapshot'->>'source_hash'or p->>'semantic_hash'<>e->'analysis'->>'semantic_hash'then raise exception 'CP7_REPORT_ORIGINAL_CHANGED';end if;
 select *into old from cp7_analysis_native.report_requests where actor=(a->>'actor')::uuid and request_id=p_request;
 if found then
  if old.payload<>p then raise exception 'CP7_REPORT_REQUEST_CHANGED';end if;
  return jsonb_build_object('contract_version','cp7.report-command.v1','request_id',p_request,'status',old.status,
   'document',case when old.publication_id is not null then cp7_analysis_native.report_document(old.publication_id)else null end,'analysis',e,'production_go',false);
 end if;
 if p_lookup then
  insert into cp7_analysis_native.report_requests(actor,request_id,payload,status)values((a->>'actor')::uuid,p_request,p,'CLOSED_UNCOMMITTED');
  return jsonb_build_object('contract_version','cp7.report-command.v1','request_id',p_request,'status','CLOSED_UNCOMMITTED','document',null,'analysis',e,'production_go',false);
 end if;
 if e->>'source_state'<>'UNCHANGED'then raise exception using errcode='40001',message='CP7_REPORT_SOURCE_CHANGED';end if;
 if p->'series_id'='null'::jsonb then series:=gen_random_uuid();revision:=1;
 else
  series:=(p->>'series_id')::uuid;
  perform pg_advisory_xact_lock(hashtextextended('CP7:REPORT_SERIES:'||(a->>'actor')||':'||series::text,0));
  if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_REPORT_ACCESS_CHANGED';end if;
  e:=cp7_analysis_native.serve((p->>'run_id')::uuid);
  if e->>'source_state'<>'UNCHANGED'then raise exception using errcode='40001',message='CP7_REPORT_SOURCE_CHANGED';end if;
  select *into prior from cp7_analysis_native.publications where actor=(a->>'actor')::uuid and series_id=series order by revision desc limit 1;
  if prior.id is null or prior.revision::text<>p->>'expected_revision'then raise exception using errcode='40001',message='CP7_REPORT_REVISION_CHANGED';end if;
  if prior.kind<>p->>'kind'or prior.period_query<>e->'query'then raise exception 'CP7_REPORT_SERIES_SCOPE_CHANGED';end if;
  -- Protected earlier content is never exposed by a revision after rights loss.
  perform cp7_analysis_native.serve(prior.run_id);revision:=prior.revision+1;
 end if;
 body:=cp7_analysis_native.report_render(e,p->>'kind',btrim(p->>'title'));
 if octet_length(body)>8000000 then raise exception 'CP7_REPORT_BODY_TOO_LARGE';end if;
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_REPORT_ACCESS_CHANGED';end if;
 insert into cp7_analysis_native.publications(actor,series_id,revision,run_id,kind,period_query,title,reason,template_version,body,body_sha256,source_hash,semantic_hash,request_id)
 values((a->>'actor')::uuid,series,revision,(e->>'run_id')::uuid,p->>'kind',e->'query',btrim(p->>'title'),btrim(p->>'reason'),
  'native-report-1',body,encode(pg_catalog.sha256(convert_to(body,'UTF8')),'hex'),p->>'source_hash',p->>'semantic_hash',p_request)returning *into r;
 insert into cp7_analysis_native.report_requests(actor,request_id,payload,publication_id,status)values(r.actor,p_request,p,r.id,'COMMITTED');
 return jsonb_build_object('contract_version','cp7.report-command.v1','request_id',p_request,'status','COMMITTED','document',cp7_analysis_native.report_document(r.id),'analysis',e,'production_go',false);
end $$;

create function cp7_analysis_native.report_index(p jsonb)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;report_access boolean;preflight_access boolean;cursor uuid;at timestamptz;n integer;rows jsonb;total bigint;remaining bigint;next_id text;
begin
 a:=cp7_schedule_native.access_now(false);perform cp7_wip.fields(p,array['before_id','limit']);
 if jsonb_typeof(p->'before_id')not in('string','null')or jsonb_typeof(p->'limit')<>'number'or p->>'limit'!~'^[1-9][0-9]?$'then raise exception 'CP7_REPORT_INDEX_QUERY';end if;
 n:=(p->>'limit')::integer;if n>50 then raise exception 'CP7_REPORT_INDEX_QUERY';end if;cursor:=(p->>'before_id')::uuid;
 report_access:=coalesce(a->'profile'->>'role_code'in('OWNER','ADMIN')and erp.has_permission('finance.reports.view'),false);
 preflight_access:=report_access and erp.has_permission('finance.period_close.manage');
 if cursor is not null then
  select pub.published_at into at from cp7_analysis_native.publications pub join cp7_analysis_native.runs r on r.id=pub.run_id
   where pub.actor=(a->>'actor')::uuid and pub.id=cursor
    and(coalesce(r.facts->'financial_source','null')='null'::jsonb or report_access)
    and(coalesce(r.facts->'financial_source'->'report'->'close_preflight','null')='null'::jsonb or preflight_access);
  if not found then raise exception using errcode='42501',message='CP7_REPORT_INDEX_CURSOR_UNAVAILABLE';end if;
 end if;
 with visible as materialized(
  select pub.*from cp7_analysis_native.publications pub join cp7_analysis_native.runs r on r.id=pub.run_id
   where pub.actor=(a->>'actor')::uuid
    and(coalesce(r.facts->'financial_source','null')='null'::jsonb or report_access)
    and(coalesce(r.facts->'financial_source'->'report'->'close_preflight','null')='null'::jsonb or preflight_access)),
 eligible as materialized(select *from visible where cursor is null or(published_at,id)<(at,cursor)),
 page as materialized(select *from eligible order by published_at desc,id desc limit n)
 select coalesce((select jsonb_agg(jsonb_build_object('id',id,'series_id',series_id,'revision',revision::text,'run_id',run_id,
  'kind',kind,'title',title,'period_query',period_query,'published_at',published_at,'body_sha256',body_sha256)
  order by published_at desc,id desc)from page),'[]'),(select count(*)from visible),(select count(*)from eligible),
  (select id::text from page order by published_at,id limit 1)into rows,total,remaining,next_id;
 if cp7_schedule_native.access_now(false)is distinct from a or report_access is distinct from
  coalesce(a->'profile'->>'role_code'in('OWNER','ADMIN')and erp.has_permission('finance.reports.view'),false)
  or preflight_access is distinct from(report_access and erp.has_permission('finance.period_close.manage'))then raise exception using errcode='42501',message='CP7_REPORT_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.report-index.v1','actor_scope_id',a->>'actor','rows',rows,'total',total::text,
  'next_before_id',case when remaining>n then next_id else null end,'page_complete',true,'production_go',false);
end $$;

create function cp7_analysis_native.report_compare(p_before uuid,p_after uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;left_doc jsonb;right_doc jsonb;l jsonb;r jsonb;m jsonb;rows jsonb:='[]';difference jsonb;engine_left text;engine_right text;
begin
 a:=cp7_schedule_native.access_now(false);left_doc:=cp7_analysis_native.report_document(p_before);right_doc:=cp7_analysis_native.report_document(p_after);
 select facts->>'analysis_engine_signature'into engine_left from cp7_analysis_native.runs where id=(left_doc->>'run_id')::uuid;
 select facts->>'analysis_engine_signature'into engine_right from cp7_analysis_native.runs where id=(right_doc->>'run_id')::uuid;
 for m in select value from(
  select value from jsonb_array_elements(right_doc->'analysis'->'analysis'->'metrics')
  union
  select value from jsonb_array_elements(left_doc->'analysis'->'analysis'->'metrics')l
   where not exists(select 1 from jsonb_array_elements(right_doc->'analysis'->'analysis'->'metrics')r
    where r.value->>'metric_id'=l.value->>'metric_id'and r.value->>'version'=l.value->>'version'
     and r.value->>'scope_kind'=l.value->>'scope_kind'and r.value->>'scope_key'=l.value->>'scope_key'
     and r.value->>'knowledge_mode'=l.value->>'knowledge_mode'and r.value->'value'->>'unit'=l.value->'value'->>'unit'))all_metrics
  order by value->>'metric_id',value->>'version',value->>'scope_kind',value->>'scope_key',value->>'knowledge_mode',value->'value'->>'unit'loop
  l:=(select value from jsonb_array_elements(left_doc->'analysis'->'analysis'->'metrics')
   where value->>'metric_id'=m->>'metric_id'and value->>'version'=m->>'version'
    and value->>'scope_kind'=m->>'scope_kind'and value->>'scope_key'=m->>'scope_key'
    and value->>'knowledge_mode'=m->>'knowledge_mode'and value->'value'->>'unit'=m->'value'->>'unit');
  r:=(select value from jsonb_array_elements(right_doc->'analysis'->'analysis'->'metrics')
   where value->>'metric_id'=m->>'metric_id'and value->>'version'=m->>'version'
    and value->>'scope_kind'=m->>'scope_kind'and value->>'scope_key'=m->>'scope_key'
    and value->>'knowledge_mode'=m->>'knowledge_mode'and value->'value'->>'unit'=m->'value'->>'unit');
  difference:=jsonb_build_object('state','UNKNOWN','unit',m->'value'->'unit','reason',case when engine_left is distinct from engine_right
   then'ENGINE_VERSIONS_NOT_COMPARABLE'when l is null or r is null then'METRIC_SCOPE_NOT_COMPARABLE'else'ONE_OR_BOTH_VALUES_UNKNOWN'end);
  if l is not null and r is not null and engine_left=engine_right and l->'value'->>'state'in('KNOWN','ASSUMED')and r->'value'->>'state'in('KNOWN','ASSUMED')then
   difference:=jsonb_build_object('state',case when l->'value'->>'state'='ASSUMED'or r->'value'->>'state'='ASSUMED'then'ASSUMED'else'KNOWN'end,
    'unit',r->'value'->'unit','value',((r->'value'->>'value')::numeric-(l->'value'->>'value')::numeric)::text);
  end if;
  rows:=rows||jsonb_build_array(jsonb_build_object('metric_id',m->>'metric_id','version',m->>'version','scope_kind',m->>'scope_kind',
   'scope_key',m->>'scope_key','knowledge_mode',m->>'knowledge_mode','before',l,'after',r,'difference',difference));
 end loop;
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_REPORT_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.report-comparison.v1','actor_scope_id',a->>'actor','before',left_doc,'after',right_doc,
  'rows',rows,'comparison_basis','AFTER_MINUS_BEFORE_NATIVE_METRICS_MATCHED_VERSION_SCOPE_UNIT_KNOWLEDGE','production_go',false);
end $$;

alter function cp7_analysis_native.report_fact(jsonb)owner to cp7_capture;
alter function cp7_analysis_native.report_render(jsonb,text,text)owner to cp7_capture;
alter function cp7_analysis_native.report_document(uuid)owner to cp7_capture;
alter function cp7_analysis_native.report_command(jsonb,uuid,boolean)owner to cp7_capture;
alter function cp7_analysis_native.report_index(jsonb)owner to cp7_capture;
alter function cp7_analysis_native.report_compare(uuid,uuid)owner to cp7_capture;
revoke all on function cp7_analysis_native.report_fact(jsonb),cp7_analysis_native.report_render(jsonb,text,text),
 cp7_analysis_native.report_document(uuid),cp7_analysis_native.report_command(jsonb,uuid,boolean),
 cp7_analysis_native.report_index(jsonb),cp7_analysis_native.report_compare(uuid,uuid)from public,anon,authenticated,service_role;
create function public.erp_cp7_publish_report_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_analysis_native.report_command(p_payload,p_request,false)$$;
create function public.erp_cp7_get_report_request_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_analysis_native.report_command(p_payload,p_request,true)$$;
create function public.erp_cp7_read_report_v1(p_id uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_analysis_native.report_document(p_id)$$;
create function public.erp_cp7_list_reports_v1(p_query jsonb)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_analysis_native.report_index(p_query)$$;
create function public.erp_cp7_compare_reports_v1(p_before uuid,p_after uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_analysis_native.report_compare(p_before,p_after)$$;
grant create on schema public to cp7_capture;
alter function public.erp_cp7_publish_report_v1(jsonb,uuid)owner to cp7_capture;
alter function public.erp_cp7_get_report_request_v1(jsonb,uuid)owner to cp7_capture;
alter function public.erp_cp7_read_report_v1(uuid)owner to cp7_capture;
alter function public.erp_cp7_list_reports_v1(jsonb)owner to cp7_capture;
alter function public.erp_cp7_compare_reports_v1(uuid,uuid)owner to cp7_capture;
revoke create on schema public from cp7_capture;
revoke all on function public.erp_cp7_publish_report_v1(jsonb,uuid),public.erp_cp7_get_report_request_v1(jsonb,uuid),
 public.erp_cp7_read_report_v1(uuid),public.erp_cp7_list_reports_v1(jsonb),public.erp_cp7_compare_reports_v1(uuid,uuid)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_publish_report_v1(jsonb,uuid),public.erp_cp7_get_report_request_v1(jsonb,uuid),
 public.erp_cp7_read_report_v1(uuid),public.erp_cp7_list_reports_v1(jsonb),public.erp_cp7_compare_reports_v1(uuid,uuid)to authenticated;
