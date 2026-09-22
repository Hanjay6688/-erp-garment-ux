"""Initial masters share the admitted staging and posting transaction.

Preview reads the proposed account graph without creating records. Posting
keeps the existing stock/account triggers and cannot remap financial history.
"""

VALIDATE = r"""CREATE OR REPLACE FUNCTION erp.validate_initial_import_master_row_v1(
 p_batch_id uuid,p_entity text,j jsonb)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' AS $function$
declare old_row record; parent_code text; coa record; v_cycle boolean; v_missing boolean;
begin
 perform erp.require_owner_admin();
 if p_entity='LOCATION' then
   if upper(j->>'location_type') not in('RAW_MATERIAL_WAREHOUSE','CUTTING_WIP','CONTRACTOR_WIP',
     'LAUNDRY_WIP','QC_WIP','FG_WAREHOUSE','SCRAP_AREA','OTHER') then
     raise exception 'location_type: jenis lokasi tidak dikenal'; end if;
   select * into old_row from erp.locations where location_code=j->>'location_code' for share;
   if old_row.id is not null and old_row.location_type is distinct from upper(j->>'location_type') then
     raise exception 'location_type: impor tidak boleh mengganti jenis lokasi existing'; end if;
   if old_row.id is not null and not coalesce(nullif(j->>'is_active','')::boolean,true)
     and (coalesce((select sum(qty_signed) from erp.material_stock_movements where location_id=old_row.id),0)<>0
       or coalesce((select sum(qty_signed) from erp.fg_stock_movements where location_id=old_row.id),0)<>0) then
     raise exception 'is_active: lokasi masih memiliki stok'; end if;
 elsif p_entity='CHART_ACCOUNT' then
   if upper(j->>'account_type') not in('ASSET','LIABILITY','EQUITY','REVENUE','EXPENSE') then
     raise exception 'account_type: jenis akun tidak dikenal'; end if;
   if upper(j->>'normal_balance') not in('DEBIT','CREDIT') then
     raise exception 'normal_balance: gunakan DEBIT atau CREDIT'; end if;
   select a.*,p.account_code parent_code into old_row from erp.chart_accounts a
     left join erp.chart_accounts p on p.id=a.parent_account_id where a.account_code=j->>'account_code' for share of a;
   parent_code:=nullif(btrim(j->>'parent_account_code'),'');
   if old_row.id is not null and (
     old_row.account_type is distinct from upper(j->>'account_type')
     or old_row.report_group is distinct from j->>'report_group'
     or old_row.normal_balance is distinct from upper(j->>'normal_balance')
     or old_row.parent_code is distinct from parent_code
     or old_row.is_postable is distinct from coalesce(nullif(j->>'is_postable','')::boolean,true)
     or old_row.is_active is distinct from coalesce(nullif(j->>'is_active','')::boolean,true)) then
     raise exception 'account_code: impor tidak boleh mengubah arti, induk, atau status akun existing'; end if;
   -- Staged definitions replace the same code only in this read-only graph.
   -- Reversed CSV order works; self-links, long cycles and missing ancestors fail.
   with recursive staged as(
     select distinct on(normalized_payload->>'account_code') normalized_payload->>'account_code' code,
       nullif(btrim(normalized_payload->>'parent_account_code'),'') parent
     from erp.migration_staging_rows where batch_id=p_batch_id and entity_type='CHART_ACCOUNT'
     order by normalized_payload->>'account_code',source_row_no,id
   ), graph as(
     select a.account_code code,p.account_code parent from erp.chart_accounts a
       left join erp.chart_accounts p on p.id=a.parent_account_id
       where not exists(select 1 from staged s where s.code=a.account_code)
     union all select code,parent from staged
   ), walk(code,parent,path,cycle,missing) as(
     select g.code,g.parent,array[g.code]::text[],false,false from graph g where g.code=j->>'account_code'
     union all
     select coalesce(g.code,w.parent),g.parent,w.path||w.parent,w.parent=any(w.path),g.code is null
       from walk w left join graph g on g.code=w.parent
       where w.parent is not null and not w.cycle and not w.missing
   ) select coalesce(bool_or(cycle),false),coalesce(bool_or(missing),false) into v_cycle,v_missing from walk;
   if v_cycle then raise exception 'parent_account_code: hubungan induk akun membentuk lingkaran'; end if;
   if v_missing then raise exception 'parent_account_code: akun induk tidak ditemukan'; end if;
 elsif p_entity='CASH_ACCOUNT' then
   if upper(j->>'account_kind') not in('CASH','BANK','EWALLET','OTHER') then
     raise exception 'account_kind: jenis rekening tidak dikenal'; end if;
   select a.id,a.account_code,a.account_type,a.is_active,a.is_postable into coa
     from erp.chart_accounts a where a.account_code=j->>'coa_account_code' for share;
   if exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch_id and s.entity_type='CHART_ACCOUNT'
      and s.normalized_payload->>'account_code'=j->>'coa_account_code') then
     select null::uuid id,s.normalized_payload->>'account_code' account_code,
       upper(s.normalized_payload->>'account_type') account_type,
       coalesce(nullif(s.normalized_payload->>'is_active','')::boolean,true) is_active,
       coalesce(nullif(s.normalized_payload->>'is_postable','')::boolean,true) is_postable into coa
       from erp.migration_staging_rows s where s.batch_id=p_batch_id and s.entity_type='CHART_ACCOUNT'
       and s.normalized_payload->>'account_code'=j->>'coa_account_code' and s.validation_status='VALID' limit 1;
   end if;
   if coa.account_code is null or coa.account_type is distinct from 'ASSET' or not coa.is_active or not coa.is_postable then
     raise exception 'coa_account_code: rekening memerlukan akun ASSET aktif yang boleh dipakai jurnal'; end if;
   select c.*,a.account_code into old_row from erp.cash_accounts c join erp.chart_accounts a on a.id=c.coa_account_id
     where c.cash_account_code=j->>'cash_account_code' for share of c;
   if old_row.id is not null and (old_row.account_code is distinct from j->>'coa_account_code'
      or old_row.account_kind is distinct from upper(j->>'account_kind')) then
     raise exception 'coa_account_code/account_kind: impor tidak boleh memindahkan rekening existing'; end if;
 end if;
end;$function$;
"""


def extend_master_contract(functions):
    def change(identity, old, new, count=1):
        assert functions[identity].count(old) == count, (identity, old)
        functions[identity] = functions[identity].replace(old, new)

    validator = 'erp._validate_migration_batch_base(uuid)'
    writer = 'erp.apply_migration_master_rows(uuid)'
    functions['erp.validate_initial_import_master_row_v1(uuid,text,jsonb)'] = VALIDATE
    change(validator, "when 'BRAND' then 'brand_code'", "when 'LAUNDRY_VENDOR' then 'vendor_code' when 'LOCATION' then 'location_code' when 'CHART_ACCOUNT' then 'account_code' when 'CASH_ACCOUNT' then 'cash_account_code' when 'BRAND' then 'brand_code'")
    change(validator, "when 'BRAND' then 10", "when 'LAUNDRY_VENDOR' then 1 when 'LOCATION' then 2 when 'CHART_ACCOUNT' then 3 when 'CASH_ACCOUNT' then 4 when 'BRAND' then 10")
    change(validator, "when 'BRAND' then array['brand_code','brand_name']", """when 'LAUNDRY_VENDOR' then array['vendor_code','vendor_name']
      when 'LOCATION' then array['location_code','location_name','location_type']
      when 'CHART_ACCOUNT' then array['account_code','account_name','account_type','report_group','normal_balance']
      when 'CASH_ACCOUNT' then array['cash_account_code','cash_account_name','coa_account_code','account_kind']
      when 'BRAND' then array['brand_code','brand_name']""")
    change(validator, "('BRAND','brands',array['brand_code','brand_name','is_active']),", """('LAUNDRY_VENDOR','laundry_vendors',array['vendor_code','vendor_name','phone','is_active','notes']),
      ('LOCATION','locations',array['location_code','location_name','location_type','is_active']),
      ('CHART_ACCOUNT','chart_accounts',array['account_code','account_name','account_type','report_group','normal_balance','is_postable','is_active']),
      ('CASH_ACCOUNT','cash_accounts',array['cash_account_code','cash_account_name','account_kind','is_active']),
      ('BRAND','brands',array['brand_code','brand_name','is_active']),""")
    change(validator, "    if r.entity_type='SUPPLIER'", "    perform erp.validate_initial_import_master_row_v1(p_batch_id,r.entity_type,r.normalized_payload);\n    if r.entity_type='SUPPLIER'")
    for code, relation, staged in [('location_code','locations','LOCATION'), ('vendor_code','laundry_vendors','LAUNDRY_VENDOR'), ('cash_account_code','cash_accounts','CASH_ACCOUNT')]:
        change(validator, f"('{code}','{relation}','{code}',null,", f"('{code}','{relation}','{code}','{staged}',")
    old = "if not exists(select 1 from erp.locations where location_code=r.normalized_payload->>'location_code' and location_type='RAW_MATERIAL_WAREHOUSE' and is_active=true) then"
    change(validator, old, """if not exists(select 1 from erp.locations where location_code=r.normalized_payload->>'location_code' and location_type='RAW_MATERIAL_WAREHOUSE' and is_active=true)
        and not exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch_id and s.entity_type='LOCATION'
          and s.validation_status='VALID' and s.normalized_payload->>'location_code'=r.normalized_payload->>'location_code'
          and upper(s.normalized_payload->>'location_type')='RAW_MATERIAL_WAREHOUSE'
          and coalesce(nullif(s.normalized_payload->>'is_active','')::boolean,true)) then""")

    change(writer, "'BRAND','SIZE','MODEL','CUSTOMER','SUPPLIER','CONTRACTOR',", "'LAUNDRY_VENDOR','LOCATION','CHART_ACCOUNT','CASH_ACCOUNT','BRAND','SIZE','MODEL','CUSTOMER','SUPPLIER','CONTRACTOR',")
    change(writer, "when 'BRAND' then 10", "when 'LAUNDRY_VENDOR' then 1 when 'LOCATION' then 2 when 'CHART_ACCOUNT' then 3 when 'CASH_ACCOUNT' then 4 when 'BRAND' then 10")
    change(writer, "    case r.entity_type", """    perform erp.validate_initial_import_master_row_v1(p_batch_id,r.entity_type,j);
    case r.entity_type
      when 'LAUNDRY_VENDOR' then
        insert into erp.laundry_vendors(vendor_code,vendor_name,phone,is_active,notes)
        values(j->>'vendor_code',j->>'vendor_name',nullif(j->>'phone',''),coalesce(nullif(j->>'is_active','')::boolean,true),j->>'notes')
        on conflict(vendor_code) do update set vendor_name=excluded.vendor_name,phone=excluded.phone,
          is_active=excluded.is_active,notes=excluded.notes,updated_at=statement_timestamp() returning id into v_id;
      when 'LOCATION' then
        insert into erp.locations(location_code,location_name,location_type,is_active)
        values(j->>'location_code',j->>'location_name',upper(j->>'location_type'),coalesce(nullif(j->>'is_active','')::boolean,true))
        on conflict(location_code) do update set location_name=excluded.location_name,is_active=excluded.is_active
          where locations.location_type=excluded.location_type returning id into v_id;
        if v_id is null then raise exception 'location_type: identitas lokasi berubah saat impor'; end if;
      when 'CHART_ACCOUNT' then
        -- Parent links are attached after every code exists, in this transaction.
        -- Existing semantic fields remain unchanged and were checked above.
        insert into erp.chart_accounts(account_code,account_name,account_type,report_group,normal_balance,is_postable,is_active)
        values(j->>'account_code',j->>'account_name',upper(j->>'account_type'),j->>'report_group',upper(j->>'normal_balance'),
          coalesce(nullif(j->>'is_postable','')::boolean,true),coalesce(nullif(j->>'is_active','')::boolean,true))
        on conflict(account_code) do update set account_name=excluded.account_name
          where chart_accounts.account_type=excluded.account_type and chart_accounts.report_group=excluded.report_group
            and chart_accounts.normal_balance=excluded.normal_balance and chart_accounts.is_postable=excluded.is_postable
            and chart_accounts.is_active=excluded.is_active
            and (select p.account_code from erp.chart_accounts p where p.id=chart_accounts.parent_account_id)
              is not distinct from nullif(btrim(j->>'parent_account_code'),'') returning id into v_id;
        if v_id is null then raise exception 'account_code: arti akun berubah saat impor'; end if;
      when 'CASH_ACCOUNT' then
        select id into v_category from erp.chart_accounts where account_code=j->>'coa_account_code';
        if v_category is null then raise exception 'coa_account_code: akun belum diterapkan'; end if;
        insert into erp.cash_accounts(cash_account_code,cash_account_name,coa_account_id,account_kind,is_active)
        values(j->>'cash_account_code',j->>'cash_account_name',v_category,upper(j->>'account_kind'),coalesce(nullif(j->>'is_active','')::boolean,true))
        on conflict(cash_account_code) do update set cash_account_name=excluded.cash_account_name,is_active=excluded.is_active
          where cash_accounts.coa_account_id=excluded.coa_account_id and cash_accounts.account_kind=excluded.account_kind returning id into v_id;
        if v_id is null then raise exception 'coa_account_code: rekening berubah saat impor'; end if;""")
    change(writer, "  return v_count;", """  update erp.chart_accounts a set parent_account_id=p.id
    from erp.migration_staging_rows s join erp.chart_accounts p on p.account_code=s.normalized_payload->>'parent_account_code'
    where s.batch_id=p_batch_id and s.entity_type='CHART_ACCOUNT' and s.posted_entity_id=a.id
      and a.parent_account_id is distinct from p.id;
  return v_count;""")
