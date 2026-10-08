-- Business Report v2 (owner decision 8 Oct 2026; docs/cp7/p19/P19_STAGED_SNAPSHOT_V2.md §4).
-- A published report of ONE staged run of the actor (up to 5,000 targets),
-- built in steps under the unchanged statement limit and sealed once. The
-- analysis part is the run's immutable snapshot, always labelled with its
-- time ("Data analisis per ...") and never called current; the freshness at
-- publication (changes recorded since the snapshot) is part of the report.
-- Actual numbers come from the authoritative sources at the report date:
-- finished-goods stock from the stock movements at the actuals read, finance
-- and HPP from the Native owner report for that date (only when chosen and
-- permitted). Nothing here changes a run, posts a transaction or applies
-- production. The v1 report path (report-publication.sql) is unchanged.
--
-- One request is one job: ACTUALS (stock and, when chosen, finance, in ONE
-- statement), one SECTION per page of the run (its targets rendered from the
-- stored page), FRESHNESS (changes since the snapshot), SUMMARY (rendered,
-- checked against the series and sealed as the publication). The client
-- calls step while RUNNING, as for the staged analysis job.

create table cp7_analysis_stage.report_jobs(id uuid primary key,actor uuid not null,request_id uuid not null,payload jsonb not null,
 run_id uuid not null references cp7_analysis_stage.page_sets(run_id),analysis_job uuid not null references cp7_analysis_stage.jobs(id),
 identity_hash text not null,data_as_of timestamptz not null,period_query jsonb not null,
 kind text not null check(kind in('DAILY','PERIOD','EXCEPTIONS','ARCHIVE')),finance text not null check(finance in('INCLUDED','DEFERRED')),
 series_id uuid not null,revision bigint not null check(revision>0),page_count integer not null check(page_count>=0),
 targets_total integer not null check(targets_total>=0),access_at_request jsonb not null,
 state text not null check(state in('RUNNING','DONE','FAILED','CLOSED_UNCOMMITTED')),unit_count integer not null check(unit_count>=0),
 units_done integer not null default 0,unit_attempts integer not null default 0,failure_unit integer,failure_sqlstate text,failure_code text,
 failure_message text,publication_id uuid,created_at timestamptz not null,updated_at timestamptz not null,unique(actor,request_id),
 check(units_done between 0 and unit_count),check((state='FAILED')=(failure_code is not null)),
 check((state='DONE')=(publication_id is not null)),check(state<>'DONE'or units_done=unit_count),
 check((state='CLOSED_UNCOMMITTED')=(unit_count=0)),check(state='CLOSED_UNCOMMITTED'or unit_count=page_count+3));
-- The reads of a job, once each: ACTUALS {read_at, stock per product root,
-- finance or null}; FRESHNESS (cp7.native-analysis-snapshot-freshness.v1).
create table cp7_analysis_stage.report_reads(job_id uuid not null references cp7_analysis_stage.report_jobs(id),
 kind text not null check(kind in('ACTUALS','FRESHNESS')),read_at timestamptz not null,body jsonb not null,server_ms numeric not null,
 primary key(job_id,kind));
-- One rendered section per page of the run (idx = page index).
create table cp7_analysis_stage.report_sections(job_id uuid not null references cp7_analysis_stage.report_jobs(id),idx integer not null check(idx>=0),
 target_lo integer not null,target_hi integer not null,body text not null,utf8_bytes integer not null check(utf8_bytes between 1 and 8000000),
 sha256 text not null,server_ms numeric not null,primary key(job_id,idx),check(target_lo between 1 and target_hi));
-- The sealed publication. report_hash = sha256(summary_sha256 || '\n' ||
-- section sha256s joined by '\n' in index order).
create table cp7_analysis_stage.report_publications(id uuid primary key,job_id uuid not null unique references cp7_analysis_stage.report_jobs(id),
 actor uuid not null,request_id uuid not null,series_id uuid not null,revision bigint not null check(revision>0),
 run_id uuid not null references cp7_analysis_stage.page_sets(run_id),identity_hash text not null,data_as_of timestamptz not null,
 kind text not null check(kind in('DAILY','PERIOD','EXCEPTIONS','ARCHIVE')),period_query jsonb not null,title text not null,reason text not null,
 template_version text not null,finance text not null check(finance in('INCLUDED','DEFERRED')),finance_close_preflight boolean not null,
 report_date date not null,actuals_read_at timestamptz not null,financial_source_hash text,
 freshness_state text not null check(freshness_state in('STALE_VERIFIED','VERIFIED_SAME','CHANGES_RECORDED','NO_RECORDED_CHANGE')),
 freshness_evaluated_at timestamptz not null,changes_total bigint not null check(changes_total>=0),
 summary text not null,summary_utf8_bytes integer not null check(summary_utf8_bytes between 1 and 8000000),summary_sha256 text not null,
 section_count integer not null check(section_count>=0),targets_total integer not null check(targets_total>=0),report_hash text not null,
 published_at timestamptz not null,unique(actor,series_id,revision),unique(actor,request_id),
 check((finance='INCLUDED')=(financial_source_hash is not null)),check(finance='INCLUDED'or not finance_close_preflight));
create index cp7_analysis_stage_report_actor_time on cp7_analysis_stage.report_publications(actor,published_at desc,id desc);
alter table cp7_analysis_stage.report_jobs add constraint report_jobs_publication_fk foreign key(publication_id)
 references cp7_analysis_stage.report_publications(id)deferrable initially deferred;
do $$declare t text;begin
 foreach t in array array['report_jobs','report_reads','report_sections','report_publications']loop
  execute format('alter table cp7_analysis_stage.%I owner to cp7_capture',t);
  execute format('alter table cp7_analysis_stage.%I enable row level security',t);
  execute format('create policy cp7_analysis_stage_no_access on cp7_analysis_stage.%I for all to public using(false)with check(false)',t);
  execute format('revoke all on cp7_analysis_stage.%I from public,anon,authenticated,service_role',t);
 end loop;
 foreach t in array array['report_reads','report_sections','report_publications']loop
  execute format('create trigger immutable_stage_%s before update or delete on cp7_analysis_stage.%I for each row execute function cp7_private.immutable_run()',t,t);
 end loop;
end $$;
-- The job row: only its progress columns (state, units, attempts, failure,
-- publication, updated_at) ever change; a job row is never deleted.
create trigger immutable_stage_report_jobs before update of id,actor,request_id,payload,run_id,analysis_job,identity_hash,data_as_of,period_query,
 kind,finance,series_id,revision,page_count,targets_total,access_at_request,unit_count,created_at or delete
 on cp7_analysis_stage.report_jobs for each row execute function cp7_private.immutable_run();

-- ------------------------------------------------------------ rendering --
create function cp7_analysis_stage.report_wib(t timestamptz)returns text
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select to_char(t at time zone 'Asia/Jakarta','YYYY-MM-DD HH24:MI:SS')||' WIB'
$$;
-- Unit k of a job over n pages: 0 ACTUALS, 1..n SECTION, n+1 FRESHNESS, n+2 SUMMARY.
create function cp7_analysis_stage.report_unit_kind(k integer,n integer)returns text
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select case when k=0 then 'ACTUALS'when k<=n then 'SECTION'when k=n+1 then 'FRESHNESS'when k=n+2 then 'SUMMARY'end
$$;
-- Whether the actor may see owner finance (and the close preflight) now.
create function cp7_analysis_stage.report_finance_access(a jsonb,p_preflight boolean)returns boolean
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select coalesce(a->'profile'->>'role_code'in('OWNER','ADMIN')and erp.has_permission('finance.reports.view')
  and(not p_preflight or erp.has_permission('finance.period_close.manage')),false)
$$;
-- The freshness at publication in words. The snapshot is never called
-- current; a full check only says how it compared at the check's own time.
create function cp7_analysis_stage.report_freshness_text(f jsonb)returns text
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select case f->>'freshness_state'
  when 'VERIFIED_SAME'then 'Sama dengan data per '||cp7_analysis_stage.report_wib((f->>'same_as_of')::timestamptz)||
   ' menurut cek sumber penuh; belum ada perubahan tercatat sesudahnya.'
  when 'STALE_VERIFIED'then 'Data sudah berubah menurut cek sumber penuh '||cp7_analysis_stage.report_wib((f->'last_full_check'->>'checked_at')::timestamptz)||
   '; isi analisis tetap keadaan per '||cp7_analysis_stage.report_wib((f->>'data_as_of')::timestamptz)||'.'
  when 'CHANGES_RECORDED'then 'Ada '||(f->>'changes_total')||' perubahan tercatat sejak data analisis diambil; isi analisis tetap keadaan per '||
   cp7_analysis_stage.report_wib((f->>'data_as_of')::timestamptz)||'.'
  else 'Belum ada perubahan tercatat sejak data analisis diambil; belum dicek penuh.'end
$$;
-- One section: the targets of one page as the run stored them, beside the
-- actual stock read for the report. labels: target_key -> {sku, product_name}
-- (this page's keys only); stock: product root -> {physical_fg_pcs, available_fg_pcs}.
create function cp7_analysis_stage.report_section_text(pg jsonb,labels jsonb,stock jsonb,p_as_of timestamptz,p_read timestamptz)returns text
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 with it as(select coalesce(pg->'items','{}'::jsonb)v),
 w as(select cp7_analysis_stage.report_wib(p_read)r,cp7_analysis_stage.report_wib(p_as_of)s),
 recs as(select string_agg(coalesce(lb->>'sku',x.r->'target'->>'key')||' · '||coalesce(lb->>'product_name','')||' · size '||(x.r->'target'->>'size_id')||' · '||
   case x.r->>'production_state'when'ACTIVE'then'Aktif'when'PAUSED'then'Ditunda'when'STOPPED'then'Dihentikan'else'Status lain'end||
   ': stok fisik saat analisis '||cp7_analysis_native.report_fact(x.r->'actual_fg')||
   '; stok fisik aktual per '||w.r||' '||coalesce(st->>'physical_fg_pcs','Belum diketahui')||' PCS'||
   '; stok tersedia setelah reservasi aktual '||coalesce(st->>'available_fg_pcs','Belum diketahui')||' PCS'||
   '; target '||cp7_analysis_native.report_fact(x.r->'target_qty')||'; gap dasar '||cp7_analysis_native.report_fact(x.r->'q_base')||
   '; gap bersyarat '||cp7_analysis_native.report_fact(x.r->'q_conditional')||
   '; produksi baru layak '||cp7_analysis_native.report_fact(x.r->'feasible_new')||
   '; belum tertutup '||cp7_analysis_native.report_fact(x.r->'unresolved_qty')||'.'||E'\n'||
   'Identitas produk, size dan membership: '||(x.r->'target')::text||'; referensi gap '||coalesce((x.r->'q_base'->'refs')::text,'[]')||
   '; alokasi bersyarat '||coalesce((x.r->'q_conditional'->'refs')::text,'[]')||'.',E'\n\n'order by x.o)t
  from it cross join w cross join lateral jsonb_array_elements(coalesce(it.v->'recommendations','[]'::jsonb))with ordinality x(r,o)
  cross join lateral(select labels->(x.r->'target'->>'key')lb,stock->split_part(x.r->'target'->>'key',':',1)st)z),
 acts as(select string_agg((x.a->>'intent')||' · '||(x.a->>'key')||': '||
   coalesce((select string_agg(b.value,'; 'order by b.ord)from jsonb_array_elements_text(coalesce(x.a->'display_priority'->'basis','[]'::jsonb))with ordinality b(value,ord)),'')||
   '; alasan '||coalesce(x.a->>'primary_reason','')||'; sumber '||coalesce((x.a->'source_links')::text,'[]')||'.',E'\n\n'
   order by(x.a->'display_priority'->>'rank')::numeric nulls first,x.a->>'key',x.o)t
  from it cross join lateral jsonb_array_elements(coalesce(it.v->'actions','[]'::jsonb))with ordinality x(a,o)),
 mats as(select string_agg((x.m->>'target_key')||' · bahan '||coalesce(x.m->>'material_key','belum tertaut')||
   ': kebutuhan '||cp7_analysis_native.report_fact(x.m->'gross')||'; terpasang terbukti '||cp7_analysis_native.report_fact(x.m->'installed_proven')||
   '; sisa layak teralokasi '||cp7_analysis_native.report_fact(x.m->'unused_allocated_proven')||
   '; tambahan eksternal '||cp7_analysis_native.report_fact(x.m->'additional_external')||'. '||coalesce(x.m->>'reason',''),E'\n\n'
   order by x.m->>'target_key',x.m->>'material_key',x.o)t
  from it cross join lateral jsonb_array_elements(coalesce(it.v->'material_needs','[]'::jsonb))with ordinality x(m,o)),
 mets as(select string_agg(case when x.m->>'metric_id'like'AVAILABLE_FG_PCS:%'then'Stok jadi tersedia saat analisis'else x.m->>'metric_id'end||
   ' · '||(x.m->>'scope_key')||': '||cp7_analysis_native.report_fact(x.m->'value')||'; periode '||coalesce(x.m->>'period_start','')||' sampai '||
   coalesce(x.m->>'period_end','')||'; kesiapan '||coalesce(x.m->>'readiness','')||'; sumber '||coalesce((x.m->'value'->'refs')::text,'[]')||'.',E'\n\n'
   order by x.m->>'metric_id',x.m->>'scope_key',x.o)t
  from it cross join lateral jsonb_array_elements(coalesce(it.v->'metrics','[]'::jsonb))with ordinality x(m,o)),
 asm as(select string_agg((x.a->>'id')||': '||coalesce(x.a->>'label','')||'; '||
   case when x.a->'confirmed_for_operation'='true'::jsonb then'dikonfirmasi untuk operasi'else'belum dikonfirmasi untuk operasi'end||'.',E'\n\n'
   order by x.a->>'id',x.o)t
  from it cross join lateral jsonb_array_elements(coalesce(it.v->'assumptions','[]'::jsonb))with ordinality x(a,o)),
 warn as(select string_agg('PERLU DIPERIKSA: '||(x.s#>>'{}'),E'\n\n'order by x.o)t
  from it cross join lateral jsonb_array_elements(coalesce(it.v->'generation_warnings','[]'::jsonb))with ordinality x(s,o))
 select concat_ws(E'\n\n',
  'BAGIAN '||((pg->>'index')::integer+1)||' dari '||(pg->>'page_count')||' · Target '||(pg->>'target_lo')||'–'||(pg->>'target_hi')||
   ' dari '||(pg->>'targets_total')||' · Data analisis per '||w.s||'.',
  'Angka analisis di bagian ini adalah keadaan per '||w.s||', bukan angka saat ini. Stok barang jadi aktual dibaca dari catatan stok ERP per '||w.r||'.',
  'KONDISI PRODUK DAN SIZE',coalesce(recs.t,'Tidak ada target pada bagian ini.'),
  'TINDAKAN DAN ALASAN',coalesce(acts.t,'Tidak ada tindakan per target pada bagian ini.'),
  'KEBUTUHAN BAHAN',coalesce(mats.t,'Tidak ada kebutuhan bahan per target pada bagian ini.'),
  'ANGKA PER TARGET',coalesce(mets.t,'Tidak ada angka per target pada bagian ini.'),
  'ASUMSI PER TARGET',coalesce(asm.t,'Tidak ada asumsi per target pada bagian ini.'),
  warn.t,
  'Issue bukan bukti pemasangan. Barang proses tetap terpisah dari stok jadi. Kelayakan yang belum terbukti tidak mengizinkan produksi baru.')
 from w,recs,acts,mats,mets,asm,warn
$$;
-- The summary: what the report is, its snapshot time and freshness, the
-- actual numbers read for the report date, the whole-run totals and the
-- run-level parts of the analysis, and the section index.
create function cp7_analysis_stage.report_summary_text(j jsonb,hdr jsonb,totals jsonb,actuals jsonb,fresh jsonb,sections jsonb,p_title text)returns text
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare x jsonb:=hdr->'analysis_header';f jsonb:=actuals->'finance';v jsonb;lines text[];rec jsonb:=totals->'recommendations';labels jsonb:='{"SALES":"Penjualan & retur","FG_STOCK":"Stok barang jadi","MATERIAL_STOCK":"Stok bahan","PRODUCTION":"Produksi (potong, jahit, QC, laundry, BS)","PRODUCTION_ORDERS":"PO produksi","MASTER_DATA":"Data induk (produk, SKU, pola, bahan, lokasi)","MATERIAL_PURCHASES":"Pembelian bahan","PLANNING_POLICIES":"Kebijakan perencanaan"}'::jsonb;
 financial_labels jsonb:='{"sales_revenue_gl": "Pendapatan penjualan tercatat", "cogs_gl": "HPP penjualan tercatat", "gross_profit": "Laba kotor", "other_income": "Pendapatan lain tercatat", "operating_and_other_expense": "Beban tercatat", "net_profit": "Laba bersih", "gross_sales_before_discount": "Penjualan sebelum diskon", "line_discounts": "Diskon penjualan", "posted_sales_returns": "Retur penjualan tercatat", "operational_net_sales": "Penjualan bersih operasional", "sales_revenue_bridge_delta": "Selisih penjualan operasional dan jurnal", "assets": "Aset", "cash": "Saldo kas tercatat", "customer_ar": "Piutang pelanggan tercatat", "material_inventory": "Nilai persediaan bahan", "wip_inventory": "Nilai barang dalam proses", "fg_inventory": "Nilai persediaan barang jadi", "liabilities": "Kewajiban", "supplier_final_ap": "Utang pemasok final tercatat", "grni_estimated_liability": "Kewajiban penerimaan belum ditagih tercatat", "recorded_equity": "Ekuitas tercatat", "current_earnings": "Laba berjalan", "liabilities_plus_equity": "Kewajiban dan ekuitas", "balance_difference": "Selisih neraca"}'::jsonb;
 read_at text:=cp7_analysis_stage.report_wib((actuals->>'read_at')::timestamptz);as_of text:=cp7_analysis_stage.report_wib((j->>'data_as_of')::timestamptz);
begin
 lines:=array[p_title,case j->>'kind'when'DAILY'then'BRIEFING HARIAN'when'PERIOD'then'REVIEW PERIODE'when'EXCEPTIONS'then'ANALISIS DAN PENGECUALIAN'else'ARSIP LAPORAN'end,
  'Periode riwayat: '||(j->'period_query'->>'from_date')||' sampai '||(j->'period_query'->>'through_date')||'; pengelompokan '||(j->'period_query'->>'group_mode')||'.',
  'Data analisis per '||as_of||' (analisis bertahap '||(j->>'run_id')||', '||(totals->>'targets')||' target). Isi analisis adalah keadaan pada waktu itu, bukan angka saat ini.',
  'KESEGARAN DATA SAAT LAPORAN DIBUAT',
  'Dihitung '||cp7_analysis_stage.report_wib((fresh->>'evaluated_at')::timestamptz)||': '||cp7_analysis_stage.report_freshness_text(fresh)];
 for v in select c.value from jsonb_array_elements(fresh->'changes_since')c where(c.value->>'rows')::bigint>0 loop
  lines:=array_append(lines,coalesce(labels->>(v->>'category'),v->>'category')||': '||(v->>'rows')||' perubahan'||
   case when(v->>'deleted')::bigint>0 then' ('||(v->>'deleted')||' dihapus)'else''end||
   case when v->>'last_recorded_at'is not null then', terakhir '||cp7_analysis_stage.report_wib((v->>'last_recorded_at')::timestamptz)else''end||'.');
 end loop;
 lines:=array_append(lines,'ANGKA AKTUAL MENURUT SUMBER ERP (TANGGAL LAPORAN '||(actuals->>'report_date')||')');
 lines:=array_append(lines,'Stok barang jadi aktual dibaca dari catatan stok ERP per '||read_at||' dan dicantumkan per target pada bagian rincian, di samping angka saat analisis.');
 if f is null or f='null'::jsonb then
  lines:=array_append(lines,'Keuangan dan HPP tidak dimasukkan ke laporan ini. Tidak ada angka pengganti.');
 else
  v:=cp7_analysis_native.finance_apply(jsonb_build_object('metrics','[]'::jsonb,'financial_readiness',null,'quality','{}'::jsonb,
   'snapshot',jsonb_build_object('fact_count',0),'dependencies','[]'::jsonb,'generation_warnings','[]'::jsonb),jsonb_build_object('financial_source',f));
  lines:=array_append(lines,'Angka keuangan dan HPP dari laporan Native ERP untuk tanggal laporan '||(f->'dates'->>'as_of')||', dibaca '||read_at||
   '; kinerja periode '||(f->'dates'->>'from')||' sampai '||(f->'dates'->>'to')||'; kesiapan '||(v->>'financial_readiness')||
   '. Laba dan penilaian yang belum siap tetap belum diketahui.');
  lines:=lines||coalesce((select array_agg(coalesce(financial_labels->>split_part(m.value->>'metric_id',':',3),m.value->>'metric_id')||': '||
    cp7_analysis_native.report_fact(m.value->'value')||'; periode '||(m.value->>'period_start')||' sampai '||(m.value->>'period_end')||
    '; kesiapan '||(m.value->>'readiness')||'.'order by m.value->>'metric_id'like'NATIVE_FINANCE:performance:%'desc,m.value->>'metric_id')
   from jsonb_array_elements(v->'metrics')m),'{}'::text[]);
  lines:=lines||coalesce((select array_agg('PENGHALANG KEUANGAN: '||(b.value->>'reason')||'; cakupan '||(b.value->>'scope')||
    '; tanggal '||coalesce(b.value->>'impact_date','keadaan sekarang')||'; sumber '||(b.value->'reference')::text||'.'order by b.o)
   from jsonb_array_elements(coalesce(f->'report'->'snapshot'->'data_confidence'->'blockers','[]'::jsonb))with ordinality b(value,o)),'{}'::text[]);
 end if;
 lines:=array_append(lines,'RINGKASAN SELURUH TARGET (SAAT ANALISIS)');
 lines:=array_append(lines,'Status produksi aktif '||(rec->>'ACTIVE')||' target; ditunda '||(rec->>'PAUSED')||'; dihentikan '||(rec->>'STOPPED')||
  '; status lain '||(rec->>'OTHER')||'; status produksi belum diperiksa '||(totals->>'policy_unreviewed')||' target.');
 lines:=array_append(lines,'TINDAKAN UMUM DAN ALASAN');
 lines:=lines||coalesce((select array_agg((a.value->>'intent')||' · '||(a.value->>'key')||': '||
   coalesce((select string_agg(b.value,'; 'order by b.ord)from jsonb_array_elements_text(coalesce(a.value->'display_priority'->'basis','[]'::jsonb))with ordinality b(value,ord)),'')||
   '; alasan '||coalesce(a.value->>'primary_reason','')||'; sumber '||coalesce((a.value->'source_links')::text,'[]')||'.'
   order by(a.value->'display_priority'->>'rank')::numeric nulls first,a.value->>'key')
  from jsonb_array_elements(coalesce(x->'actions','[]'::jsonb))a),array['Tidak ada tindakan umum.']);
 lines:=array_append(lines,'STOK PROSES, BAHAN DAN KAPASITAS (SAAT ANALISIS)');
 lines:=lines||coalesce((select array_agg((s.value->>'source_key')||': fisik '||cp7_analysis_native.report_fact(s.value->'physical_remaining')||
   '; proyeksi '||cp7_analysis_native.report_fact(s.value->'eligible_projected')||'; dibagi '||cp7_analysis_native.report_fact(s.value->'allocated')||
   '; siap '||coalesce(s.value->>'eta','Belum diketahui')||' ('||coalesce(s.value->>'eta_basis','')||').'order by s.value->>'source_key')
  from jsonb_array_elements(coalesce(x->'sources','[]'::jsonb))s),array['Tidak ada stok proses tercatat pada analisis.']);
 lines:=array_append(lines,'ANGKA UMUM (SAAT ANALISIS)');
 lines:=lines||coalesce((select array_agg((m.value->>'metric_id')||' · '||(m.value->>'scope_key')||': '||cp7_analysis_native.report_fact(m.value->'value')||
   '; periode '||coalesce(m.value->>'period_start','')||' sampai '||coalesce(m.value->>'period_end','')||'; kesiapan '||coalesce(m.value->>'readiness','')||'.'
   order by m.value->>'metric_id',m.value->>'scope_key')from jsonb_array_elements(coalesce(x->'metrics','[]'::jsonb))m),array['Tidak ada angka umum.']);
 lines:=array_append(lines,'ASUMSI DAN DATA YANG MASIH KURANG');
 lines:=lines||coalesce((select array_agg((a.value->>'id')||': '||coalesce(a.value->>'label','')||'; '||
   case when a.value->'confirmed_for_operation'='true'::jsonb then'dikonfirmasi untuk operasi'else'belum dikonfirmasi untuk operasi'end||'.'order by a.value->>'id')
  from jsonb_array_elements(coalesce(x->'assumptions','[]'::jsonb))a where jsonb_typeof(a.value)='object'),'{}'::text[]);
 lines:=lines||coalesce((select array_agg('PERLU DIPERIKSA: '||(s.value#>>'{}')order by s.o)
  from jsonb_array_elements(coalesce(x->'generation_warnings','[]'::jsonb))with ordinality s(value,o)
  -- As the finance overlay does: the analysis' own "finance not captured" is
  -- not repeated beside the finance this report read.
  where f is null or f='null'::jsonb or s.value<>'"FINANCIAL_DOMAIN_NOT_CAPTURED"'::jsonb),'{}'::text[]);
 lines:=array_append(lines,'Asumsi per target ada pada bagian rinciannya.');
 lines:=array_append(lines,'BAGIAN RINCIAN');
 lines:=lines||coalesce((select array_agg('Bagian '||((s.value->>'index')::integer+1)||': target '||(s.value->>'target_lo')||'–'||(s.value->>'target_hi')||
   '; '||(s.value->>'utf8_bytes')||' byte; sha256 '||(s.value->>'sha256')||'.'order by(s.value->>'index')::integer)
  from jsonb_array_elements(sections)s),array['Analisis ini tidak memuat rincian per target.']);
 lines:=array_append(lines,'Identitas analisis '||(j->>'identity_hash')||'; template native-report-staged-1. Laporan ini tidak memposting transaksi atau menerapkan produksi.');
 return array_to_string(lines,E'\n\n');
end $$;

-- ---------------------------------------------------------------- reads --
-- The actuals, in ONE statement (one database snapshot, one clock): the
-- finished-goods stock of every product root of the run at p_at, by the
-- analysis' own rules (grade A and B; physical without sale reservations and
-- their reversals; available = every grade A/B movement, i.e. after active
-- reservations), and, when chosen, the Native owner finance report for the
-- Jakarta date of p_at (the report date).
create function cp7_analysis_stage.report_actuals(p_job uuid,p_query jsonb,p_finance boolean,p_at timestamptz)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 with roots as materialized(select distinct split_part(t.target_key,':',1)root from cp7_analysis_stage.plan_targets t where t.job_id=p_job),
 fg as materialized(select coalesce(p.identity_root_id,p.id)::text root,
   sum(m.qty_signed)filter(where m.movement_type<>'SALE_RESERVE'and not exists(select 1 from erp.fg_stock_movements r
     where r.id=m.reversal_of_id and r.movement_type='SALE_RESERVE'))physical,sum(m.qty_signed)available
  from erp.fg_stock_movements m join erp.products p on p.id=m.product_id
  where m.quality_grade in('GRADE_A','GRADE_B')and m.physical_at<=p_at and m.system_created_at<=p_at
   and coalesce(p.identity_root_id,p.id)::text in(select root from roots)group by 1)
 select jsonb_build_object('read_at',p_at,'report_date',(p_at at time zone 'Asia/Jakarta')::date::text,
  'stock',(select coalesce(jsonb_object_agg(r.root,jsonb_build_object('physical_fg_pcs',coalesce(f.physical,0)::text,'available_fg_pcs',coalesce(f.available,0)::text)),'{}'::jsonb)
   from roots r left join fg f on f.root=r.root),
  'finance',case when p_finance then cp7_analysis_native.financial_source(p_query,p_at)end)
$$;

-- ---------------------------------------------------------------- status --
create function cp7_analysis_stage.report_status(p_job uuid)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('contract_version','cp7.report-job.v2','request_id',j.request_id,'state',j.state,
  'stage',case when j.state='RUNNING'then cp7_analysis_stage.report_unit_kind(j.units_done,j.page_count)end,
  'units_done',j.units_done,'unit_count',j.unit_count,'unit_attempts',j.unit_attempts,
  'sections_done',case when j.state='CLOSED_UNCOMMITTED'then 0 else greatest(0,least(j.units_done-1,j.page_count))end,'section_count',j.page_count,
  'run_id',j.run_id,'identity_hash',j.identity_hash,'data_as_of',j.data_as_of,'kind',j.kind,'finance',j.finance,
  'series_id',j.series_id,'revision',j.revision::text,'last_progress_at',j.updated_at,'publication_id',j.publication_id,
  'failure',case when j.state='FAILED'then jsonb_build_object('unit',j.failure_unit,'sqlstate',j.failure_sqlstate,'code',j.failure_code)end,
  'production_go',false)
 from cp7_analysis_stage.report_jobs j where j.id=p_job
$$;

-- -------------------------------------------------------------- request --
-- publish (p_lookup false): the same request UUID with the same payload is
-- the same job (its status); otherwise the actor's own DONE staged run with
-- the presented identity hash, the finance choice permitted now, and for a
-- revision the series' latest version as expected, same kind and period.
-- lookup (p_lookup true): an existing job's status, or the UUID closed for
-- good (CLOSED_UNCOMMITTED) so a delayed publish can never commit it.
create function cp7_analysis_stage.report_request(p jsonb,p_request uuid,p_lookup boolean)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;sj cp7_analysis_stage.jobs%rowtype;ps cp7_analysis_stage.page_sets%rowtype;hd cp7_analysis_stage.headers%rowtype;
 old cp7_analysis_stage.report_jobs%rowtype;prior cp7_analysis_stage.report_publications%rowtype;v_series uuid;v_revision bigint;jid uuid;now_at timestamptz;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);
 perform cp7_wip.fields(p,array['run_id','identity_hash','kind','series_id','expected_revision','title','reason','finance','explicit_review']);
 if p_request is null or jsonb_typeof(p->'run_id')<>'string'or jsonb_typeof(p->'kind')<>'string'
  or p->>'run_id'!~'^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
  or p->>'kind'not in('DAILY','PERIOD','EXCEPTIONS','ARCHIVE')or p->'explicit_review'is distinct from'true'::jsonb
  or jsonb_typeof(p->'identity_hash')<>'string'or p->>'identity_hash'!~'^[0-9a-f]{64}$'
  or jsonb_typeof(p->'finance')<>'string'or p->>'finance'not in('INCLUDED','DEFERRED')
  or jsonb_typeof(p->'title')<>'string'or length(btrim(p->>'title'))not between 1 and 200
  or jsonb_typeof(p->'reason')<>'string'or length(btrim(p->>'reason'))not between 1 and 1000
  or jsonb_typeof(p->'series_id')not in('null','string')then raise exception 'CP7_REPORT_REVIEW';end if;
 if p->'series_id'='null'::jsonb then
  if p->'expected_revision'<>'null'::jsonb then raise exception 'CP7_REPORT_REVISION';end if;
 else
  if p->>'series_id'!~'^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
   or jsonb_typeof(p->'expected_revision')<>'string'or p->>'expected_revision'!~'^[1-9][0-9]{0,18}$'then raise exception 'CP7_REPORT_REVISION';end if;
  if(p->>'expected_revision')::numeric>=9223372036854775807 then raise exception 'CP7_REPORT_REVISION';end if;
 end if;
 -- The v1 request lock: one UUID is one report request across both versions.
 perform pg_advisory_xact_lock(hashtextextended('CP7:REPORT_REQUEST:'||(a->>'actor')||':'||p_request::text,0));
 select *into old from cp7_analysis_stage.report_jobs x where x.actor=(a->>'actor')::uuid and x.request_id=p_request;
 if found then
  if old.payload<>p then raise exception 'CP7_REPORT_REQUEST_CHANGED';end if;
  if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_REPORT_ACCESS_CHANGED';end if;
  return cp7_analysis_stage.report_status(old.id);
 end if;
 if exists(select 1 from cp7_analysis_native.report_requests x where x.actor=(a->>'actor')::uuid and x.request_id=p_request)then
  raise exception 'CP7_REPORT_REQUEST_CHANGED';end if;
 select *into sj from cp7_analysis_stage.jobs x where x.run_id=(p->>'run_id')::uuid and x.actor=(a->>'actor')::uuid and x.state='DONE';
 select *into ps from cp7_analysis_stage.page_sets x where x.run_id=sj.run_id;
 select *into hd from cp7_analysis_stage.headers x where x.run_id=sj.run_id;
 if sj.id is null or ps.run_id is null or hd.run_id is null then raise exception using errcode='42501',message='CP7_REPORT_V2_SNAPSHOT_UNAVAILABLE';end if;
 if ps.identity_hash<>p->>'identity_hash'then raise exception 'CP7_REPORT_V2_IDENTITY_CHANGED';end if;
 if p->'series_id'='null'::jsonb then v_series:=gen_random_uuid();v_revision:=1;
 else v_series:=(p->>'series_id')::uuid;v_revision:=(p->>'expected_revision')::bigint+1;end if;
 if not p_lookup then
  if p->>'finance'='INCLUDED'and not cp7_analysis_stage.report_finance_access(a,false)then
   raise exception using errcode='42501',message='CP7_REPORT_V2_FINANCE_ACCESS';end if;
  if p->'series_id'<>'null'::jsonb then
   perform pg_advisory_xact_lock(hashtextextended('CP7:REPORT_SERIES_V2:'||(a->>'actor')||':'||v_series::text,0));
   select *into prior from cp7_analysis_stage.report_publications x where x.actor=(a->>'actor')::uuid and x.series_id=v_series order by x.revision desc limit 1;
   if prior.id is null then raise exception using errcode='42501',message='CP7_REPORT_V2_SERIES_UNAVAILABLE';end if;
   if prior.revision::text<>p->>'expected_revision'then raise exception using errcode='40001',message='CP7_REPORT_REVISION_CHANGED';end if;
   if prior.kind<>p->>'kind'or prior.period_query<>sj.query then raise exception 'CP7_REPORT_SERIES_SCOPE_CHANGED';end if;
  end if;
 end if;
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_REPORT_ACCESS_CHANGED';end if;
 jid:=gen_random_uuid();now_at:=clock_timestamp();
 insert into cp7_analysis_stage.report_jobs(id,actor,request_id,payload,run_id,analysis_job,identity_hash,data_as_of,period_query,kind,finance,
  series_id,revision,page_count,targets_total,access_at_request,state,unit_count,created_at,updated_at)
 values(jid,(a->>'actor')::uuid,p_request,p,sj.run_id,sj.id,ps.identity_hash,sj.captured_at,sj.query,p->>'kind',p->>'finance',
  v_series,v_revision,hd.page_count,hd.targets_total,a,case when p_lookup then 'CLOSED_UNCOMMITTED'else 'RUNNING'end,
  case when p_lookup then 0 else hd.page_count+3 end,now_at,now_at);
 return cp7_analysis_stage.report_status(jid);
end $$;

-- ----------------------------------------------------------------- units --
-- One unit of the job; returns the publication id from SUMMARY, else null.
create function cp7_analysis_stage.report_run_unit(j cp7_analysis_stage.report_jobs,a jsonb)returns uuid
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare k text:=cp7_analysis_stage.report_unit_kind(j.units_done,j.page_count);t0 timestamptz:=clock_timestamp();body jsonb;txt text;
 pg cp7_analysis_stage.pages%rowtype;hd cp7_analysis_stage.headers%rowtype;labels jsonb;dup text;actuals jsonb;fresh jsonb;sections jsonb;
 prior cp7_analysis_stage.report_publications%rowtype;sha text;hash text;pid uuid;n integer;expect integer;s record;preflight boolean;
begin
 if k='ACTUALS'then
  if j.finance='INCLUDED'and not cp7_analysis_stage.report_finance_access(a,false)then
   raise exception using errcode='42501',message='CP7_REPORT_V2_FINANCE_ACCESS';end if;
  select cp7_analysis_stage.report_actuals(j.analysis_job,j.period_query,j.finance='INCLUDED',clock_timestamp())into body;
  -- The close preflight is shown only to an actor who may manage closing.
  if j.finance='INCLUDED'and coalesce(body->'finance'->'report'->'close_preflight','null')<>'null'::jsonb
   and not cp7_analysis_stage.report_finance_access(a,true)then raise exception using errcode='42501',message='CP7_REPORT_V2_FINANCE_ACCESS';end if;
  insert into cp7_analysis_stage.report_reads values(j.id,'ACTUALS',(body->>'read_at')::timestamptz,body,round(extract(epoch from clock_timestamp()-t0)*1000,1));
  return null;
 end if;
 if k='SECTION'then
  select *into pg from cp7_analysis_stage.pages x where x.run_id=j.run_id and x.idx=j.units_done-1;
  select *into hd from cp7_analysis_stage.headers x where x.run_id=j.run_id;
  select x.body into actuals from cp7_analysis_stage.report_reads x where x.job_id=j.id and x.kind='ACTUALS';
  if pg.run_id is null or hd.run_id is null or actuals is null then raise exception 'CP7_REPORT_V2_STAGE_INVARIANT';end if;
  body:=pg.body::jsonb;
  -- Labels of this page's targets only; a target with two labels is refused
  -- (the v1 render refuses the same way).
  with keys as materialized(select distinct r.value->'target'->>'key'tk from jsonb_array_elements(coalesce(body->'items'->'recommendations','[]'::jsonb))r),
  lb as materialized(select l.value->>'target_key'tk,count(*)n,min(jsonb_build_object('sku',l.value->'sku','product_name',l.value->'product_name')::text)::jsonb v
   from jsonb_array_elements(coalesce((hd.body::jsonb)->'product_labels','[]'::jsonb))l where l.value->>'target_key'in(select tk from keys)group by 1)
  select coalesce(jsonb_object_agg(lb.tk,lb.v),'{}'::jsonb),min(lb.tk)filter(where lb.n>1)into labels,dup from lb;
  if dup is not null then raise exception 'CP7_REPORT_V2_LABEL_AMBIGUOUS';end if;
  txt:=cp7_analysis_stage.report_section_text(body,labels,actuals->'stock',j.data_as_of,(actuals->>'read_at')::timestamptz);
  if octet_length(txt)>8000000 then raise exception 'CP7_REPORT_V2_SECTION_TOO_LARGE';end if;
  insert into cp7_analysis_stage.report_sections values(j.id,pg.idx,pg.target_lo,pg.target_hi,txt,octet_length(txt),
   encode(pg_catalog.sha256(convert_to(txt,'UTF8')),'hex'),round(extract(epoch from clock_timestamp()-t0)*1000,1));
  return null;
 end if;
 if k='FRESHNESS'then
  body:=cp7_analysis_stage.freshness(j.run_id);
  insert into cp7_analysis_stage.report_reads values(j.id,'FRESHNESS',(body->>'evaluated_at')::timestamptz,body,round(extract(epoch from clock_timestamp()-t0)*1000,1));
  return null;
 end if;
 if k='SUMMARY'then
  select x.body into actuals from cp7_analysis_stage.report_reads x where x.job_id=j.id and x.kind='ACTUALS';
  select x.body into fresh from cp7_analysis_stage.report_reads x where x.job_id=j.id and x.kind='FRESHNESS';
  select *into hd from cp7_analysis_stage.headers x where x.run_id=j.run_id;
  if actuals is null or fresh is null or hd.run_id is null then raise exception 'CP7_REPORT_V2_STAGE_INVARIANT';end if;
  preflight:=j.finance='INCLUDED'and coalesce(actuals->'finance'->'report'->'close_preflight','null')<>'null'::jsonb;
  if j.finance='INCLUDED'and not cp7_analysis_stage.report_finance_access(a,preflight)then
   raise exception using errcode='42501',message='CP7_REPORT_V2_FINANCE_ACCESS';end if;
  -- Every section present, contiguous over 1..targets_total, as the run's pages.
  n:=0;expect:=1;
  for s in select x.idx,x.target_lo,x.target_hi from cp7_analysis_stage.report_sections x where x.job_id=j.id order by x.idx loop
   if s.idx<>n or s.target_lo<>expect then raise exception 'CP7_REPORT_V2_STAGE_INVARIANT';end if;
   n:=n+1;expect:=s.target_hi+1;
  end loop;
  if n<>j.page_count or expect<>j.targets_total+1 then raise exception 'CP7_REPORT_V2_STAGE_INVARIANT';end if;
  -- The series: a revision follows the latest version it named, same kind and period.
  perform pg_advisory_xact_lock(hashtextextended('CP7:REPORT_SERIES_V2:'||j.actor::text||':'||j.series_id::text,0));
  select *into prior from cp7_analysis_stage.report_publications x where x.actor=j.actor and x.series_id=j.series_id order by x.revision desc limit 1;
  if coalesce(prior.revision,0)<>j.revision-1 then raise exception using errcode='40001',message='CP7_REPORT_REVISION_CHANGED';end if;
  if prior.id is not null and(prior.kind<>j.kind or prior.period_query<>j.period_query)then raise exception 'CP7_REPORT_SERIES_SCOPE_CHANGED';end if;
  select coalesce(jsonb_agg(jsonb_build_object('index',x.idx,'target_lo',x.target_lo,'target_hi',x.target_hi,'utf8_bytes',x.utf8_bytes,'sha256',x.sha256)order by x.idx),'[]'::jsonb)
   into sections from cp7_analysis_stage.report_sections x where x.job_id=j.id;
  txt:=cp7_analysis_stage.report_summary_text(to_jsonb(j),hd.body::jsonb,(select x.totals from cp7_analysis_stage.page_sets x where x.run_id=j.run_id),
   actuals,fresh,sections,btrim(j.payload->>'title'));
  if octet_length(txt)>8000000 then raise exception 'CP7_REPORT_V2_SUMMARY_TOO_LARGE';end if;
  sha:=encode(pg_catalog.sha256(convert_to(txt,'UTF8')),'hex');
  select encode(pg_catalog.sha256(convert_to(sha||coalesce(E'\n'||string_agg(x.sha256,E'\n'order by x.idx),''),'UTF8')),'hex')into hash
   from cp7_analysis_stage.report_sections x where x.job_id=j.id;
  pid:=gen_random_uuid();
  insert into cp7_analysis_stage.report_publications(id,job_id,actor,request_id,series_id,revision,run_id,identity_hash,data_as_of,kind,period_query,
   title,reason,template_version,finance,finance_close_preflight,report_date,actuals_read_at,financial_source_hash,freshness_state,freshness_evaluated_at,
   changes_total,summary,summary_utf8_bytes,summary_sha256,section_count,targets_total,report_hash,published_at)
  values(pid,j.id,j.actor,j.request_id,j.series_id,j.revision,j.run_id,j.identity_hash,j.data_as_of,j.kind,j.period_query,
   btrim(j.payload->>'title'),btrim(j.payload->>'reason'),'native-report-staged-1',j.finance,preflight,(actuals->>'report_date')::date,
   (actuals->>'read_at')::timestamptz,case when j.finance='INCLUDED'then actuals->'finance'->>'source_hash'end,fresh->>'freshness_state',
   (fresh->>'evaluated_at')::timestamptz,(fresh->>'changes_total')::bigint,txt,octet_length(txt),sha,n,j.targets_total,hash,clock_timestamp());
  return pid;
 end if;
 raise exception 'CP7_REPORT_V2_STAGE_INVARIANT';
end $$;
-- step: the actor's own job; one unit per call, as the staged analysis step
-- (a concurrent caller runs nothing; access changed since the request fails
-- the job; the statement limit is retried three times; any other refusal
-- fails the job with its code; access changing during the unit refuses the
-- call and keeps nothing of the unit).
create function cp7_analysis_stage.report_step(p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;j cp7_analysis_stage.report_jobs%rowtype;pid uuid;s jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);
 select *into j from cp7_analysis_stage.report_jobs x where x.actor=(a->>'actor')::uuid and x.request_id=p_request for update skip locked;
 if not found then
  select *into j from cp7_analysis_stage.report_jobs x where x.actor=(a->>'actor')::uuid and x.request_id=p_request;
  if j.id is null then raise exception using errcode='42501',message='CP7_REPORT_V2_JOB_UNAVAILABLE';end if;
  return cp7_analysis_stage.report_status(j.id)||jsonb_build_object('worker_active',true);
 end if;
 if j.state='RUNNING'then
  if a is distinct from j.access_at_request then
   update cp7_analysis_stage.report_jobs set state='FAILED',updated_at=clock_timestamp(),failure_unit=units_done,failure_sqlstate='42501',
    failure_code='CP7_REPORT_ACCESS_CHANGED',failure_message='CP7_REPORT_ACCESS_CHANGED'where id=j.id;
  else
   begin
    pid:=cp7_analysis_stage.report_run_unit(j,a);
    update cp7_analysis_stage.report_jobs set units_done=units_done+1,unit_attempts=0,updated_at=clock_timestamp(),
     publication_id=coalesce(pid,publication_id),state=case when units_done+1=unit_count then 'DONE'else 'RUNNING'end where id=j.id;
   exception
    when query_canceled then
     update cp7_analysis_stage.report_jobs set unit_attempts=unit_attempts+1,updated_at=clock_timestamp(),
      state=case when unit_attempts+1>=3 then 'FAILED'else state end,
      failure_unit=case when unit_attempts+1>=3 then units_done end,failure_sqlstate=case when unit_attempts+1>=3 then SQLSTATE end,
      failure_code=case when unit_attempts+1>=3 then 'CP7_REPORT_V2_STAGE_STOPPED'end,failure_message=case when unit_attempts+1>=3 then SQLERRM end where id=j.id;
    when others then
     update cp7_analysis_stage.report_jobs set state='FAILED',updated_at=clock_timestamp(),failure_unit=units_done,failure_sqlstate=SQLSTATE,
      failure_code=case when SQLERRM~'^CP7_[A-Z0-9_]+$'then SQLERRM else 'CP7_REPORT_V2_STAGE_ERROR'end,failure_message=SQLERRM where id=j.id;
   end;
  end if;
 end if;
 s:=cp7_analysis_stage.report_status(j.id);
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_REPORT_ACCESS_CHANGED';end if;
 return s;
end $$;

-- --------------------------------------------------------------- readers --
-- A publication of the actor, visible under the finance rule of v1's index
-- (finance only to an owner/admin with finance reports; a close preflight
-- only with period-close rights): its summary, the section index and the
-- access epoch every section read must present.
create function cp7_analysis_stage.report_document(p_id uuid)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;r cp7_analysis_stage.report_publications%rowtype;sections jsonb;latest bigint;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);
 select *into r from cp7_analysis_stage.report_publications x where x.id=p_id and x.actor=(a->>'actor')::uuid;
 if r.id is null or r.finance='INCLUDED'and not cp7_analysis_stage.report_finance_access(a,r.finance_close_preflight)then
  raise exception using errcode='42501',message='CP7_REPORT_UNAVAILABLE';end if;
 select coalesce(jsonb_agg(jsonb_build_object('index',x.idx,'target_lo',x.target_lo,'target_hi',x.target_hi,'utf8_bytes',x.utf8_bytes,'sha256',x.sha256)order by x.idx),'[]'::jsonb)
  into sections from cp7_analysis_stage.report_sections x where x.job_id=r.job_id;
 select max(x.revision)into latest from cp7_analysis_stage.report_publications x where x.actor=r.actor and x.series_id=r.series_id;
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_REPORT_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.report-publication.v2','actor_scope_id',r.actor,'id',r.id,'series_id',r.series_id,
  'revision',r.revision::text,'run_id',r.run_id,'request_id',r.request_id,'identity_hash',r.identity_hash,'data_as_of',r.data_as_of,
  'kind',r.kind,'period_query',r.period_query,'title',r.title,'reason',r.reason,'template_version',r.template_version,
  'finance',r.finance,'report_date',r.report_date::text,'actuals_read_at',r.actuals_read_at,'financial_source_hash',r.financial_source_hash,
  'freshness',jsonb_build_object('state',r.freshness_state,'evaluated_at',r.freshness_evaluated_at,'changes_total',r.changes_total::text),
  'targets_total',r.targets_total,'summary',r.summary,'summary_sha256',r.summary_sha256,'sections',sections,'report_hash',r.report_hash,
  'published_at',r.published_at,'is_latest',r.revision=latest,
  'access_epoch',encode(pg_catalog.sha256(convert_to(a::text,'UTF8')),'hex'),'production_go',false);
end $$;
create function cp7_analysis_stage.report_section(p_id uuid,p_index integer,p_access text)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;r cp7_analysis_stage.report_publications%rowtype;s cp7_analysis_stage.report_sections%rowtype;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);
 if p_access is distinct from encode(pg_catalog.sha256(convert_to(a::text,'UTF8')),'hex')then
  raise exception using errcode='42501',message='CP7_REPORT_ACCESS_CHANGED';end if;
 select *into r from cp7_analysis_stage.report_publications x where x.id=p_id and x.actor=(a->>'actor')::uuid;
 if r.id is null or r.finance='INCLUDED'and not cp7_analysis_stage.report_finance_access(a,r.finance_close_preflight)then
  raise exception using errcode='42501',message='CP7_REPORT_UNAVAILABLE';end if;
 select *into s from cp7_analysis_stage.report_sections x where x.job_id=r.job_id and x.idx=p_index;
 if s.job_id is null then raise exception 'CP7_REPORT_V2_SECTION_UNAVAILABLE';end if;
 return jsonb_build_object('contract_version','cp7.report-section.v2','publication_id',r.id,'report_hash',r.report_hash,'index',s.idx,
  'section_count',r.section_count,'target_lo',s.target_lo,'target_hi',s.target_hi,'utf8_bytes',s.utf8_bytes,'sha256',s.sha256,'body',s.body);
end $$;
create function cp7_analysis_stage.report_index(p jsonb)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;fin boolean;pre boolean;cur uuid;at timestamptz;n integer;out_rows jsonb;total bigint;remaining bigint;next_id text;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);perform cp7_wip.fields(p,array['before_id','limit']);
 if jsonb_typeof(p->'before_id')not in('string','null')or jsonb_typeof(p->'limit')<>'number'or p->>'limit'!~'^[1-9][0-9]?$'then raise exception 'CP7_REPORT_INDEX_QUERY';end if;
 if p->>'before_id'is not null and p->>'before_id'!~'^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'then raise exception 'CP7_REPORT_INDEX_QUERY';end if;
 n:=(p->>'limit')::integer;if n>50 then raise exception 'CP7_REPORT_INDEX_QUERY';end if;cur:=(p->>'before_id')::uuid;
 fin:=cp7_analysis_stage.report_finance_access(a,false);pre:=cp7_analysis_stage.report_finance_access(a,true);
 if cur is not null then
  select x.published_at into at from cp7_analysis_stage.report_publications x where x.actor=(a->>'actor')::uuid and x.id=cur
   and(x.finance='DEFERRED'or fin)and(not x.finance_close_preflight or pre);
  if not found then raise exception using errcode='42501',message='CP7_REPORT_INDEX_CURSOR_UNAVAILABLE';end if;
 end if;
 with visible as materialized(select x.*from cp7_analysis_stage.report_publications x where x.actor=(a->>'actor')::uuid
   and(x.finance='DEFERRED'or fin)and(not x.finance_close_preflight or pre)),
 eligible as materialized(select *from visible v where cur is null or(v.published_at,v.id)<(at,cur)),
 pagerows as materialized(select *from eligible e order by e.published_at desc,e.id desc limit n)
 select coalesce((select jsonb_agg(jsonb_build_object('id',g.id,'series_id',g.series_id,'revision',g.revision::text,'run_id',g.run_id,
   'kind',g.kind,'title',g.title,'period_query',g.period_query,'data_as_of',g.data_as_of,'finance',g.finance,'published_at',g.published_at,
   'report_hash',g.report_hash)order by g.published_at desc,g.id desc)from pagerows g),'[]'::jsonb),(select count(*)from visible),(select count(*)from eligible),
  (select g.id::text from pagerows g order by g.published_at,g.id limit 1)into out_rows,total,remaining,next_id;
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_REPORT_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.report-index.v2','actor_scope_id',a->>'actor','rows',out_rows,'total',total::text,
  'next_before_id',case when remaining>n then next_id end,'page_complete',true,'production_go',false);
end $$;

do $$declare r record;begin
 for r in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname='cp7_analysis_stage'and p.proname like 'report\_%'loop
  execute format('alter function %s owner to cp7_capture',r.sig);
  execute format('revoke all on function %s from public,anon,authenticated,service_role',r.sig);
 end loop;
end $$;
grant create on schema public to cp7_capture;
create function public.erp_cp7_publish_report_v2(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_analysis_stage.report_request(p_payload,p_request,false)$$;
create function public.erp_cp7_get_report_request_v2(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_analysis_stage.report_request(p_payload,p_request,true)$$;
create function public.erp_cp7_step_report_v2(p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_analysis_stage.report_step(p_request)$$;
create function public.erp_cp7_read_report_v2(p_id uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_analysis_stage.report_document(p_id)$$;
create function public.erp_cp7_read_report_section_v2(p_id uuid,p_index integer,p_access text)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_analysis_stage.report_section(p_id,p_index,p_access)$$;
create function public.erp_cp7_list_reports_v2(p_query jsonb)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_analysis_stage.report_index(p_query)$$;
alter function public.erp_cp7_publish_report_v2(jsonb,uuid)owner to cp7_capture;
alter function public.erp_cp7_get_report_request_v2(jsonb,uuid)owner to cp7_capture;
alter function public.erp_cp7_step_report_v2(uuid)owner to cp7_capture;
alter function public.erp_cp7_read_report_v2(uuid)owner to cp7_capture;
alter function public.erp_cp7_read_report_section_v2(uuid,integer,text)owner to cp7_capture;
alter function public.erp_cp7_list_reports_v2(jsonb)owner to cp7_capture;
revoke create on schema public from cp7_capture;
revoke all on function public.erp_cp7_publish_report_v2(jsonb,uuid),public.erp_cp7_get_report_request_v2(jsonb,uuid),public.erp_cp7_step_report_v2(uuid),
 public.erp_cp7_read_report_v2(uuid),public.erp_cp7_read_report_section_v2(uuid,integer,text),public.erp_cp7_list_reports_v2(jsonb)
 from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_publish_report_v2(jsonb,uuid),public.erp_cp7_get_report_request_v2(jsonb,uuid),public.erp_cp7_step_report_v2(uuid),
 public.erp_cp7_read_report_v2(uuid),public.erp_cp7_read_report_section_v2(uuid,integer,text),public.erp_cp7_list_reports_v2(jsonb)to authenticated;
