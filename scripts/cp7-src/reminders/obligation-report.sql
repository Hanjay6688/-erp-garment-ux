-- P15: a dated appendix to an immutable Native publication. No business DML,
-- monetary aggregation, historical reconstruction or external transport.
grant usage on schema cp7_analysis_native to cp7_reminder;
grant select on cp7_analysis_native.publications to cp7_reminder;
create table cp7_reminder_native.obligation_reports(
 id uuid primary key default gen_random_uuid(),actor uuid not null,series_id uuid not null,
 revision bigint not null check(revision>0),run_id uuid not null,publication_id uuid not null,
 request_id uuid not null,title text not null,reason text not null,source jsonb not null,
 body text not null,body_sha256 text not null,published_at timestamptz not null,
 unique(actor,series_id,revision),unique(actor,request_id));
create table cp7_reminder_native.obligation_report_requests(
 actor uuid not null,request_id uuid not null,payload jsonb not null,
 document_id uuid references cp7_reminder_native.obligation_reports(id),
 status text not null check(status in('COMMITTED','CLOSED_UNCOMMITTED')),
 primary key(actor,request_id),check((status='COMMITTED')=(document_id is not null)));
alter table cp7_reminder_native.obligation_reports owner to cp7_reminder;
alter table cp7_reminder_native.obligation_report_requests owner to cp7_reminder;
alter table cp7_reminder_native.obligation_reports enable row level security;
alter table cp7_reminder_native.obligation_report_requests enable row level security;
create policy obligation_report_no_access on cp7_reminder_native.obligation_reports
 for all to public using(false)with check(false);
create policy obligation_report_request_no_access on cp7_reminder_native.obligation_report_requests
 for all to public using(false)with check(false);
revoke all on cp7_reminder_native.obligation_reports,cp7_reminder_native.obligation_report_requests
 from public,anon,authenticated,service_role;
create trigger obligation_report_immutable before update or delete on cp7_reminder_native.obligation_reports
 for each row execute function cp7_reminder_native.immutable_request();
create trigger obligation_report_request_immutable before update or delete on cp7_reminder_native.obligation_report_requests
 for each row execute function cp7_reminder_native.immutable_request();
create index obligation_report_actor_time on cp7_reminder_native.obligation_reports(actor,published_at desc,id desc);

create function cp7_reminder_native.obligation_report_fields(p jsonb,keys text[])returns void
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
begin
 if jsonb_typeof(p)is distinct from'object'then raise exception 'CP7_OBLIGATION_REPORT_FIELDS';end if;
 if not(p?&keys)or(select count(*)from jsonb_object_keys(p))<>cardinality(keys)
  then raise exception 'CP7_OBLIGATION_REPORT_FIELDS';end if;
end $$;

create function cp7_reminder_native.obligation_report_visible(s jsonb)returns boolean
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare r jsonb;k text;d text;access jsonb;
begin
 if s->>'contract_version' is distinct from 'cp7.native-rule-conditions.v2'
  or s->>'actor_scope_id' is distinct from auth.uid()::text then return false;end if;
 access:=erp.get_my_access_v1();
 if coalesce(s->'analysis'->'financial_source','null')<>'null'::jsonb then
  if access->'profile'->>'role_code'not in('OWNER','ADMIN')or not erp.has_permission('finance.reports.view')then return false;end if;
  if coalesce(s->'analysis'->'financial_source'->'report'->'close_preflight','null')<>'null'::jsonb
   and not erp.has_permission('finance.period_close.manage')then return false;end if;
 end if;
 for k,d in select key,value from jsonb_each_text('{"sales_ar":"SALES_AR","material_ap":"MATERIAL_AP","opening_ar":"OPENING_AR","opening_ap":"OPENING_AP","payroll_ap":"PAYROLL_AP","accessory_ap":"ACCESSORY_AP","laundry_ap":"LAUNDRY_AP"}'::jsonb)loop
  if s->'coverage'->>k is distinct from'EXCLUDED_BY_CURRENT_RIGHTS'
   and not cp7_reminder_native.condition_domain_access(d)then return false;end if;
 end loop;
 for r in select value from jsonb_array_elements(s->'rows')loop
  if not cp7_reminder_native.condition_domain_access(r->>'domain')then return false;end if;
 end loop;
 return true;
end $$;

create function cp7_reminder_native.obligation_report_render(b jsonb,s jsonb,p_title text)returns text
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare lines text[];r jsonb;f jsonb;remaining text;due text;k text;v text;
 labels jsonb:='{"SALES_AR":"Piutang penjualan","MATERIAL_AP":"Utang bahan","OPENING_AR":"Piutang saldo awal","OPENING_AP":"Utang saldo awal","PAYROLL_AP":"Utang gaji","ACCESSORY_AP":"Kredit retur aksesori","LAUNDRY_AP":"Utang nota laundry","LAUNDRY_RECEIPT":"Penerimaan laundry belum final","LAUNDRY_OPENING_UNINVOICED":"Laundry saldo awal belum ditagih"}';
begin
 lines:=array[p_title,'LAPORAN DAN LAMPIRAN TAGIHAN ERP',b->>'body',
  'TAGIHAN YANG DIKETAHUI SAAT LAMPIRAN DIBUAT',
  'Dibaca '||to_char((s->>'read_at')::timestamptz at time zone'Asia/Jakarta','YYYY-MM-DD HH24:MI:SS')||
   ' WIB. Ini keadaan sumber saat dibaca, bukan rekonstruksi tagihan pada periode laporan lama.',
  'Angka berikut disalin per dokumen dari ERP. Saldo awal, alokasi gaji, kredit retur, penerimaan dan nota dapat saling terkait. Jangan menjumlahkan baris ini sebagai total utang. Estimasi dan penerimaan belum ditagih tidak menjadi utang final.',
  'CAKUPAN IZIN DAN SUMBER'];
 for k,v in select key,value from jsonb_each_text(s->'coverage')order by key collate "C"loop
  lines:=array_append(lines,k||': '||v||'.');
 end loop;
 for r in select value from jsonb_array_elements(s->'rows')
  where value->'financial_source' is distinct from 'null'::jsonb order by(value->>'key')collate "C"loop
  f:=r->'financial_source';
  remaining:=case when f->'remaining'->>'state'='KNOWN'then f->'remaining'->>'value'||' IDR'
   else 'Belum diketahui ('||coalesce(f->'remaining'->>'reason','sumber belum terbukti')||')'end;
  due:=coalesce(f->>'recorded_due_date','Belum diketahui');
  lines:=array_append(lines,coalesce(labels->>(r->>'domain'),r->>'domain')||' · '||(r->>'label')||
   ': sisa '||remaining||'; jatuh tempo tercatat '||due||'; keadaan ekonomi '||(r->>'economic_state')||
   '; pemeriksaan '||(r->>'reason')||'; sumber '||(r->>'key')||'.');
  lines:=array_append(lines,'Revisi sumber '||(f->>'revision_basis')||'; hash dokumen '||
   (f->>'document_sha256')||'. Referensi lengkap dipertahankan bersama sumber lampiran.');
 end loop;
 lines:=array_append(lines,'Arsip dasar '||(b->>'id')||'; hash isi '||(b->>'body_sha256')||
  '; sumber lampiran '||(s->>'source_hash')||'; template native-obligation-report-1. Tidak memposting transaksi.');
 return array_to_string(lines,E'\n\n');
end $$;

create function cp7_reminder_native.obligation_report_index(p jsonb)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;cursor uuid;at timestamptz;n integer;rows jsonb;total bigint;remaining bigint;next_id uuid;
begin
 perform cp7_reminder_native.obligation_report_fields(p,array['run_id','before_id','limit']);
 if jsonb_typeof(p->'run_id')<>'string'
  or p->>'run_id'!~'^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
  or jsonb_typeof(p->'before_id')not in('null','string')
  or jsonb_typeof(p->'limit')<>'number'or p->>'limit'!~'^[1-9][0-9]?$'
  then raise exception 'CP7_OBLIGATION_REPORT_INDEX_QUERY';end if;
 a:=cp7_reminder_native.access_now((p->>'run_id')::uuid);
 n:=(p->>'limit')::integer;if n>50 then raise exception 'CP7_OBLIGATION_REPORT_INDEX_QUERY';end if;
 cursor:=(p->>'before_id')::uuid;
 if cursor is not null then
  select published_at into at from cp7_reminder_native.obligation_reports
   where id=cursor and actor=auth.uid()and cp7_reminder_native.obligation_report_visible(source);
  if not found then raise exception using errcode='42501',message='CP7_OBLIGATION_REPORT_CURSOR_UNAVAILABLE';end if;
 end if;
 with visible as materialized(select *from cp7_reminder_native.obligation_reports
  where actor=auth.uid()and cp7_reminder_native.obligation_report_visible(source)),
 eligible as materialized(select *from visible where cursor is null or(published_at,id)<(at,cursor)),
 page as materialized(select *from eligible order by published_at desc,id desc limit n)
 select coalesce((select jsonb_agg(jsonb_build_object('id',id,'series_id',series_id,'revision',revision::text,
  'run_id',run_id,'publication_id',publication_id,'title',title,'published_at',published_at,'body_sha256',body_sha256)
  order by published_at desc,id desc)from page),'[]'),(select count(*)from visible),(select count(*)from eligible),
  (select id from page order by published_at,id limit 1)into rows,total,remaining,next_id;
 perform cp7_reminder_native.recheck(a);
 return jsonb_build_object('contract_version','cp7.obligation-report-index.v1','actor_scope_id',auth.uid(),
  'rows',rows,'total',total::text,'next_before_id',case when remaining>n then next_id else null end,
  'page_complete',true,'production_go',false);
end $$;

create function cp7_reminder_native.obligation_report_base(p_id uuid,e jsonb)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare r cp7_analysis_native.publications%rowtype;
begin
 select *into r from cp7_analysis_native.publications where id=p_id and actor=auth.uid();
 if r.id is null then raise exception using errcode='42501',message='CP7_REPORT_UNAVAILABLE';end if;
 if r.run_id::text is distinct from e->>'run_id'or r.source_hash is distinct from e->'analysis'->'snapshot'->>'source_hash'
  or r.semantic_hash is distinct from e->'analysis'->>'semantic_hash' then raise exception 'CP7_OBLIGATION_REPORT_ORIGINAL_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.report-publication.v1','actor_scope_id',r.actor,
  'id',r.id,'series_id',r.series_id,'revision',r.revision::text,'run_id',r.run_id,'request_id',r.request_id,
  'kind',r.kind,'period_query',r.period_query,'title',r.title,'reason',r.reason,'template_version',r.template_version,
  'body',r.body,'body_sha256',r.body_sha256,'source_hash',r.source_hash,'semantic_hash',r.semantic_hash,
  'published_at',r.published_at,'is_latest',r.revision=(select max(revision)from cp7_analysis_native.publications where actor=r.actor and series_id=r.series_id),
  'source_state',e->'source_state','analysis',e,'production_go',false);
end $$;

create function cp7_reminder_native.obligation_report_preview(p_publication uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare b jsonb;s jsonb;a jsonb;run uuid;
begin
 select run_id into run from cp7_analysis_native.publications where id=p_publication and actor=auth.uid();
 if run is null then raise exception using errcode='42501',message='CP7_REPORT_UNAVAILABLE';end if;
 s:=cp7_reminder_native.condition_source(run);
 a:=jsonb_build_object('access',erp.get_my_access_v1(),'analysis',s->'analysis');
 b:=cp7_reminder_native.obligation_report_base(p_publication,s->'analysis');
 if b->>'source_state'<>'UNCHANGED'then raise exception using errcode='40001',message='CP7_OBLIGATION_REPORT_SOURCE_CHANGED';end if;
 if not cp7_reminder_native.obligation_report_visible(s)then raise exception using errcode='42501',message='CP7_OBLIGATION_REPORT_DOMAIN_DENIED';end if;
 perform cp7_reminder_native.recheck(a);
 if octet_length(b::text)+octet_length(s::text)>8000000 then raise exception 'CP7_OBLIGATION_REPORT_TOO_LARGE';end if;
 return jsonb_build_object('contract_version','cp7.obligation-report-preview.v1','actor_scope_id',auth.uid(),'base_report',b,'source',s,'production_go',false);
end $$;

create function cp7_reminder_native.obligation_report_document(p_id uuid,p_current_source jsonb default null)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare r cp7_reminder_native.obligation_reports%rowtype;b jsonb;current_source jsonb;a jsonb;state text;
begin
 if auth.uid()is null then raise exception using errcode='42501',message='CP7_OBLIGATION_REPORT_UNAVAILABLE';end if;
 select *into r from cp7_reminder_native.obligation_reports where id=p_id and actor=auth.uid();
 if r.id is null then raise exception using errcode='42501',message='CP7_OBLIGATION_REPORT_UNAVAILABLE';end if;
 if not cp7_reminder_native.obligation_report_visible(r.source)then raise exception using errcode='42501',message='CP7_OBLIGATION_REPORT_DOMAIN_DENIED';end if;
 -- A write supplies the fresh, fully protected snapshot it just read. Other
 -- reads call the full current-source reader, never a body-only cache.
 current_source:=case when p_current_source is null then cp7_reminder_native.condition_source(r.run_id)else p_current_source end;
 if current_source->>'actor_scope_id' is distinct from auth.uid()::text or current_source->'analysis'->>'run_id' is distinct from r.run_id::text
  then raise exception using errcode='42501',message='CP7_OBLIGATION_REPORT_UNAVAILABLE';end if;
 a:=jsonb_build_object('access',erp.get_my_access_v1(),'analysis',current_source->'analysis');
 b:=cp7_reminder_native.obligation_report_base(r.publication_id,current_source->'analysis');
 state:=case when b->>'source_state'='UNCHANGED'and current_source->>'source_hash'=r.source->>'source_hash'then'UNCHANGED'else'ARCHIVED_STALE'end;
 perform cp7_reminder_native.recheck(a);
 return jsonb_build_object('contract_version','cp7.obligation-report.v1','actor_scope_id',r.actor,
  'id',r.id,'series_id',r.series_id,'revision',r.revision::text,'run_id',r.run_id,'publication_id',r.publication_id,
  'request_id',r.request_id,'title',r.title,'reason',r.reason,'published_at',r.published_at,
  'is_latest',r.revision=(select max(revision)from cp7_reminder_native.obligation_reports where actor=r.actor and series_id=r.series_id),
  'source_hash',r.source->>'source_hash','source',r.source,'base_report',b,'source_state',state,
  'template_version','native-obligation-report-1','body',r.body,'body_sha256',r.body_sha256,'production_go',false);
end $$;

create function cp7_reminder_native.obligation_report_command(p jsonb,p_request uuid,p_lookup boolean)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;b jsonb;preview jsonb;s jsonb;old cp7_reminder_native.obligation_report_requests%rowtype;
 prior cp7_reminder_native.obligation_reports%rowtype;r cp7_reminder_native.obligation_reports%rowtype;
 series uuid;revision bigint;body text;prior_doc jsonb;
begin
 perform cp7_reminder_native.obligation_report_fields(p,array['publication_id','run_id','source_hash','title','reason','explicit_review','series_id','expected_revision']);
 if p_request is null or jsonb_typeof(p->'publication_id')<>'string'or jsonb_typeof(p->'run_id')<>'string'
  or p->>'publication_id'!~'^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
  or p->>'run_id'!~'^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
  or jsonb_typeof(p->'source_hash')<>'string'or p->>'source_hash'!~'^[0-9a-f]{64}$'
  or jsonb_typeof(p->'title')<>'string'or length(btrim(p->>'title'))not between 1 and 200
  or jsonb_typeof(p->'reason')<>'string'or length(btrim(p->>'reason'))not between 1 and 1000
  or p->'explicit_review'is distinct from'true'::jsonb or jsonb_typeof(p->'series_id')not in('null','string')
  then raise exception 'CP7_OBLIGATION_REPORT_REVIEW';end if;
 if p->'series_id'='null'::jsonb then
  if p->'expected_revision'<>'null'::jsonb then raise exception 'CP7_OBLIGATION_REPORT_REVISION';end if;
 else
  if p->>'series_id'!~'^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
   or jsonb_typeof(p->'expected_revision')<>'string'or p->>'expected_revision'!~'^[1-9][0-9]{0,18}$'
   then raise exception 'CP7_OBLIGATION_REPORT_REVISION';end if;
  if(p->>'expected_revision')::numeric>=9223372036854775807 then raise exception 'CP7_OBLIGATION_REPORT_REVISION';end if;
 end if;
 a:=cp7_reminder_native.original_authority((p->>'run_id')::uuid);
 -- Admission validates only immutable identity. New publication replaces
 -- this base with the complete current, protected preview after all waits;
 -- cached documents also perform their full current-source reader.
 b:=cp7_reminder_native.obligation_report_base((p->>'publication_id')::uuid,a->'analysis');
 if b->>'run_id'<>p->>'run_id' then raise exception 'CP7_OBLIGATION_REPORT_ORIGINAL_CHANGED';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:OBLIGATION_REPORT_REQUEST:'||auth.uid()::text||':'||p_request::text,0));
 perform cp7_reminder_native.recheck(a);
 select *into old from cp7_reminder_native.obligation_report_requests where actor=auth.uid()and request_id=p_request;
 if found then
  if old.payload<>p then raise exception 'CP7_OBLIGATION_REPORT_REQUEST_CHANGED';end if;
  return jsonb_build_object('contract_version','cp7.obligation-report-command.v1','request_id',p_request,'status',old.status,
   'document',case when old.document_id is not null then cp7_reminder_native.obligation_report_document(old.document_id)else null end,'production_go',false);
 end if;
 if p_lookup then
  insert into cp7_reminder_native.obligation_report_requests(actor,request_id,payload,status)
   values(auth.uid(),p_request,p,'CLOSED_UNCOMMITTED');
  return jsonb_build_object('contract_version','cp7.obligation-report-command.v1','request_id',p_request,'status','CLOSED_UNCOMMITTED','document',null,'production_go',false);
 end if;
 if p->'series_id'='null'::jsonb then series:=gen_random_uuid();revision:=1;
 else
  series:=(p->>'series_id')::uuid;
  perform pg_advisory_xact_lock(hashtextextended('CP7:OBLIGATION_REPORT_SERIES:'||auth.uid()::text||':'||series::text,0));
  perform cp7_reminder_native.recheck(a);
  select q.*into prior from cp7_reminder_native.obligation_reports q
   where q.actor=auth.uid()and q.series_id=series order by q.revision desc limit 1;
  if prior.id is null or prior.revision::text<>p->>'expected_revision'
   then raise exception using errcode='40001',message='CP7_OBLIGATION_REPORT_REVISION_CHANGED';end if;
  prior_doc:=cp7_reminder_native.obligation_report_document(prior.id);
  if prior.source->'analysis'->'query' is distinct from b->'period_query'or prior_doc->'base_report'->>'kind' is distinct from b->>'kind'
   then raise exception 'CP7_OBLIGATION_REPORT_SERIES_SCOPE_CHANGED';end if;
  revision:=prior.revision+1;
 end if;
 preview:=cp7_reminder_native.obligation_report_preview((p->>'publication_id')::uuid);
 s:=preview->'source';b:=preview->'base_report';
 if s->>'source_hash'<>p->>'source_hash'then raise exception using errcode='40001',message='CP7_OBLIGATION_REPORT_SOURCE_CHANGED';end if;
 body:=cp7_reminder_native.obligation_report_render(b,s,btrim(p->>'title'));
 if octet_length(body)+octet_length(preview::text)>8000000 then raise exception 'CP7_OBLIGATION_REPORT_TOO_LARGE';end if;
 perform cp7_reminder_native.recheck(a);
 insert into cp7_reminder_native.obligation_reports(actor,series_id,revision,run_id,publication_id,request_id,title,reason,source,body,body_sha256,published_at)
  values(auth.uid(),series,revision,(p->>'run_id')::uuid,(p->>'publication_id')::uuid,p_request,
   btrim(p->>'title'),btrim(p->>'reason'),s,body,encode(pg_catalog.sha256(convert_to(body,'UTF8')),'hex'),clock_timestamp())returning *into r;
 insert into cp7_reminder_native.obligation_report_requests(actor,request_id,payload,document_id,status)
  values(r.actor,p_request,p,r.id,'COMMITTED');
 return jsonb_build_object('contract_version','cp7.obligation-report-command.v1','request_id',p_request,'status','COMMITTED',
  'document',cp7_reminder_native.obligation_report_document(r.id,s),'production_go',false);
end $$;

alter function cp7_reminder_native.obligation_report_visible(jsonb)owner to cp7_reminder;
alter function cp7_reminder_native.obligation_report_fields(jsonb,text[])owner to cp7_reminder;
alter function cp7_reminder_native.obligation_report_render(jsonb,jsonb,text)owner to cp7_reminder;
alter function cp7_reminder_native.obligation_report_preview(uuid)owner to cp7_reminder;
alter function cp7_reminder_native.obligation_report_base(uuid,jsonb)owner to cp7_reminder;
alter function cp7_reminder_native.obligation_report_document(uuid,jsonb)owner to cp7_reminder;
alter function cp7_reminder_native.obligation_report_command(jsonb,uuid,boolean)owner to cp7_reminder;
alter function cp7_reminder_native.obligation_report_index(jsonb)owner to cp7_reminder;
revoke all on function cp7_reminder_native.obligation_report_fields(jsonb,text[]),cp7_reminder_native.obligation_report_visible(jsonb),cp7_reminder_native.obligation_report_render(jsonb,jsonb,text),
 cp7_reminder_native.obligation_report_preview(uuid),cp7_reminder_native.obligation_report_base(uuid,jsonb),cp7_reminder_native.obligation_report_document(uuid,jsonb),
 cp7_reminder_native.obligation_report_command(jsonb,uuid,boolean),cp7_reminder_native.obligation_report_index(jsonb)from public,anon,authenticated,service_role;
grant create on schema public to cp7_reminder;
create function public.erp_cp7_get_obligation_report_preview_v1(p_publication uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.obligation_report_preview(p_publication)$$;
create function public.erp_cp7_read_obligation_report_v1(p_id uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.obligation_report_document(p_id)$$;
create function public.erp_cp7_publish_obligation_report_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.obligation_report_command(p_payload,p_request,false)$$;
create function public.erp_cp7_get_obligation_report_request_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.obligation_report_command(p_payload,p_request,true)$$;
create function public.erp_cp7_list_obligation_reports_v1(p_query jsonb)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.obligation_report_index(p_query)$$;
alter function public.erp_cp7_get_obligation_report_preview_v1(uuid)owner to cp7_reminder;
alter function public.erp_cp7_read_obligation_report_v1(uuid)owner to cp7_reminder;
alter function public.erp_cp7_publish_obligation_report_v1(jsonb,uuid)owner to cp7_reminder;
alter function public.erp_cp7_get_obligation_report_request_v1(jsonb,uuid)owner to cp7_reminder;
alter function public.erp_cp7_list_obligation_reports_v1(jsonb)owner to cp7_reminder;
revoke create on schema public from cp7_reminder;
revoke all on function public.erp_cp7_get_obligation_report_preview_v1(uuid),public.erp_cp7_read_obligation_report_v1(uuid),
 public.erp_cp7_publish_obligation_report_v1(jsonb,uuid),public.erp_cp7_get_obligation_report_request_v1(jsonb,uuid),public.erp_cp7_list_obligation_reports_v1(jsonb)
 from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_get_obligation_report_preview_v1(uuid),public.erp_cp7_read_obligation_report_v1(uuid),
 public.erp_cp7_publish_obligation_report_v1(jsonb,uuid),public.erp_cp7_get_obligation_report_request_v1(jsonb,uuid),public.erp_cp7_list_obligation_reports_v1(jsonb)to authenticated;
