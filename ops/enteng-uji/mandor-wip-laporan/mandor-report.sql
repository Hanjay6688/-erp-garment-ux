-- S05 / owner D17-19C. This stage adds a reader, never a posting or repair path.
-- Historical standard quantities come only from fg_accessory_cost_snapshots.
-- Committed BOM/selection rows only prove completeness or an explicit empty set.
-- Costs are the Native effective snapshots, with every revision exposed.
create role cp7_accessory_standard_read nologin noinherit nosuperuser nocreatedb nocreaterole noreplication nobypassrls;
grant cp7_accessory_standard_read to postgres with inherit false,set true granted by postgres;
create schema cp7_accessory_standard_report authorization cp7_accessory_standard_read;
revoke all on schema cp7_accessory_standard_report from public,anon,authenticated,service_role,cp7_capture;
set local role cp7_accessory_standard_read;
grant usage,create on schema cp7_accessory_standard_report to postgres;
reset role;

create function cp7_accessory_standard_report.iso(p_at timestamptz)returns text
language sql stable set search_path=''as $$
 select to_char(p_at at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"')$$;

create function cp7_accessory_standard_report.access_now()returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare v_access jsonb;
begin
 if auth.uid()is null or coalesce(auth.jwt()->>'role','')<>'authenticated'then
  raise exception using errcode='42501',message='CP7_ACCESSORY_REPORT_DENIED: masuk dengan akun ERP sendiri.';end if;
 v_access:=erp.get_my_access_v1();
 if v_access->'allowed'is distinct from'true'::jsonb
  or coalesce(v_access->'profile'->>'role_code','')not in('OWNER','ADMIN')
  or not erp.has_permission('finance.contractor_accessory.view')or not erp.has_permission('finance.hpp.view')then
  raise exception using errcode='42501',message='CP7_ACCESSORY_REPORT_DENIED: laporan ini memerlukan Owner/Admin, hak melihat nota aksesori dan HPP.';end if;
 return v_access;
end $$;

-- STABLE gives every source, its completeness assessment and its totals one
-- statement snapshot. No helper that creates a commitment/snapshot is called.
create function cp7_accessory_standard_report.period_data(p_start date,p_end date,p_contractor uuid,p_po uuid)returns jsonb
language sql stable security definer set search_path=''as $$
with
 issue_sources as materialized(
  select ii.id,ii.issue_id,h.issue_number,h.po_id,po.po_number,h.contractor_id,h.physical_at,h.location_id,
   ii.material_id,m.material_sku,m.material_name,m.accessory_category_id category_id,c.category_name,c.base_uom_code,
   ii.qty,ii.unit_cost_snapshot,ii.qty*ii.unit_cost_snapshot inventory_cost,ii.unit_sale_price_snapshot,ii.total_receivable,
   ii.transaction_qty,ii.transaction_uom_code,ii.base_qty_per_transaction_uom,
   ii.accessory_price_version_id,ii.material_price_version_id,
   (select coalesce(jsonb_agg(mv.id order by mv.id),'[]')from erp.material_stock_movements mv
    where mv.source_type='CONTRACTOR_MATERIAL_ISSUE_ITEM'and mv.source_id=ii.id)movement_ids,
   (m.accessory_category_id is not null and c.id is not null and m.unit_code=c.base_uom_code
    and exists(select 1 from erp.material_stock_movements mv where mv.source_type='CONTRACTOR_MATERIAL_ISSUE_ITEM'
     and mv.source_id=ii.id and mv.material_id=ii.material_id and mv.movement_type='CONTRACTOR_ISSUE'
     and mv.reversal_of_id is null and mv.qty_signed=-ii.qty))unit_known
  from erp.contractor_material_issue_items ii
  join erp.contractor_material_issues h on h.id=ii.issue_id
  join erp.materials m on m.id=ii.material_id
  left join erp.accessory_categories c on c.id=m.accessory_category_id
  left join erp.production_orders po on po.id=h.po_id
  where h.status='POSTED'and m.material_type='ACCESSORY'and h.contractor_id=p_contractor
   and h.physical_at>=p_start::timestamp at time zone 'Asia/Jakarta'
   and h.physical_at<(p_end+1)::timestamp at time zone 'Asia/Jakarta'
   and(p_po is null or h.po_id=p_po)
 ),
 lot_base as materialized(
  select l.id,l.lot_number,l.po_id,po.po_number,l.product_id,p.sku,l.produced_at,l.initial_qty_pcs,
   ro.id rework_order_id,d.id decision_id,d.decision_state,d.selected_item_count,d.bom_version_id decision_bom,
   case when ro.id is not null then d.reimbursement_contractor_id else po.contractor_id end contractor_id,
   case when ro.id is not null then 'REWORK_DECISION'else 'GUARDED_PO'end recipient_basis,
   c.id commitment_id,c.bom_version_id committed_bom,
   (select count(*)from erp.accessory_bom_items bi where bi.bom_version_id=c.bom_version_id)committed_item_count,
   (select count(*)from erp.rework_accessory_selection_lines sl where sl.decision_id=d.id)selection_line_count,
   (select count(*)from erp.fg_accessory_cost_snapshots sn where sn.lot_id=l.id)snapshot_count
  from erp.fg_lots l left join erp.production_orders po on po.id=l.po_id
  join erp.products p on p.id=l.product_id
  left join erp.rework_orders ro on ro.good_fg_lot_id=l.id
  left join erp.rework_accessory_decisions d on d.rework_order_id=ro.id
  left join erp.po_accessory_bom_commitments c on c.po_id=l.po_id and c.product_id=l.product_id
  where l.lot_origin='PRODUCTION'
   and l.produced_at>=p_start::timestamp at time zone 'Asia/Jakarta'
   and l.produced_at<(p_end+1)::timestamp at time zone 'Asia/Jakarta'
   and(p_po is null or l.po_id=p_po)
 ),
 lots as materialized(
  select lb.*,
   array_remove(array[
    case when contractor_id is null then 'UNALLOCATED_RECIPIENT'end,
    case when commitment_id is null then 'MISSING_COMMITMENT'end,
    case when rework_order_id is not null and(decision_id is null or decision_state='UNAVAILABLE')then 'MISSING_REWORK_STANDARD'end,
    case when rework_order_id is not null and decision_bom is distinct from committed_bom then 'REWORK_COMMITMENT_MISMATCH'end,
    case when rework_order_id is not null and(selected_item_count<>selection_line_count or snapshot_count<>selected_item_count)
      then 'MISSING_OR_EXTRA_SNAPSHOT'end,
    case when rework_order_id is null and snapshot_count<>committed_item_count then 'MISSING_OR_EXTRA_SNAPSHOT'end,
    case when exists(select 1 from erp.fg_accessory_cost_snapshots sn
      where sn.lot_id=lb.id and(sn.po_id is distinct from lb.po_id or sn.product_id<>lb.product_id
       or sn.bom_version_id is distinct from lb.committed_bom or sn.good_qty_pcs<>lb.initial_qty_pcs
       or(lb.rework_order_id is null and not exists(select 1 from erp.accessory_bom_items bi
        where bi.id=sn.bom_item_id and bi.bom_version_id=lb.committed_bom and bi.category_id=sn.category_id
         and bi.qty_per_good_fg_base=sn.qty_per_good_fg_base))
       or(lb.rework_order_id is not null and not exists(select 1 from erp.rework_accessory_selection_lines sl
        where sl.decision_id=lb.decision_id and sl.bom_item_id=sn.bom_item_id and sl.category_id=sn.category_id
         and sl.qty_per_good_fg_base_snapshot=sn.qty_per_good_fg_base))))
      then 'SNAPSHOT_LINEAGE_MISMATCH'end
   ],null)::text[]reasons,
   (snapshot_count=0 and commitment_id is not null and
    ((rework_order_id is null and committed_item_count=0)
     or(rework_order_id is not null and decision_state='NONE'and selected_item_count=0
      and decision_bom=committed_bom)))explicit_zero
  from lot_base lb where contractor_id=p_contractor or contractor_id is null
 ),
 standard_sources as materialized(
  select sn.*,l.lot_number,l.po_number,l.sku,l.produced_at,l.contractor_id,l.recipient_basis,l.commitment_id,l.rework_order_id,l.decision_id,
   c.category_name,c.base_uom_code,
   -- The snapshot has no base-UOM field. Timestamp comparisons cannot prove
   -- order within one transaction (both updated_at and snapshotted_at use
   -- now()). Require retained audited creation and no subsequent unit edit.
   -- A renamed category is fine; a unit edit, even an edit back, is UNKNOWN.
   (c.id is not null and exists(select 1 from erp.audit_logs a where a.entity_type='accessory_categories'
     and a.entity_id=c.id and a.action='INSERT'and a.new_data->>'base_uom_code'=c.base_uom_code)
    and not exists(select 1 from erp.audit_logs a where a.entity_type='accessory_categories'and a.entity_id=c.id
     and(a.action='DELETE'or(a.action='UPDATE'and a.old_data->>'base_uom_code'is distinct from a.new_data->>'base_uom_code'))))unit_known,
   coalesce(en.ids,'[]'::jsonb)entitlement_ids,
   (sn.total_reimbursement=0 or(en.n=1 and en.recipient=sn_recipient.contractor_id::text
     and en.amount=sn.total_reimbursement and not en.cancelled))entitlement_known,
   (select coalesce(jsonb_agg(a.id::text order by a.id),'[]')from erp.audit_logs a
    where a.entity_type='accessory_categories'and a.entity_id=c.id
     and(a.action='INSERT'or a.action='DELETE'or(a.action='UPDATE'and a.old_data->>'base_uom_code'is distinct from a.new_data->>'base_uom_code')))unit_basis_audit_ids,
   (select coalesce(jsonb_agg(jsonb_build_object('id',r.id::text,'material_id',r.material_id,
    'old_hpp_unit_cost',r.old_hpp_unit_cost::text,'new_hpp_unit_cost',r.new_hpp_unit_cost::text,
    'old_category_avg_cost',r.old_category_avg_cost::text,'new_category_avg_cost',r.new_category_avg_cost::text,
    'reason',r.reason,'changed_at',cp7_accessory_standard_report.iso(r.changed_at))order by r.changed_at,r.id),'[]')
    from erp.fg_accessory_cost_revisions r where r.snapshot_id=sn.id)revisions
  from erp.fg_accessory_cost_snapshots sn join lots l on l.id=sn.lot_id
  left join erp.accessory_categories c on c.id=sn.category_id
  cross join lateral(select l.contractor_id)sn_recipient
  left join lateral(select count(*)n,min(e.contractor_id::text)recipient,sum(e.amount)amount,bool_or(e.payroll_status='CANCELLED')cancelled,
   jsonb_agg(e.id order by e.id)ids from erp.contractor_accessory_reimbursement_entitlements e where e.snapshot_id=sn.id)en on true
 ),
 quality as(
  select (select count(*)from lots where cardinality(reasons)>0)unknown_lots,
   (select count(*)from lots where contractor_id is null)unallocated_lots,
   (select count(*)from lots where contractor_id=p_contractor)assigned_lots,
   (select count(*)from lots where contractor_id=p_contractor and not explicit_zero)nonempty_lots,
   exists(select 1 from standard_sources where not coalesce(entitlement_known,false))entitlement_unknown
 ),
 category_keys as(select category_id from issue_sources union select category_id from standard_sources where contractor_id=p_contractor),
 category_totals as(
  select k.category_id,c.category_name,c.base_uom_code,
   coalesce(a.qty,0)actual_qty,coalesce(a.cost,0)actual_inventory_cost,
   case when coalesce(a.receivables_known,true)then coalesce(a.receivable,0)else null end actual_receivable,
   case when s.n>0 then s.qty when q.assigned_lots>0 and q.nonempty_lots=0 and q.unknown_lots=0 then 0 else null end standard_qty,
   case when s.n>0 then s.cost when q.assigned_lots>0 and q.nonempty_lots=0 and q.unknown_lots=0 then 0 else null end standard_hpp_cost,
   case when s.n>0 then s.reimbursement when q.assigned_lots>0 and q.nonempty_lots=0 and q.unknown_lots=0 then 0 else null end standard_reimbursement,
   coalesce(a.ids,'[]'::jsonb)issue_item_ids,coalesce(s.ids,'[]'::jsonb)snapshot_ids,
   array_remove(array[
    case when q.unknown_lots>0 then 'INCOMPLETE_LOT_STANDARD'end,
    case when q.unallocated_lots>0 then 'UNALLOCATED_RECIPIENT'end,
    case when q.entitlement_unknown then 'ENTITLEMENT_MISMATCH'end,
    case when k.category_id is null or not coalesce(a.units_known,true)or not coalesce(s.units_known,true)then 'HISTORICAL_UNIT_UNKNOWN'end,
    case when coalesce(s.n,0)=0 and not(q.assigned_lots>0 and q.nonempty_lots=0 and q.unknown_lots=0)then 'NO_CATEGORY_STANDARD'end
   ],null)::text[]reasons
  from category_keys k left join erp.accessory_categories c on c.id=k.category_id cross join quality q
  left join lateral(select sum(i.qty)qty,sum(i.inventory_cost)cost,sum(i.total_receivable)receivable,
   bool_and(i.unit_known)units_known,bool_and(i.total_receivable is not null)receivables_known,
   jsonb_agg(i.id order by i.id)ids from issue_sources i where i.category_id is not distinct from k.category_id)a on true
  left join lateral(select count(*)n,sum(sn.good_qty_pcs*sn.qty_per_good_fg_base)qty,sum(sn.total_hpp_cost)cost,
   sum(sn.total_reimbursement)reimbursement,bool_and(sn.unit_known)units_known,jsonb_agg(sn.id order by sn.id)ids
   from standard_sources sn where sn.contractor_id=p_contractor and sn.category_id is not distinct from k.category_id)s on true
 )
select jsonb_build_object(
 'period_start',p_start,'period_end',p_end,'business_timezone','Asia/Jakarta','contractor_id',p_contractor,'po_filter',p_po,
 'definitions',jsonb_build_object('actual','POSTED_ISSUE_PHYSICAL_WIB','standard','ACCEPTED_GOOD_PRODUCED_WIB',
  'comparison','PERIOD_COHORTS_NOT_PO_WASTE','cost','NATIVE_EFFECTIVE_SNAPSHOTS_WITH_REVISIONS'),
 'counts',jsonb_build_object('issue_items',(select count(*)from issue_sources),'snapshots',(select count(*)from standard_sources),
  'lots',(select count(*)from lots),'unknown_lots',q.unknown_lots,'unallocated_lots',q.unallocated_lots,
  'issues_without_po',(select count(*)from issue_sources where po_id is null)),
 'status',case when q.unknown_lots>0 or q.entitlement_unknown
  or exists(select 1 from category_totals where cardinality(reasons)>0)then 'UNKNOWN'
  when q.assigned_lots=0 then 'NO_GOOD_OUTPUT'else 'KNOWN'end,
 'rows',coalesce((select jsonb_agg(jsonb_build_object('category_id',r.category_id,'category_name',coalesce(r.category_name,'Kategori belum diketahui'),
  'unit_reference',r.base_uom_code,'unit',case when 'HISTORICAL_UNIT_UNKNOWN'=any(r.reasons)then null else r.base_uom_code end,
  'actual_qty',r.actual_qty::text,'standard_qty',r.standard_qty::text,
  'delta_qty',case when cardinality(r.reasons)=0 then(r.actual_qty-r.standard_qty)::text else null end,
  'comparison_status',case when cardinality(r.reasons)=0 then 'KNOWN'else 'UNKNOWN'end,'reasons',to_jsonb(r.reasons),
  'actual_inventory_cost',r.actual_inventory_cost::text,'actual_receivable',r.actual_receivable::text,
  'standard_hpp_cost',r.standard_hpp_cost::text,'standard_reimbursement',r.standard_reimbursement::text,
  'issue_item_ids',r.issue_item_ids,'snapshot_ids',r.snapshot_ids)order by r.category_name nulls last,r.category_id nulls last)from category_totals r),'[]'),
 'actual_sources',coalesce((select jsonb_agg(jsonb_build_object('id',i.id,'issue_id',i.issue_id,'issue_number',i.issue_number,
  'po_id',i.po_id,'po_number',i.po_number,'physical_at',cp7_accessory_standard_report.iso(i.physical_at),'location_id',i.location_id,
  'material_id',i.material_id,'material_sku',i.material_sku,'material_name',i.material_name,'category_id',i.category_id,
  'qty',i.qty::text,'unit',case when i.unit_known then i.base_uom_code else null end,'unit_known',i.unit_known,
  'transaction_qty',i.transaction_qty::text,'transaction_uom',i.transaction_uom_code,'base_qty_per_transaction_uom',i.base_qty_per_transaction_uom::text,
  'inventory_unit_cost',i.unit_cost_snapshot::text,'inventory_cost',i.inventory_cost::text,'selling_unit_price',i.unit_sale_price_snapshot::text,'receivable',i.total_receivable::text,
  'accessory_price_version_id',i.accessory_price_version_id,'material_price_version_id',i.material_price_version_id,'movement_ids',i.movement_ids)
  order by i.physical_at,i.issue_id,i.id)from issue_sources i),'[]'),
 'standard_sources',coalesce((select jsonb_agg(jsonb_build_object('id',s.id,'lot_id',s.lot_id,'lot_number',s.lot_number,
  'po_id',s.po_id,'po_number',s.po_number,'product_id',s.product_id,'sku',s.sku,'produced_at',cp7_accessory_standard_report.iso(s.produced_at),
  'contractor_id',s.contractor_id,'recipient_basis',s.recipient_basis,'commitment_id',s.commitment_id,'rework_order_id',s.rework_order_id,'decision_id',s.decision_id,
  'bom_version_id',s.bom_version_id,'bom_item_id',s.bom_item_id,'category_id',s.category_id,'good_qty_pcs',s.good_qty_pcs::text,
  'qty_per_good_fg_base',s.qty_per_good_fg_base::text,'standard_qty',(s.good_qty_pcs*s.qty_per_good_fg_base)::text,
  'unit',case when s.unit_known then s.base_uom_code else null end,'unit_reference',s.base_uom_code,'unit_known',s.unit_known,'unit_basis_audit_ids',s.unit_basis_audit_ids,
  'hpp_method',s.hpp_method,'hpp_unit_cost',s.hpp_unit_cost_base_snapshot::text,'reimbursement_unit_rate',s.reimbursement_unit_rate_base_snapshot::text,
  'hpp_cost',s.total_hpp_cost::text,'reimbursement',s.total_reimbursement::text,
  'costing_basis_at',cp7_accessory_standard_report.iso(s.costing_basis_at),'costing_basis_source',s.costing_basis_source,
  'snapshotted_at',cp7_accessory_standard_report.iso(s.snapshotted_at),'entitlement_ids',s.entitlement_ids,
  'entitlement_known',coalesce(s.entitlement_known,false),'revisions',s.revisions)
  order by s.produced_at,s.lot_id,s.id)from standard_sources s),'[]'),
 'lot_sources',coalesce((select jsonb_agg(jsonb_build_object('id',l.id,'lot_number',l.lot_number,'po_id',l.po_id,'po_number',l.po_number,
  'product_id',l.product_id,'sku',l.sku,'produced_at',cp7_accessory_standard_report.iso(l.produced_at),'good_qty_pcs',l.initial_qty_pcs::text,
  'contractor_id',l.contractor_id,'recipient_basis',l.recipient_basis,'commitment_id',l.commitment_id,'committed_bom',l.committed_bom,
  'rework_order_id',l.rework_order_id,'decision_id',l.decision_id,'decision_state',l.decision_state,
  'expected_snapshot_count',case when l.rework_order_id is null then l.committed_item_count else l.selected_item_count end,
  'snapshot_count',l.snapshot_count,'explicit_zero',l.explicit_zero,'reasons',to_jsonb(l.reasons))order by l.produced_at,l.id)from lots l),'[]')
)from quality q $$;

create function cp7_accessory_standard_report.workspace(p_start date,p_end date,p_contractor uuid,p_po uuid,p_query text,p_offset integer,p_limit integer)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare v_access jsonb;v_result jsonb;v_report jsonb;v_total integer;v_contractors jsonb;v_pos jsonb;v_selected jsonb;v_q text;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_ACCESSORY_REPORT_FRESH_ACCESS_REQUIRED';end if;
 v_access:=cp7_accessory_standard_report.access_now();
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
 -- A second live permission read after the statement data read; no cached
 -- JWT metadata, no elevated browser/private grants and no stale answer.
 if cp7_accessory_standard_report.access_now()is distinct from v_access then
  raise exception using errcode='42501',message='CP7_ACCESSORY_REPORT_ACCESS_CHANGED: hak akses berubah; muat ulang.';end if;
 return v_result;
end $$;

alter function cp7_accessory_standard_report.iso(timestamptz)owner to postgres;
alter function cp7_accessory_standard_report.access_now()owner to postgres;
alter function cp7_accessory_standard_report.period_data(date,date,uuid,uuid)owner to postgres;
alter function cp7_accessory_standard_report.workspace(date,date,uuid,uuid,text,integer,integer)owner to postgres;
revoke all on all functions in schema cp7_accessory_standard_report from public,anon,authenticated,service_role,cp7_capture,cp7_accessory_standard_read;
grant execute on function cp7_accessory_standard_report.workspace(date,date,uuid,uuid,text,integer,integer)to cp7_accessory_standard_read;
create function public.erp_cp7_get_accessory_standard_report_v1(p_start date,p_end date,p_contractor uuid default null,p_po uuid default null,
 p_query text default '',p_offset integer default 0,p_limit integer default 30)returns jsonb
language sql volatile security definer set search_path=''as $$
 select cp7_accessory_standard_report.workspace(p_start,p_end,p_contractor,p_po,p_query,p_offset,p_limit)$$;
grant create on schema public to cp7_accessory_standard_read;
alter function public.erp_cp7_get_accessory_standard_report_v1(date,date,uuid,uuid,text,integer,integer)owner to cp7_accessory_standard_read;
set local role cp7_accessory_standard_read;
revoke all on function public.erp_cp7_get_accessory_standard_report_v1(date,date,uuid,uuid,text,integer,integer)from public,anon,service_role,cp7_capture,postgres;
grant execute on function public.erp_cp7_get_accessory_standard_report_v1(date,date,uuid,uuid,text,integer,integer)to authenticated;

reset role;
revoke create on schema public from cp7_accessory_standard_read;
set local role cp7_accessory_standard_read;
revoke create on schema cp7_accessory_standard_report from postgres;
reset role;
revoke cp7_accessory_standard_read from postgres granted by postgres restrict;
do $mandor_pre$ begin if exists(select from (values ('cp7_cutting_correction.sewing_revision(uuid,uuid,numeric,uuid,timestamp with time zone,uuid)','1838d87d2541f2ff93cd9a602bf20d3ee705290534db7c980fbbbf918831a9ff'),('erp.save_cutting_pickup_v1(jsonb,uuid,bigint)','902fddd480c649649ed58b8d5cb7a5fe550f91155cda34f35b0fb572242e689c')) as p(sig,sha) where encode(sha256(convert_to(pg_get_functiondef(to_regprocedure(p.sig)),'UTF8')),'hex') is distinct from p.sha) then raise exception 'Mandor correction predecessor differs'; end if; end $mandor_pre$;
-- OW05. A PO owns the Mandor identity. Posted wages/notes are never reassigned.
-- The operator first uses the named Native inverses in the workspace. This
-- command then replaces every current pickup, preserving its physical time,
-- quantities and old immutable allocations. Sewing is recorded again through
-- the existing writer with its explicit OLD/NEW rate choice (D16-2/3/4).
create schema cp7_contractor_correction authorization postgres;
revoke all on schema cp7_contractor_correction from public,anon,authenticated,service_role;

create table cp7_contractor_correction.requests_v1(
 actor uuid not null,request_id uuid not null,payload jsonb not null,response jsonb,
 primary key(actor,request_id)
);
create table cp7_contractor_correction.history_v1(
 actor uuid not null,request_id uuid not null,po_id uuid not null,
 old_contractor_id uuid not null,new_contractor_id uuid not null,
 source jsonb not null,result jsonb not null,reason text not null,
 recorded_at timestamptz not null default clock_timestamp(),
 generation_no bigint generated always as identity unique,primary key(actor,request_id)
);
-- No GUC, JWT claim, user-writable flag or durable row grants this capability.
create table cp7_contractor_correction.context_v1(
 backend_pid integer not null,transaction_id bigint not null,actor uuid not null,
 request_id uuid not null,po_id uuid not null,group_id uuid not null,
 primary key(backend_pid,transaction_id)
);
alter table cp7_contractor_correction.requests_v1 enable row level security;
alter table cp7_contractor_correction.history_v1 enable row level security;
alter table cp7_contractor_correction.context_v1 enable row level security;
create policy private_requests on cp7_contractor_correction.requests_v1 for all using(false)with check(false);
create policy private_history on cp7_contractor_correction.history_v1 for all using(false)with check(false);
create policy private_context on cp7_contractor_correction.context_v1 for all using(false)with check(false);
revoke all on all tables in schema cp7_contractor_correction from public,anon,authenticated,service_role,cp7_capture;
create trigger immutable_history before update or delete on cp7_contractor_correction.history_v1
 for each row execute function cp7_cutting_correction.immutable();
create trigger immutable_history_truncate before truncate on cp7_contractor_correction.history_v1
 for each statement execute function cp7_cutting_correction.immutable();

create function cp7_contractor_correction.access_now_v1()returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare v_pickup jsonb;v_sewing jsonb;
begin
 v_pickup:=cp7_cutting_correction.pickup_access_now();
 v_sewing:=cp7_cutting_correction.sewing_access_now(true);
 if erp.has_permission('production.distribution.create')is distinct from true then
  raise exception using errcode='42501',message='CP7_MANDOR_CORRECTION_DENIED';end if;
 if v_pickup is distinct from v_sewing then
  raise exception using errcode='42501',message='CP7_MANDOR_CORRECTION_ACCESS_CHANGED';end if;
 return v_pickup;
end $$;

-- All correction commands hold the same global envelope before allocating the
-- identity. Thus generation order is commit order (rolled-back gaps are fine),
-- unlike arbitrary sequence allocation by unrelated concurrent transactions.
-- A generation is an assignment, never a new physical date or a changed rate.
create function cp7_contractor_correction.generation_v1(p_po uuid)returns uuid
language plpgsql stable security definer set search_path=''as $$
declare v_history cp7_contractor_correction.history_v1;v_contractor uuid;
begin
 select *into v_history from cp7_contractor_correction.history_v1 hh where hh.po_id=p_po
  order by hh.generation_no desc limit 1;
 if not found then return null;end if;
 select po.contractor_id into v_contractor from erp.production_orders po where po.id=p_po;
 if v_history.new_contractor_id is distinct from v_contractor then
  raise exception 'CP7_MANDOR_CORRECTION_GENERATION_CHANGED';end if;
 return md5(v_history.actor::text||':'||v_history.request_id::text)::uuid;
end $$;

-- A known append-only Laundry WIP original needs its own exact Native inverse;
-- unrelated inflows, a net-zero sum, or a matching amount alone are insufficient.
create function cp7_contractor_correction.wip_closed_v1(p_po uuid)returns boolean
language sql stable security definer set search_path=''as $$
 select not exists(
  select 1 from erp.wip_stage_events w where w.po_id=p_po and not(
   (w.source_type in('LAUNDRY_DELIVERY_LINE','LAUNDRY_RECEIPT_LINE','CP6_LAUNDRY_BS_SIZE_LINE')
    and(select count(*)from erp.wip_stage_events rv where rv.source_id=w.id
     and rv.source_type=case w.source_type
      when'LAUNDRY_DELIVERY_LINE'then'CP6_LAUNDRY_DELIVERY_WIP_REVERSAL'
      when'LAUNDRY_RECEIPT_LINE'then'CP6_LAUNDRY_RECEIPT_WIP_REVERSAL'
      else'CP6_LAUNDRY_BS_WIP_REVERSAL'end
     and rv.po_id=w.po_id and rv.cutting_group_id is not distinct from w.cutting_group_id
     and rv.contractor_id is not distinct from w.contractor_id
     and rv.stage_from=w.stage_to and rv.stage_to=w.stage_from and rv.qty_pcs=w.qty_pcs)=1)
   or(w.source_type in('CP6_LAUNDRY_DELIVERY_WIP_REVERSAL','CP6_LAUNDRY_RECEIPT_WIP_REVERSAL','CP6_LAUNDRY_BS_WIP_REVERSAL')
    and exists(select 1 from erp.wip_stage_events orig where orig.id=w.source_id and orig.po_id=w.po_id
     and orig.cutting_group_id is not distinct from w.cutting_group_id
     and orig.contractor_id is not distinct from w.contractor_id
     and orig.stage_from=w.stage_to and orig.stage_to=w.stage_from and orig.qty_pcs=w.qty_pcs
     and w.source_type=case orig.source_type
      when'LAUNDRY_DELIVERY_LINE'then'CP6_LAUNDRY_DELIVERY_WIP_REVERSAL'
      when'LAUNDRY_RECEIPT_LINE'then'CP6_LAUNDRY_RECEIPT_WIP_REVERSAL'
      when'CP6_LAUNDRY_BS_SIZE_LINE'then'CP6_LAUNDRY_BS_WIP_REVERSAL'else''end))
  ))
$$;

create function cp7_contractor_correction.blockers_v1(p_po uuid)returns jsonb
language sql stable security definer set search_path=''as $$
 select coalesce(jsonb_agg(d.item order by(d.item->>'order')::integer,d.item->>'id'),'[]')from(
  select jsonb_build_object('order',10,'kind','PO_STATE','id',po.id,'number',po.po_number,
   'status',po.status,'step','Buka kembali PO selesai atau selesaikan status tahan/batal melalui layar PO.')item
   from erp.production_orders po where po.id=p_po and po.status in('FINISHED','ON_HOLD','CANCELLED')
  union all select jsonb_build_object('order',10,'kind','PICKUP_SOURCE','id',po.id,
   'step','Koreksi ini memerlukan mandor PO dan pembagian yang sudah diposting dengan mandor yang sama. Periksa riwayat Bagi Potongan.')
   from erp.production_orders po where po.id=p_po and(po.contractor_id is null
    or not exists(select 1 from erp.cutting_pickups pk join erp.cutting_groups cg on cg.id=pk.cutting_group_id
     where cg.po_id=po.id and pk.status='POSTED')
    or exists(select 1 from erp.cutting_pickups pk join erp.cutting_groups cg on cg.id=pk.cutting_group_id
     where cg.po_id=po.id and pk.status='POSTED'and pk.contractor_id is distinct from po.contractor_id))
  union all select jsonb_build_object('order',20,'kind','PAYROLL','id',ps.id,'number',ps.payroll_number,'status',ps.status,
   'step',case when ps.status='PAID'then'Balik pembayaran dan nota melalui layar Nota/Gaji; uang keluar lama tidak dipindahkan ke mandor baru.'
    else'Batalkan nota/gaji yang belum dibayar melalui layar Nota/Gaji.'end)
   from erp.payroll_settlements ps where ps.status<>'REVERSED'and(
    exists(select 1 from erp.payroll_work_items wi where wi.payroll_id=ps.id and wi.po_id=p_po)
    or exists(select 1 from erp.payroll_reimbursements ri where ri.payroll_id=ps.id and ri.po_id=p_po))
  union all select jsonb_build_object('order',15,'kind','ATTENDANCE_POOL','id',ap.id,'number',ap.pool_number,
   'step','Batalkan pool HPP absen yang memakai hasil jahit ini melalui layar Pool HPP.')
   from erp.attendance_hpp_pools ap where ap.status='ACTIVE'and exists(
    select 1 from erp.attendance_hpp_pool_allocations aa where aa.pool_id=ap.id and aa.po_id=p_po)
  union all select distinct jsonb_build_object('order',15,'kind','POCKET_POOL','id',pd.pool_id,
   'step','Batalkan pembagian kain kantong yang memakai PO ini melalui layar Kain Kantong.')
   from erp.pocket_period_destinations pd where pd.po_id=p_po and erp.pocket_period_active_v1(pd.pool_id)
  union all select jsonb_build_object('order',40,'kind','QC','id',qh.id,'number',qh.inspection_number,'status',qh.status,
   'step','Balik QC dan pemakaian barang jadinya dari dokumen paling akhir; hapus draft QC yang belum diposting.')
   from erp.qc_inspections qh where qh.po_id=p_po and qh.status<>'REVERSED'
  union all select jsonb_build_object('order',40,'kind','FG_LOT','id',fl.id,'number',fl.lot_number,
   'step','Balik pemakaian barang jadi lalu QC asalnya; lot harus dibatalkan dan stoknya kembali nol.')
   from erp.fg_lots fl where fl.po_id=p_po and(fl.lot_origin<>'VOIDED_PRODUCTION'
    or exists(select 1 from erp.fg_stock_movements fm where fm.lot_id=fl.id group by fm.lot_id having sum(fm.qty_signed)<>0))
  union all select jsonb_build_object('order',50,'kind','LAUNDRY','id',ld.id,'number',ld.delivery_number,'status',ld.status,
   'step','Balik penerimaan/cuci dan kirim laundry dari dokumen paling akhir; hapus draft yang masih mengikat potongan.')
   from erp.laundry_deliveries ld where ld.po_id=p_po and ld.status<>'REVERSED'
  union all select jsonb_build_object('order',60,'kind','SEWING','id',st.id,'number',st.event_number,
   'step','Batalkan hasil Selesai Dijahit dari layar WIP & Jahit; upah/jurnal dibalik melalui penulis yang sama.')
   from erp.sewing_terminal_events st where st.po_id=p_po and st.event_kind='SELESAI_DIJAHIT'
    and not exists(select 1 from erp.sewing_terminal_events rv where rv.reversal_of_id=st.id)
  union all select jsonb_build_object('order',65,'kind','WORK','id',we.id,'number',we.completion_number,'status',we.status,
   'step','Balik hasil kerja/upah melalui layar WIP & Jahit; hapus draft hasil kerja. Riwayat lama tetap tersimpan.')
   from erp.work_completion_events we where we.po_id=p_po and we.status<>'REVERSED'
  union all select jsonb_build_object('order',66,'kind','WORK_JOURNAL','id',je.id,'number',je.journal_number,
   'step','Selesaikan pembalikan upah dari dokumen hasil kerja asalnya; jurnal tidak boleh dibalik terpisah.')
   from erp.journal_entries je join erp.work_completion_events we on we.id=je.source_id
   where we.po_id=p_po and je.source_type='WORK_COMPLETION'and je.status='POSTED'
  union all select jsonb_build_object('order',70,'kind','ACCESSORY_NOTE','id',ae.id,'status',ae.payroll_status,
   'step','Balik nota/pembayaran lalu dokumen aksesori atau QC asal hak tagih; hak mandor lama harus berstatus dibatalkan.')
   from erp.contractor_accessory_reimbursement_entitlements ae where ae.po_id=p_po and ae.payroll_status<>'CANCELLED'
  union all select jsonb_build_object('order',70,'kind','MATERIAL_ISSUE','id',mi.id,'number',mi.issue_number,'status',mi.status,
   'step','Balik pengeluaran bahan ke mandor atau hapus draftnya dari layar Bahan Mandor.')
   from erp.contractor_material_issues mi where mi.po_id=p_po and mi.status<>'REVERSED'
  union all select jsonb_build_object('order',70,'kind','REWORK','id',ro.id,'number',ro.rework_number,'status',ro.status,
   'step','Balik hasil/perjalanan rework lalu batalkan order rework yang terkait PO ini.')
   from erp.rework_orders ro join erp.bs_cases bc on bc.id=ro.bs_case_id where bc.po_id=p_po and ro.status<>'CANCELLED'
  union all select jsonb_build_object('order',70,'kind','BS','id',bc.id,'number',bc.bs_number,'status',bc.status,
   'step','Selesaikan pembalikan dokumen terkait dan batalkan kasus BS melalui layar BS.')
   from erp.bs_cases bc where bc.po_id=p_po and bc.status<>'CANCELLED'
  union all select jsonb_build_object('order',70,'kind','SCRAP','id',sb.id,'number',sb.scrap_number,'status',sb.status,
   'step','Balik atau batalkan dokumen scrap yang masih mengikat potongan PO ini.')
   from erp.scrap_batches sb join erp.cutting_groups cg on cg.id=sb.source_cutting_group_id
   where cg.po_id=p_po and sb.status<>'CANCELLED'
  union all select jsonb_build_object('order',80,'kind','PICKUP_DRAFT','id',pk.id,
   'step','Hapus draft Bagi Potongan terlebih dahulu; koreksi akan mengganti semua pembagian yang sudah diposting dalam PO.')
   from erp.cutting_pickups pk join erp.cutting_groups cg on cg.id=pk.cutting_group_id where cg.po_id=p_po and pk.status='DRAFT'
  union all select jsonb_build_object('order',80,'kind','GROUP_STATE','id',cg.id,'number',cg.group_number,'status',cg.status,
   'step','Selesaikan pembalikan proses lanjutan sampai potongan kembali ke status sudah diambil atau menunggu dibagi.')
   from erp.cutting_groups cg where cg.po_id=p_po and(cg.status not in('CUT','PICKED_UP')
    or(cg.status='PICKED_UP'and not exists(select 1 from erp.cutting_pickups pk where pk.cutting_group_id=cg.id and pk.status='POSTED')))
  union all select jsonb_build_object('order',90,'kind','WIP_HISTORY','id',p_po,
   'step','Riwayat perpindahan WIP belum memiliki pasangan pembalikan Native yang lengkap; balik dokumen sumbernya.')
   where not cp7_contractor_correction.wip_closed_v1(p_po)
 )d
$$;

-- A correction of assignment must have zero financial/stock/HPP effect of its
-- own. Native inverses and subsequent sewing own those effects, separately.
create function cp7_contractor_correction.financial_fingerprint_v1(p_po uuid)returns text
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select md5(jsonb_build_object(
  'journal_lines',coalesce((select jsonb_agg(to_jsonb(jl)order by jl.id)from erp.journal_lines jl where jl.po_id=p_po),'[]'),
  'journals',coalesce((select jsonb_agg(to_jsonb(je)order by je.id)from erp.journal_entries je where exists(
   select 1 from erp.journal_lines jl where jl.journal_entry_id=je.id and jl.po_id=p_po)),'[]'),
  'fg_lots',coalesce((select jsonb_agg(to_jsonb(fl)order by fl.id)from erp.fg_lots fl where fl.po_id=p_po),'[]'),
  'fg_movements',coalesce((select jsonb_agg(to_jsonb(fm)order by fm.id)from erp.fg_stock_movements fm
   join erp.fg_lots fl on fl.id=fm.lot_id where fl.po_id=p_po),'[]'),
  'hpp_versions',coalesce((select jsonb_agg(to_jsonb(hv)order by hv.id)from erp.hpp_versions hv
   join erp.fg_lots fl on fl.id=hv.lot_id where fl.po_id=p_po),'[]'),
  'hpp_components',coalesce((select jsonb_agg(to_jsonb(hc)order by hc.id)from erp.hpp_version_components hc
   join erp.hpp_versions hv on hv.id=hc.hpp_version_id join erp.fg_lots fl on fl.id=hv.lot_id where fl.po_id=p_po),'[]'),
  'hpp_gl',coalesce((select jsonb_agg(to_jsonb(hg)order by hg.po_id)from erp.po_hpp_gl_state hg where hg.po_id=p_po),'[]'),
  'hpp_gl_events',coalesce((select jsonb_agg(to_jsonb(he)order by he.id)from erp.po_hpp_gl_events he where he.po_id=p_po),'[]'),
  'material_movements',coalesce((select jsonb_agg(to_jsonb(mm)order by mm.id)from erp.material_stock_movements mm where
   mm.roll_id in(select cr.roll_id from erp.cutting_group_rolls cr join erp.cutting_groups cg on cg.id=cr.cutting_group_id where cg.po_id=p_po)
   or mm.source_id in(select cg.id from erp.cutting_groups cg where cg.po_id=p_po)
   or mm.source_id in(select mi.id from erp.contractor_material_issues mi where mi.po_id=p_po)),'[]'),
  'entitlements',coalesce((select jsonb_agg(to_jsonb(ae)order by ae.id)from erp.contractor_accessory_reimbursement_entitlements ae where ae.po_id=p_po),'[]'),
  'payroll_work',coalesce((select jsonb_agg(to_jsonb(wi)order by wi.id)from erp.payroll_work_items wi where wi.po_id=p_po),'[]'),
  'payroll_reimbursements',coalesce((select jsonb_agg(to_jsonb(ri)order by ri.id)from erp.payroll_reimbursements ri where ri.po_id=p_po),'[]')
 )::text)
$$;

-- Full relevant facts are bound to the review, including closed old documents.
create function cp7_contractor_correction.snapshot_v1(p_po uuid)returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('po',to_jsonb(po),'groups',
  coalesce((select jsonb_agg(to_jsonb(cg)order by cg.id)from erp.cutting_groups cg where cg.po_id=po.id),'[]'),
  'pickups',coalesce((select jsonb_agg(to_jsonb(pk)order by pk.id)from erp.cutting_pickups pk
   join erp.cutting_groups cg on cg.id=pk.cutting_group_id where cg.po_id=po.id),'[]'),
  'batches',coalesce((select jsonb_agg(to_jsonb(bt)order by bt.id)from erp.cutting_distribution_batches bt
   join erp.cutting_pickups pk on pk.id=bt.pickup_id join erp.cutting_groups cg on cg.id=pk.cutting_group_id where cg.po_id=po.id),'[]'),
  'allocations',coalesce((select jsonb_agg(to_jsonb(al)order by al.id)from erp.cutting_distribution_allocations al
   join erp.cutting_distribution_batches bt on bt.id=al.batch_id join erp.cutting_pickups pk on pk.id=bt.pickup_id
   join erp.cutting_groups cg on cg.id=pk.cutting_group_id where cg.po_id=po.id),'[]'),
  'work',coalesce((select jsonb_agg(to_jsonb(we)order by we.id)from erp.work_completion_events we where we.po_id=po.id),'[]'),
  'work_lines',coalesce((select jsonb_agg(to_jsonb(wl)order by wl.id)from erp.work_completion_lines wl
   join erp.work_completion_events we on we.id=wl.completion_id where we.po_id=po.id),'[]'),
  'work_snapshots',coalesce((select jsonb_agg(to_jsonb(ws)order by ws.id)from erp.po_work_component_snapshots ws where ws.po_id=po.id),'[]'),
  'financial_fingerprint',cp7_contractor_correction.financial_fingerprint_v1(po.id),
  'blockers',cp7_contractor_correction.blockers_v1(po.id),
  'contractors',coalesce((select jsonb_agg(to_jsonb(ct)order by ct.id)from erp.contractors ct
   where ct.contractor_type='MANDOR'and ct.is_active),'[]'),
  'closed_through',(select ac.closed_through from erp.accounting_period_control ac where ac.singleton_id=1))
 from erp.production_orders po where po.id=p_po
$$;

create function cp7_contractor_correction.admitted_group_v1(p_group uuid)returns boolean
language sql stable security definer set search_path=''as $$
 select exists(select 1 from cp7_contractor_correction.context_v1 cx
  join erp.cutting_groups cg on cg.id=cx.group_id and cg.po_id=cx.po_id
  where cx.backend_pid=pg_backend_pid()and cx.transaction_id=txid_current()and cx.actor=auth.uid()
   and cx.group_id=p_group
   and exists(select 1 from cp7_contractor_correction.requests_v1 rq
    where rq.actor=cx.actor and rq.request_id=cx.request_id and rq.response is null))
$$;

create function cp7_contractor_correction.workspace_v1(p_po uuid)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare v_access jsonb;v_source jsonb;
begin
 v_access:=cp7_contractor_correction.access_now_v1();
 v_source:=cp7_contractor_correction.snapshot_v1(p_po);
 if v_source is null then raise exception 'CP7_MANDOR_CORRECTION_NOT_FOUND';end if;
 if cp7_contractor_correction.access_now_v1()is distinct from v_access then
  raise exception using errcode='42501',message='CP7_MANDOR_CORRECTION_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.mandor-correction-workspace.v1','po_id',p_po,
  'po_number',v_source->'po'->>'po_number','contractor_id',v_source->'po'->>'contractor_id',
  'contractors',(select coalesce(jsonb_agg(jsonb_build_object('id',ct->>'id','name',ct->>'contractor_name')order by ct->>'contractor_name',ct->>'id'),'[]')
    from jsonb_array_elements(v_source->'contractors')ct),
  'group_count',jsonb_array_length(v_source->'groups'),
  'pickup_count',(select count(*)from jsonb_array_elements(v_source->'pickups')pk where pk->>'status'='POSTED'),
  'blockers',v_source->'blockers','eligible',jsonb_array_length(v_source->'blockers')=0,
  'review_token',md5(v_source::text),'closed_through',v_source->'closed_through',
  'after_step','Catat ulang hasil jahit untuk mandor yang benar dari WIP & Jahit. Periksa pilihan tarif PO lama atau tarif mandor baru pada waktu jahit asli; buat ulang nota hanya sesudah hasilnya benar.',
  'business_DML',false);
end $$;

create function cp7_contractor_correction.command_v1(p jsonb,p_request uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare v_access jsonb;v_old cp7_contractor_correction.requests_v1;v_po erp.production_orders;
 v_source jsonb;v_actor uuid;v_target uuid;v_group erp.cutting_groups;v_pickup erp.cutting_pickups;
 v_batches jsonb;v_result jsonb;v_replacements jsonb:='[]';v_response jsonb;v_check jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 v_access:=cp7_contractor_correction.access_now_v1();
 if p_request is null or jsonb_typeof(p)is distinct from'object'or not(p?&array['po_id','contractor_id','review_token','change_reason'])
  or(select count(*)from jsonb_object_keys(p))<>4
  or jsonb_typeof(p->'po_id')is distinct from'string'or coalesce(p->>'po_id','')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or jsonb_typeof(p->'contractor_id')is distinct from'string'or coalesce(p->>'contractor_id','')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or jsonb_typeof(p->'review_token')is distinct from'string'or coalesce(p->>'review_token','')!~'^[0-9a-f]{32}$'
  or jsonb_typeof(p->'change_reason')is distinct from'string'or length(btrim(p->>'change_reason'))not between 5 and 1000 then
  raise exception 'CP7_MANDOR_CORRECTION_FIELDS';end if;
 -- All source writers share this financial envelope; refresh rights after waits.
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 if cp7_contractor_correction.access_now_v1()is distinct from v_access then
  raise exception using errcode='42501',message='CP7_MANDOR_CORRECTION_ACCESS_CHANGED';end if;
 insert into cp7_contractor_correction.requests_v1 values(auth.uid(),p_request,p,null)on conflict do nothing;
 select *into strict v_old from cp7_contractor_correction.requests_v1 rq where rq.actor=auth.uid()and rq.request_id=p_request for update;
 if v_old.payload is distinct from p then raise exception 'CP7_MANDOR_CORRECTION_REQUEST_CHANGED';end if;
 if v_old.response is not null then return v_old.response;end if;
 -- Legacy sewing takes flow/rows before its Native financial writer. Never
 -- wait for those while holding the global envelope: refuse atomically so
 -- that writer can finish and the operator can obtain a fresh review.
 for v_group in select *from erp.cutting_groups cg where cg.po_id=(p->>'po_id')::uuid order by cg.id loop
  if not pg_try_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group.id::text,0))then
   raise exception using errcode='55P03',message='CP7_MANDOR_CORRECTION_BUSY';end if;end loop;
 perform 1 from erp.cutting_groups cg where cg.po_id=(p->>'po_id')::uuid order by cg.id for update nowait;
 select *into v_po from erp.production_orders po where po.id=(p->>'po_id')::uuid for update nowait;
 if v_po.id is null then raise exception 'CP7_MANDOR_CORRECTION_NOT_FOUND';end if;
 perform 1 from erp.cutting_pickups pk join erp.cutting_groups cg on cg.id=pk.cutting_group_id
  where cg.po_id=v_po.id order by pk.id for update of pk nowait;
 if cp7_contractor_correction.access_now_v1()is distinct from v_access then
  raise exception using errcode='42501',message='CP7_MANDOR_CORRECTION_ACCESS_CHANGED';end if;
 v_source:=cp7_contractor_correction.snapshot_v1(v_po.id);
 if md5(v_source::text)is distinct from p->>'review_token'then raise exception 'CP7_MANDOR_CORRECTION_STALE_REVIEW';end if;
 if jsonb_array_length(v_source->'blockers')<>0 then raise exception 'CP7_MANDOR_CORRECTION_DEPENDENCIES: %',v_source->'blockers';end if;
 v_target:=(p->>'contractor_id')::uuid;
 if v_po.contractor_id is null or v_po.contractor_id=v_target or not exists(select 1 from erp.contractors ct
  where ct.id=v_target and ct.is_active and ct.contractor_type='MANDOR')then raise exception 'CP7_MANDOR_CORRECTION_TARGET';end if;
 if not exists(select 1 from erp.cutting_groups cg join erp.cutting_pickups pk on pk.cutting_group_id=cg.id
  where cg.po_id=v_po.id and pk.status='POSTED')or exists(select 1 from erp.cutting_groups cg
  join erp.cutting_pickups pk on pk.cutting_group_id=cg.id where cg.po_id=v_po.id and pk.status='POSTED'and pk.contractor_id<>v_po.contractor_id)then
  raise exception 'CP7_MANDOR_CORRECTION_PICKUP_SOURCE';end if;
 v_actor:=erp.current_app_user_id();if v_actor is null then raise exception using errcode='42501',message='CP7_MANDOR_CORRECTION_DENIED';end if;
 perform set_config('app.change_reason',btrim(p->>'change_reason'),true);
 perform erp._cp3_lock_business_date((statement_timestamp()at time zone'Asia/Jakarta')::date);
 update erp.production_orders set contractor_id=v_target,updated_at=clock_timestamp()where id=v_po.id;
 for v_pickup in select pk.*from erp.cutting_pickups pk join erp.cutting_groups cg on cg.id=pk.cutting_group_id
  where cg.po_id=v_po.id and pk.status='POSTED'order by pk.cutting_group_id loop
  select *into strict v_group from erp.cutting_groups cg where cg.id=v_pickup.cutting_group_id;
  select jsonb_agg(jsonb_build_object('batch_no',bt.batch_no,'notes',bt.notes,'allocations',
   (select jsonb_agg(jsonb_build_object('cutting_roll_yield_id',al.cutting_roll_yield_id,'qty_pcs',al.qty_pcs)order by al.id)
    from erp.cutting_distribution_allocations al where al.batch_id=bt.id))order by bt.batch_no,bt.id)
   into v_batches from erp.cutting_distribution_batches bt where bt.pickup_id=v_pickup.id;
  insert into cp7_contractor_correction.context_v1 values(pg_backend_pid(),txid_current(),auth.uid(),p_request,v_po.id,v_group.id);
  insert into cp7_cutting_correction.pickup_context values(pg_backend_pid(),txid_current(),auth.uid(),v_pickup.id,v_group.id);
  update erp.cutting_pickups set status='REVERSED',reversed_by=v_actor,reversed_at=clock_timestamp(),
   reversal_reason=btrim(p->>'change_reason'),updated_at=clock_timestamp()where id=v_pickup.id;
  update erp.cutting_groups set picked_up_at=null,status='CUT',updated_at=clock_timestamp()where id=v_group.id;
  select *into strict v_group from erp.cutting_groups cg where cg.id=v_group.id;
  v_result:=erp.save_cutting_pickup_v1(jsonb_build_object('cutting_group_id',v_group.id,'contractor_id',v_target,
   'picked_up_at',v_pickup.picked_up_at,'allocation_mode',v_pickup.allocation_mode,'action','POST',
   'change_reason',btrim(p->>'change_reason'),'expected_group_version',v_group.row_version,
   'notes',v_pickup.notes,'batches',v_batches),md5('OW05:'||auth.uid()::text||':'||p_request::text||':'||v_group.id::text)::uuid,null);
  v_replacements:=v_replacements||jsonb_build_array(jsonb_build_object('group_id',v_group.id,'old_pickup_id',v_pickup.id,
   'new_pickup_id',v_result->>'pickup_id','picked_up_at',v_pickup.picked_up_at,'allocated_pieces',v_result->'allocated_pieces'));
  delete from cp7_cutting_correction.pickup_context pc where pc.backend_pid=pg_backend_pid()and pc.transaction_id=txid_current();
  delete from cp7_contractor_correction.context_v1 cx where cx.backend_pid=pg_backend_pid()and cx.transaction_id=txid_current();
 end loop;
 v_check:=cp7_contractor_correction.snapshot_v1(v_po.id);
 if v_check->'work'is distinct from v_source->'work'or v_check->'work_lines'is distinct from v_source->'work_lines'
  or v_check->'work_snapshots'is distinct from v_source->'work_snapshots'
  or v_check->>'financial_fingerprint'is distinct from v_source->>'financial_fingerprint'
  or v_check->'po'->>'contractor_id'is distinct from v_target::text or jsonb_array_length(v_check->'blockers')<>0 then
  raise exception 'CP7_MANDOR_CORRECTION_INCOMPLETE';end if;
 if cp7_contractor_correction.access_now_v1()is distinct from v_access then
  raise exception using errcode='42501',message='CP7_MANDOR_CORRECTION_ACCESS_CHANGED';end if;
 v_response:=jsonb_build_object('contract_version','cp7.mandor-correction-result.v1','po_id',v_po.id,'po_number',v_po.po_number,
  'old_contractor_id',v_po.contractor_id,'contractor_id',v_target,'request_id',p_request,'status','PICKUPS_REPLACED',
  'replacements',v_replacements,'sewing_repost_required',true,'wage_history_reassigned',false);
 insert into cp7_contractor_correction.history_v1(actor,request_id,po_id,old_contractor_id,new_contractor_id,source,result,reason,recorded_at)
 values(auth.uid(),p_request,v_po.id,v_po.contractor_id,v_target,
  v_source,v_response,btrim(p->>'change_reason'),clock_timestamp());
 update cp7_contractor_correction.requests_v1 rq set response=v_response where rq.actor=auth.uid()and rq.request_id=p_request;
 return v_response;
end $$;

create function public.erp_cp7_get_mandor_correction_v1(p_po uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_contractor_correction.workspace_v1(p_po)$$;
create function public.erp_cp7_correct_mandor_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_contractor_correction.command_v1(p_payload,p_request)$$;
revoke all on all functions in schema cp7_contractor_correction from public,anon,authenticated,service_role,cp7_capture;
revoke all on function public.erp_cp7_get_mandor_correction_v1(uuid),public.erp_cp7_correct_mandor_v1(jsonb,uuid)
 from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_mandor_correction_v1(uuid),public.erp_cp7_correct_mandor_v1(jsonb,uuid)to authenticated;

grant cp7_cutting_read to postgres with inherit false,set true granted by postgres;
set local role cp7_cutting_read;
grant create on schema cp7_cutting_correction to postgres;
reset role;
alter table cp7_cutting_correction.rate_revisions add column mandor_generation uuid;
alter table cp7_cutting_correction.rate_revisions drop constraint rate_revisions_original_snapshot_id_basis_at_key;
alter table cp7_cutting_correction.rate_revisions add constraint rate_revisions_original_snapshot_id_basis_at_key UNIQUE NULLS NOT DISTINCT (original_snapshot_id, basis_at, mandor_generation);
CREATE OR REPLACE FUNCTION erp.save_cutting_pickup_v1(p_payload jsonb, p_client_request_id uuid, p_expected_version bigint DEFAULT NULL::bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
  v_id uuid:=nullif(p_payload->>'id','')::uuid;
  v_group_id uuid:=nullif(p_payload->>'cutting_group_id','')::uuid;
  v_contractor_id uuid:=nullif(p_payload->>'contractor_id','')::uuid;
  v_picked_up_at timestamptz:=nullif(p_payload->>'picked_up_at','')::timestamptz;
  v_mode text:=upper(coalesce(nullif(btrim(p_payload->>'allocation_mode'),''),'ROLL'));
  v_action text:=upper(coalesce(nullif(btrim(p_payload->>'action'),''),'SAVE_DRAFT'));
  v_reason text:=nullif(btrim(p_payload->>'change_reason'),'');
  v_expected_group_version bigint:=nullif(p_payload->>'expected_group_version','')::bigint;
  v_hash text;v_cached jsonb;v_response jsonb;
  v_pickup erp.cutting_pickups%rowtype;
  v_group erp.cutting_groups%rowtype;
  v_batch jsonb;v_allocation jsonb;v_batch_id uuid;
  v_actor uuid:=erp.current_app_user_id();
  v_po_contractor_id uuid;
  v_batch_count integer;v_max_batch integer;
begin
  if v_action in ('REVERSE_BATCH','REDISTRIBUTE_BATCH') then
    return erp.cp8_save_wip_batch_v1(v_action,p_payload,p_client_request_id,p_expected_version);
  end if;
  if v_action='SAVE' then v_action:='SAVE_DRAFT'; end if;
  if v_action not in ('SAVE_DRAFT','POST','DELETE') then raise exception 'Invalid pickup action'; end if;
  if v_reason is null then raise exception 'change_reason is required'; end if;
  if v_id is null then
    perform erp.require_permission('production.distribution.create');
    if p_expected_version is not null then raise exception 'expected_version must be null when creating pickup'; end if;
  else
    perform erp.require_permission('production.distribution.edit_draft');
    if p_expected_version is null then raise exception 'expected_version is required for an existing pickup'; end if;
  end if;
  if v_action='POST' then perform erp.require_permission('production.distribution.post'); end if;
  if v_expected_group_version is null then raise exception 'expected_group_version is required'; end if;

  v_hash:=erp._request_hash(jsonb_build_object('payload',p_payload,'expected_version',p_expected_version));
  v_cached:=erp._idempotency_begin('save_cutting_pickup_v1',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  perform set_config('app.change_reason',v_reason,true);

  if v_id is not null then
    select * into v_pickup from erp.cutting_pickups where id=v_id for update;
    if v_pickup.id is null then raise exception 'Cutting pickup not found'; end if;
    if v_pickup.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_pickup.row_version;
    end if;
    if v_pickup.status<>'DRAFT' then
      raise exception using errcode='42501',message='POSTED_CUTTING_PICKUP_IS_IMMUTABLE';
    end if;
    if v_group_id is null then v_group_id:=v_pickup.cutting_group_id; end if;
    if v_group_id is distinct from v_pickup.cutting_group_id then
      raise exception using errcode='42501',message='CUTTING_PICKUP_SOURCE_IS_IMMUTABLE';
    end if;
    if v_action='DELETE' then
      select * into v_group from erp.cutting_groups where id=v_group_id for update;
      if v_group.row_version<>v_expected_group_version then
        raise exception 'STALE_GROUP_VERSION expected %, current %',v_expected_group_version,v_group.row_version;
      end if;
      perform set_config('app.cutting_pickup_delete','on',true);
      delete from erp.cutting_pickups where id=v_pickup.id;
      v_response:=jsonb_build_object(
        'pickup_id',v_pickup.id,'cutting_group_id',v_group.id,'status','DELETED',
        'row_version',v_pickup.row_version,'group_row_version',v_group.row_version,
        'picked_up_at',v_pickup.picked_up_at,'contractor_id',v_pickup.contractor_id,
        'allocation_mode',v_pickup.allocation_mode,'batch_count',0,'allocated_pieces',0
      );
      return erp._idempotency_complete('save_cutting_pickup_v1',p_client_request_id,v_response);
    end if;
  elsif v_action='DELETE' then
    raise exception 'pickup id is required for DELETE';
  end if;

  select * into v_group from erp.cutting_groups where id=v_group_id for update;
  if v_group.id is null then raise exception 'Potongan not found'; end if;
  if v_group.row_version<>v_expected_group_version then
    raise exception 'STALE_GROUP_VERSION expected %, current %',v_expected_group_version,v_group.row_version;
  end if;
  if not v_group.material_issue_posted or v_group.pattern_id is null
     or v_group.source_location_id is null then
    raise exception using errcode='23514',message='PICKUP_REQUIRES_POSTED_PATTERN_BOUND_CUTTING';
  end if;
  if v_group.status<>'CUT' or v_group.picked_up_at is not null
     or (erp.cutting_group_has_downstream_after_pickup(v_group.id)
         and not cp7_contractor_correction.admitted_group_v1(v_group.id)) then
    raise exception using errcode='23514',message='PICKUP_REQUIRES_WAITING_CUTTING_WITHOUT_DOWNSTREAM';
  end if;
  if v_contractor_id is null or not exists(
    select 1 from erp.contractors c
    where c.id=v_contractor_id and c.is_active and c.contractor_type='MANDOR'
  ) then raise exception 'Active Mandor is required'; end if;
  if v_picked_up_at is null or v_picked_up_at<v_group.cut_at
     or v_picked_up_at>clock_timestamp()+interval '5 minutes' then
    raise exception 'picked_up_at must be between cut_at and now';
  end if;
  if v_mode not in ('ROLL','SIZE') then raise exception 'allocation_mode must be ROLL or SIZE'; end if;
  if jsonb_typeof(p_payload->'batches') is distinct from 'array'
     or jsonb_array_length(p_payload->'batches')=0 then
    raise exception 'batches must be a non-empty array';
  end if;

  -- The existing downstream cost/payroll model owns Mandor at PO level.
  -- Lock that identity before composing a pickup, and never silently move an
  -- already assigned PO to another Mandor.
  select po.contractor_id into v_po_contractor_id
  from erp.production_orders po where po.id=v_group.po_id for update;
  if v_po_contractor_id is not null
     and v_po_contractor_id is distinct from v_contractor_id then
    raise exception using errcode='23514',message='PO_ALREADY_ASSIGNED_TO_DIFFERENT_MANDOR';
  end if;

  if v_id is null then
    insert into erp.cutting_pickups(
      cutting_group_id,contractor_id,picked_up_at,allocation_mode,status,notes,created_by
    ) values(
      v_group.id,v_contractor_id,v_picked_up_at,v_mode,'DRAFT',nullif(btrim(p_payload->>'notes'),''),v_actor
    ) returning * into v_pickup;
    v_id:=v_pickup.id;
  else
    update erp.cutting_pickups
    set contractor_id=v_contractor_id,picked_up_at=v_picked_up_at,allocation_mode=v_mode,
        notes=case when p_payload ? 'notes' then nullif(btrim(p_payload->>'notes'),'') else notes end,
        updated_at=clock_timestamp()
    where id=v_id returning * into v_pickup;
    -- Delete allocations while their draft parent batch is still visible.
    -- Relying on the FK cascade hides the deleting batch from the child guard,
    -- which correctly fails closed because it can no longer prove DRAFT state.
    delete from erp.cutting_distribution_allocations a
    using erp.cutting_distribution_batches b
    where a.batch_id=b.id and b.pickup_id=v_id;
    delete from erp.cutting_distribution_batches where pickup_id=v_id;
  end if;

  for v_batch in select value from jsonb_array_elements(p_payload->'batches') loop
    if nullif(v_batch->>'batch_no','')::integer is null or (v_batch->>'batch_no')::integer<1 then
      raise exception 'Every distribution batch requires a positive batch_no';
    end if;
    if jsonb_typeof(v_batch->'allocations') is distinct from 'array' then
      raise exception 'Every distribution batch requires an allocations array';
    end if;
    insert into erp.cutting_distribution_batches(pickup_id,batch_no,notes)
    values(v_id,(v_batch->>'batch_no')::integer,nullif(btrim(v_batch->>'notes'),''))
    returning id into v_batch_id;
    for v_allocation in select value from jsonb_array_elements(v_batch->'allocations') loop
      if nullif(v_allocation->>'qty_pcs','')::integer is null or (v_allocation->>'qty_pcs')::integer<=0 then
        raise exception 'Every distribution allocation requires positive qty_pcs';
      end if;
      if not exists(
        select 1
        from erp.cutting_roll_yields y
        join erp.cutting_group_rolls r on r.id=y.cutting_group_roll_id
        where y.id=nullif(v_allocation->>'cutting_roll_yield_id','')::uuid
          and r.cutting_group_id=v_group.id
      ) then raise exception 'Distribution allocation references a yield outside this Potongan'; end if;
      insert into erp.cutting_distribution_allocations(batch_id,cutting_roll_yield_id,qty_pcs)
      values(v_batch_id,(v_allocation->>'cutting_roll_yield_id')::uuid,(v_allocation->>'qty_pcs')::integer);
    end loop;
  end loop;

  select count(*),max(batch_no) into v_batch_count,v_max_batch
  from erp.cutting_distribution_batches where pickup_id=v_id;
  if v_batch_count<1 or v_max_batch<>v_batch_count or exists(
    select 1 from generate_series(1,v_batch_count) expected(batch_no)
    where not exists(
      select 1 from erp.cutting_distribution_batches b
      where b.pickup_id=v_id and b.batch_no=expected.batch_no
    )
  ) then raise exception using errcode='23514',message='DISTRIBUTION_BATCH_NUMBERS_MUST_BE_CONTIGUOUS_FROM_ONE'; end if;
  if exists(
    select 1
    from erp.cutting_roll_yields y
    join erp.cutting_group_rolls r on r.id=y.cutting_group_roll_id
    left join (
      select a.cutting_roll_yield_id,sum(a.qty_pcs)::bigint allocated
      from erp.cutting_distribution_allocations a
      join erp.cutting_distribution_batches b on b.id=a.batch_id
      where b.pickup_id=v_id group by a.cutting_roll_yield_id
    ) z on z.cutting_roll_yield_id=y.id
    where r.cutting_group_id=v_group.id and coalesce(z.allocated,0)>y.qty_pcs
  ) then raise exception using errcode='23514',message='DISTRIBUTION_EXCEEDS_CUTTING_SOURCE'; end if;

  if v_action='POST' then
    if exists(
      select 1
      from erp.cutting_roll_yields y
      join erp.cutting_group_rolls r on r.id=y.cutting_group_roll_id
      left join (
        select a.cutting_roll_yield_id,sum(a.qty_pcs)::bigint allocated
        from erp.cutting_distribution_allocations a
        join erp.cutting_distribution_batches b on b.id=a.batch_id
        where b.pickup_id=v_id group by a.cutting_roll_yield_id
      ) z on z.cutting_roll_yield_id=y.id
      where r.cutting_group_id=v_group.id and coalesce(z.allocated,0)<>y.qty_pcs
    ) or exists(
      select 1 from erp.cutting_distribution_batches b
      where b.pickup_id=v_id and not exists(
        select 1 from erp.cutting_distribution_allocations a where a.batch_id=b.id
      )
    ) then raise exception using errcode='23514',message='POSTED_DISTRIBUTION_MUST_EXACTLY_RECONCILE_EVERY_SOURCE_YIELD'; end if;

    update erp.production_orders
    set contractor_id=coalesce(contractor_id,v_contractor_id),
        status=case when status in ('DRAFT','CUTTING') then 'SEWING' else status end,
        current_stage=case when current_stage='CUTTING' then 'SEWING' else current_stage end,
        updated_at=clock_timestamp()
    where id=v_group.po_id;
    update erp.cutting_pickups
    set status='POSTED',posted_by=v_actor,posted_at=clock_timestamp(),updated_at=clock_timestamp()
    where id=v_id returning * into v_pickup;
    update erp.cutting_groups
    set executor_name=(select c.contractor_name from erp.contractors c where c.id=v_contractor_id),
        picked_up_at=v_picked_up_at,status='PICKED_UP',updated_at=clock_timestamp()
    where id=v_group.id returning * into v_group;
    insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
    values('cutting_pickups',v_pickup.id,'POST',jsonb_build_object(
      'cutting_group_id',v_group.id,'contractor_id',v_contractor_id,
      'picked_up_at',v_picked_up_at,'allocation_mode',v_mode,'batch_count',v_batch_count
    ),v_actor,v_reason);
  else
    select * into v_pickup from erp.cutting_pickups where id=v_id;
  end if;

  v_response:=jsonb_build_object(
    'pickup_id',v_pickup.id,'cutting_group_id',v_group.id,'status',v_pickup.status,
    'row_version',v_pickup.row_version,'group_row_version',v_group.row_version,
    'picked_up_at',v_pickup.picked_up_at,'contractor_id',v_pickup.contractor_id,
    'allocation_mode',v_pickup.allocation_mode,'batch_count',v_batch_count,
    'allocated_pieces',(
      select coalesce(sum(a.qty_pcs),0)
      from erp.cutting_distribution_allocations a
      join erp.cutting_distribution_batches b on b.id=a.batch_id where b.pickup_id=v_pickup.id
    )
  );
  return erp._idempotency_complete('save_cutting_pickup_v1',p_client_request_id,v_response);
end
$function$
;
CREATE OR REPLACE FUNCTION cp7_cutting_correction.sewing_revision(p_original uuid, p_version uuid, p_rate numeric, p_rate_id uuid, p_basis timestamp with time zone, p_request uuid)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
 SET "TimeZone" TO 'UTC'
AS $function$
declare o erp.po_work_component_snapshots;v_id uuid;v_rate numeric;
begin
 select *into strict o from erp.po_work_component_snapshots where id=p_original;
 select s.id,s.rate_per_pcs_snapshot into v_id,v_rate from cp7_cutting_correction.rate_revisions r join erp.po_work_component_snapshots s on s.id=r.snapshot_id
  where r.original_snapshot_id=p_original and r.basis_at=p_basis
   and r.mandor_generation is not distinct from cp7_contractor_correction.generation_v1(o.po_id);
 if v_id is not null then
  if v_rate is distinct from p_rate or(select bf_sku_version_id from erp.po_work_component_snapshots where id=v_id)is distinct from p_version then
   raise exception 'CP7_SEWING_RATE_BASIS_CHANGED';end if;
  return v_id;
 end if;
 insert into erp.po_work_component_snapshots(po_id,work_component_id,source_bom_version_id,source_bom_item_id,source_contractor_rate_id,
   sequence_no,rate_per_pcs_snapshot,committed_at,bf_sku_version_id)
  values(o.po_id,o.work_component_id,o.source_bom_version_id,o.source_bom_item_id,p_rate_id,o.sequence_no,p_rate,clock_timestamp(),p_version)
  returning id into v_id;
 insert into cp7_cutting_correction.rate_revisions(snapshot_id,original_snapshot_id,po_id,basis_at,actor,request_id,mandor_generation)
  values(v_id,p_original,o.po_id,p_basis,auth.uid(),p_request,cp7_contractor_correction.generation_v1(o.po_id));
 return v_id;
end $function$
;
set local role cp7_cutting_read;
revoke create on schema cp7_cutting_correction from postgres;
reset role;
revoke cp7_cutting_read from postgres granted by postgres restrict;
