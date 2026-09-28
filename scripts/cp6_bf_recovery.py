"""Exact function/constraint recovery, admitted only before the BF family is used."""
def capture(signatures):
    literals=','.join("'"+s+"'" for s in signatures)
    return """
create table erp.bf_rollback_v1(payload jsonb not null);
insert into erp.bf_rollback_v1(payload)
select jsonb_build_object('functions',(select jsonb_object_agg(s,pg_get_functiondef(s::regprocedure)) from unnest(array[SIGNATURES]) s),
 'snapshot_constraint',(select pg_get_constraintdef(oid) from pg_constraint where conrelid='erp.po_work_component_snapshots'::regclass and conname='po_work_component_snapshots_po_id_work_component_id_key'),
 'rework_constraint',(select pg_get_constraintdef(oid) from pg_constraint where conrelid='erp.rework_component_lines'::regclass and conname='rework_component_lines_rate_basis_check'));
""".replace('SIGNATURES',literals)

def seal(names):
    literals=','.join("'"+s+"'" for s in names)
    return """
update erp.bf_rollback_v1 set payload=payload||jsonb_build_object('installed',(
 select jsonb_object_agg(p.oid::regprocedure::text,md5(pg_get_functiondef(p.oid))) from pg_proc p join pg_namespace n on n.oid=p.pronamespace
 where n.nspname||'.'||p.proname=any(array[NAMES])));
""".replace('NAMES',literals)

def rollback(new_functions,tables):
    names=','.join("'"+s+"'" for s in new_functions)
    table_names=','.join("'"+s+"'" for s in reversed(tables) if s!='bf_rollback_v1')
    return """-- BF unused rollback. No posted history or master decisions are deleted after use.
begin;
set local search_path='';
set local lock_timeout='10s';
do $rollback$
declare capsule jsonb;r record;t text;n bigint;
begin
 perform pg_advisory_xact_lock(hashtextextended('BF:COMMERCIAL_SKUS',0));
 if not exists(select 1 from erp.schema_migrations where version='v2.6.20bf') then raise exception 'BF_NOT_INSTALLED';end if;
 select payload into strict capsule from erp.bf_rollback_v1;
 foreach t in array array[TABLES] loop
   execute format('lock table erp.%I in access exclusive mode',t);
   execute format('select count(*) from erp.%I',t) into n;
   if n<>0 then raise exception 'BF_USED_ROLLBACK_REFUSED: % sudah dipakai',t;end if;
 end loop;
 for r in select key,value from jsonb_each_text(capsule->'installed') loop
   if to_regprocedure(r.key) is null or md5(pg_get_functiondef(to_regprocedure(r.key))) is distinct from r.value then
     raise exception 'BF_ROLLBACK_SOURCE_DRIFT: %',r.key;end if;
 end loop;
 for r in select value from jsonb_each_text(capsule->'functions') loop execute r.value;end loop;
 drop trigger bf_fg_member on erp.fg_lots;
 drop trigger bf_bs_member on erp.bs_cases;
 drop trigger bf_shared_price on erp.product_price_versions;
 drop trigger bf_shared_bom on erp.accessory_bom_versions;
 drop trigger bf_shared_bom_item on erp.accessory_bom_items;
 alter table erp.po_work_component_snapshots drop column bf_sku_version_id;
 execute 'alter table erp.po_work_component_snapshots add constraint po_work_component_snapshots_po_id_work_component_id_key '||(capsule->>'snapshot_constraint');
 alter table erp.rework_component_lines drop column bf_sku_version_id;
 alter table erp.rework_component_lines drop constraint rework_component_lines_rate_basis_check;
 execute 'alter table erp.rework_component_lines add constraint rework_component_lines_rate_basis_check '||(capsule->>'rework_constraint');
 alter table erp.bd_laundry_charge_lines_v1 drop column bf_sku_version_id;
 for r in select p.oid::regprocedure::text signature from pg_proc p join pg_namespace n on n.oid=p.pronamespace
   where n.nspname||'.'||p.proname=any(array[NAMES]) loop execute 'drop function '||r.signature;end loop;
 foreach t in array array[TABLES] loop execute format('drop table erp.%I',t);end loop;
 drop table erp.bf_rollback_v1;
 delete from erp.schema_migrations where version='v2.6.20bf';
end $rollback$;
commit;
""".replace('NAMES',names).replace('TABLES',table_names)
