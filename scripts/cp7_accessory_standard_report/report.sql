-- S05 / owner D17-19C. This stage adds a reader, never a posting or repair path.
-- Historical standard quantities come only from fg_accessory_cost_snapshots.
-- Committed BOM/selection rows only prove completeness or an explicit empty set.
-- Costs are the Native effective snapshots, with every revision exposed.
create role cp7_accessory_standard_read nologin noinherit nosuperuser nocreatedb nocreaterole noreplication nobypassrls;
create schema cp7_accessory_standard_report authorization cp7_accessory_standard_read;
revoke all on schema cp7_accessory_standard_report from public,anon,authenticated,service_role,cp7_capture;
grant usage on schema cp7_accessory_standard_report to postgres;

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
alter function public.erp_cp7_get_accessory_standard_report_v1(date,date,uuid,uuid,text,integer,integer)owner to cp7_accessory_standard_read;
revoke all on function public.erp_cp7_get_accessory_standard_report_v1(date,date,uuid,uuid,text,integer,integer)from public,anon,service_role,cp7_capture,postgres;
grant execute on function public.erp_cp7_get_accessory_standard_report_v1(date,date,uuid,uuid,text,integer,integer)to authenticated;
