"""Keep BS/rework and HPP completeness on the same commercial tariff scope as sewing."""
from pathlib import Path
import re
from cp6_bc_build import substitute,last_definition
REPLACED=['erp.prepare_rework_component_line()','erp.run_v263c_bs_rework_integrity_checks()','erp.get_hpp_completeness(uuid)','erp.resolve_rework_accessory_bom_v1(uuid,timestamp with time zone)']

def changed(fixture):
    rework=substitute(fixture('prepare_rework_component_line'),[
      ('  v_remaining integer;','  v_remaining integer;bf_sku uuid;bf_version uuid;'),
      ('  new.source_contractor_rate_id:=null;','  new.bf_sku_version_id:=null;\n  new.source_contractor_rate_id:=null;'),
      ('  select r.id,r.rate_per_pcs into v_rate_id,v_rate', '''  bf_sku:=erp.bf_group_sku_v1(v_case.cutting_group_id,v_case.product_id);
  if bf_sku is null and v_case.product_id is not null then
    select sku_id into bf_sku from erp.bf_sku_versions_v1 where id=erp.bf_version_at_v1(v_case.product_id,v_order.physical_sent_at);
  end if;
  if bf_sku is not null then
    if v_order.contractor_id is not distinct from v_original_contractor then
      select s.id,s.rate_per_pcs_snapshot into v_po_snapshot,v_rate from erp.po_work_component_snapshots s
        join erp.bf_sku_versions_v1 v on v.id=s.bf_sku_version_id
        where s.po_id=v_case.po_id and v.sku_id=bf_sku and s.work_component_id=v_component.work_component_id;
      if v_po_snapshot is not null then
        new.rate_snapshot:=v_rate;new.source_po_component_snapshot_id:=v_po_snapshot;new.rate_basis:='PO_SNAPSHOT';return new;
      end if;
    end if;
    select id into bf_version from erp.bf_sku_versions_v1 where sku_id=bf_sku and effective_from<=v_order.physical_sent_at
      and(effective_to is null or effective_to>v_order.physical_sent_at);
    v_rate:=erp.bf_work_rate_v1(bf_version,v_order.contractor_id,v_component.work_component_id,v_order.physical_sent_at);
    if v_rate is not null then
      new.rate_snapshot:=v_rate;new.bf_sku_version_id:=bf_version;new.rate_basis:='SKU_RATE';return new;
    end if;
  end if;

  select r.id,r.rate_per_pcs into v_rate_id,v_rate'''),
      ('  where s.po_id=v_case.po_id and s.work_component_id=v_component.work_component_id',
       '  where s.po_id=v_case.po_id and s.work_component_id=v_component.work_component_id\n    and erp.bf_snapshot_matches_v1(s.id,v_case.cutting_group_id,v_case.product_id)')], 'BF rework tariff provenance')
    checks=substitute(fixture('run_v263c_bs_rework_integrity_checks'),[
      ("     or (l.rate_basis='LAUNDRY_ZERO' and l.rate_snapshot<>0)", """     or (l.rate_basis='LAUNDRY_ZERO' and l.rate_snapshot<>0)
     or (l.rate_basis='SKU_RATE' and (l.bf_sku_version_id is null or l.rate_snapshot is distinct from (
       select erp.bf_work_rate_v1(l.bf_sku_version_id,o.contractor_id,c.work_component_id,o.physical_sent_at)
       from erp.rework_orders o join erp.bs_case_components c on c.id=l.bs_case_component_id where o.id=l.rework_order_id)))"""),
      ("    and (l.rate_basis<>'CONTRACTOR_RATE' or l.source_contractor_rate_id is null)",
       "    and not ((l.rate_basis='CONTRACTOR_RATE' and l.source_contractor_rate_id is not null) or (l.rate_basis='SKU_RATE' and l.bf_sku_version_id is not null))")], 'BF rework detector covers SKU source')
    completeness=substitute(fixture('get_hpp_completeness'),[
      ('            where s.po_id=p.id and not exists(','''            where s.po_id=p.id and (s.bf_sku_version_id is not null or not exists(
              select 1 from erp.cutting_groups cg join erp.bf_wave_skus_v1 w on w.cutting_group_id=cg.id where cg.po_id=p.id)
              or exists(select 1 from erp.cutting_groups cg where cg.po_id=p.id and not exists(select 1 from erp.bf_wave_skus_v1 w where w.cutting_group_id=cg.id)))
            and not exists(''')], 'BF completeness ignores unconsumed template when all waves are SKU scoped')
    accessory_source=Path(__file__).resolve().parents[1]/'supabase/migrations/20260903151034_erp_v2_6_19a_cp5_rework_accessory_lineage.sql'
    accessory=substitute(last_definition(accessory_source,'resolve_rework_accessory_bom_v1',text=re.sub(r'(?i)create function erp\.', 'CREATE OR REPLACE FUNCTION erp.',accessory_source.read_text())),[
      ('  v_distinct integer;','  v_distinct integer;bf_version uuid;bf_pinned uuid;bf_sku uuid;bf_frozen uuid;'),
      ('  select abv.id into v_bom',"""  bf_version:=erp.bf_version_at_v1(v_product,p_basis_at);
  if bf_version is not null then
    select sku_id into bf_sku from erp.bf_sku_versions_v1 where id=bf_version;
    select version_id into bf_pinned from erp.bf_po_boms_v1 where po_id=v_po and sku_id=bf_sku;
    if bf_pinned is null then
      select v.id into bf_pinned from erp.po_accessory_bom_commitments c
        join erp.bf_sku_members_v1 m on m.bom_version_id=c.bom_version_id join erp.bf_sku_versions_v1 v on v.id=m.version_id
        where c.po_id=v_po and v.sku_id=bf_sku order by c.committed_at,c.id limit 1;
    end if;
    select bom_version_id into v_bom from erp.bf_sku_members_v1 where version_id=coalesce(bf_pinned,bf_version) and product_root=v_root;
    if v_bom is null and bf_pinned is not null then
      select bom_version_id into bf_frozen from erp.bf_sku_members_v1 where version_id=bf_pinned and bom_version_id is not null order by product_root limit 1;
      select bom_version_id into v_bom from erp.bf_sku_members_v1 where version_id=bf_version and product_root=v_root;
      if erp.bf_recipe_basis_v1(v_bom) is distinct from erp.bf_recipe_basis_v1(bf_frozen) then raise exception 'BF_PO_NEW_MEMBER';end if;
    end if;
    if v_bom is null then raise exception 'BF_BOM_UNCONFIGURED';end if;
    if exists(select 1 from erp.po_accessory_bom_commitments c join erp.products cp on cp.id=c.product_id
      join erp.bf_sku_members_v1 m on m.product_root=cp.identity_root_id and m.version_id=coalesce(bf_pinned,bf_version)
      where c.po_id=v_po and erp.bf_recipe_basis_v1(c.bom_version_id) is distinct from erp.bf_recipe_basis_v1(v_bom)) then raise exception 'BF_PO_LEGACY_BOM';end if;
    return v_bom;
  end if;

  select abv.id into v_bom""")],'BF rework recipe follows pinned commercial SKU')
    return [rework,checks,completeness,accessory]
