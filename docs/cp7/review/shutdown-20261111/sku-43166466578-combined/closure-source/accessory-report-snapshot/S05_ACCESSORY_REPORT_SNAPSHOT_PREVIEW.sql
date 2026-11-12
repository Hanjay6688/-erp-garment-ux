CREATE OR REPLACE FUNCTION cp7_accessory_standard_report.workspace_data_v1(p_start date, p_end date, p_contractor uuid, p_po uuid, p_query text, p_offset integer, p_limit integer)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
 SET search_path TO ''
AS $function$
declare v_result jsonb;v_report jsonb;v_total integer;v_contractors jsonb;v_pos jsonb;v_selected jsonb;v_q text;
begin
 if p_start is null or p_end is null or not isfinite(p_start)or not isfinite(p_end)or p_end<p_start or p_end-p_start>366
  or p_start<'2000-01-01'::date or p_end>'9999-12-31'::date
  or p_query is null or length(p_query)>100 or p_offset is null or p_offset not between 0 and 1000000
  or p_limit is null or p_limit not between 1 and 50 or(p_po is not null and p_contractor is null)then
  raise exception 'CP7_ACCESSORY_REPORT_FIELDS: isi periode yang sah (maksimal 367 hari), mandor dan halaman yang sah.';end if;
 v_q:=btrim(p_query);
 select count(*)into v_total from erp.contractors c where position(lower(v_q)in lower(c.contractor_name||' '||c.contractor_code))>0;
 select coalesce(jsonb_agg(jsonb_build_object('id',c.id,'name',c.contractor_name,'active',c.is_active)order by c.contractor_name,c.id),'[]')into v_contractors
  from(select c.*from erp.contractors c where position(lower(v_q)in lower(c.contractor_name||' '||c.contractor_code))>0
   order by c.contractor_name,c.id offset p_offset limit p_limit)c;
 if p_contractor is not null then
  select jsonb_build_object('id',c.id,'name',c.contractor_name,'active',c.is_active)into v_selected from erp.contractors c where c.id=p_contractor;
  if v_selected is null then raise exception 'CP7_ACCESSORY_REPORT_FIELDS: mandor tidak ditemukan.';end if;
  -- Filter options are identities only. The report itself applies the PO to
  -- both cohorts and continues to expose each row's original source PO.
  select coalesce(jsonb_agg(jsonb_build_object('id',x.id,'number',x.po_number)order by x.po_number,x.id),'[]')into v_pos
   from(select po.id,po.po_number from erp.production_orders po where po.contractor_id=p_contractor
    or exists(select 1 from erp.contractor_material_issues i where i.po_id=po.id and i.contractor_id=p_contractor))x;
  if jsonb_array_length(v_pos)>1000 then raise exception 'CP7_ACCESSORY_REPORT_TOO_LARGE: daftar PO melebihi batas pembaca; diperlukan pembaca PO berhalaman.';end if;
  if p_po is not null and not exists(select 1 from jsonb_array_elements(v_pos)x where x->>'id'=p_po::text)then
   raise exception 'CP7_ACCESSORY_REPORT_FIELDS: PO tidak terkait dengan mandor ini.';end if;
  v_report:=cp7_accessory_standard_report.period_data(p_start,p_end,p_contractor,p_po);
  if(v_report->'counts'->>'issue_items')::bigint+(v_report->'counts'->>'snapshots')::bigint+(v_report->'counts'->>'lots')::bigint>3000 then
   raise exception 'CP7_ACCESSORY_REPORT_TOO_LARGE: lebih dari 3000 baris sumber; persempit periode atau pilih PO. Angka tidak dipotong.';end if;
 end if;
 v_result:=jsonb_build_object('contract_version','cp7.accessory-standard-report.v1','business_DML',false,
  'captured_at',cp7_accessory_standard_report.iso(statement_timestamp()),
  'query',jsonb_build_object('period_start',p_start,'period_end',p_end,'contractor_id',p_contractor,'po_id',p_po,'q',p_query,'offset',p_offset,'limit',p_limit),
  'contractors',jsonb_build_object('offset',p_offset,'limit',p_limit,'total',v_total,
   'next_offset',case when p_offset+jsonb_array_length(v_contractors)<v_total then p_offset+jsonb_array_length(v_contractors)else null end,'rows',v_contractors),
  'selected_contractor',v_selected,'po_options',coalesce(v_pos,'[]'),'report',v_report);
 return v_result;
end $function$;
alter function cp7_accessory_standard_report.workspace_data_v1(date,date,uuid,uuid,text,integer,integer) owner to postgres;
revoke all on function cp7_accessory_standard_report.workspace_data_v1(date,date,uuid,uuid,text,integer,integer) from public,anon,authenticated,service_role,cp7_capture,cp7_accessory_standard_read;
CREATE OR REPLACE FUNCTION cp7_accessory_standard_report.workspace(p_start date, p_end date, p_contractor uuid, p_po uuid, p_query text, p_offset integer, p_limit integer)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare v_access jsonb;v_result jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_ACCESSORY_REPORT_FRESH_ACCESS_REQUIRED';end if;
 v_access:=cp7_accessory_standard_report.access_now();
 v_result:=cp7_accessory_standard_report.workspace_data_v1(p_start,p_end,p_contractor,p_po,p_query,p_offset,p_limit);
 -- A second live permission read after the statement data read; no cached
 -- JWT metadata, no elevated browser/private grants and no stale answer.
 if cp7_accessory_standard_report.access_now()is distinct from v_access then
  raise exception using errcode='42501',message='CP7_ACCESSORY_REPORT_ACCESS_CHANGED: hak akses berubah; muat ulang.';end if;
 return v_result;
end $function$;
