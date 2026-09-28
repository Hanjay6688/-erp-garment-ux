"""Keep BS/rework and HPP completeness on the same commercial tariff scope as sewing."""
from cp6_bc_build import substitute
REPLACED=['erp.prepare_rework_component_line()','erp.run_v263c_bs_rework_integrity_checks()','erp.get_hpp_completeness(uuid)']

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
    return [rework,checks,completeness]
