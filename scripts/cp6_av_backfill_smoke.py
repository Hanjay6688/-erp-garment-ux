"""AV rev2 local smoke (PostgreSQL 16, minimal tables): the OUT_OF_NOWHERE origin backfill and its exact install check.

Not a native PG17 result; the native proof is the probe case MANUAL:PREINSTALL_CLASSIFIED_*."""
import sys,subprocess
sys.path.insert(0,'scripts')
import cp6_av_build as b
sql=f"""
begin;
create schema erp;
create table erp.bs_cases(id uuid primary key,untracked_type text);
create table erp.audit_logs(entity_type text,entity_id uuid,action text,new_data jsonb,changed_at timestamptz default clock_timestamp());
create table erp.bs_case_manual_origins_v1(bs_case_id uuid primary key references erp.bs_cases(id),origin_type text not null check(origin_type in('LEGACY','OUT_OF_NOWHERE')),recorded_at timestamptz not null default statement_timestamp());
-- a: OOTN classified (audit OOTN, current null) -> row
-- b: OOTN unclassified (audit OOTN, current OOTN) -> row
-- c: LEGACY classified (audit LEGACY, current null) -> no row
-- d: QC BS (audit null, current null) -> no row
-- e: no audit, current OOTN -> row (fallback)
-- f: no audit, current null -> no row (documented limit)
insert into erp.bs_cases values('00000000-0000-0000-0000-00000000000a',null),('00000000-0000-0000-0000-00000000000b','OUT_OF_NOWHERE'),
 ('00000000-0000-0000-0000-00000000000c',null),('00000000-0000-0000-0000-00000000000d',null),('00000000-0000-0000-0000-00000000000e','OUT_OF_NOWHERE'),('00000000-0000-0000-0000-00000000000f',null);
insert into erp.audit_logs(entity_type,entity_id,action,new_data) values
 ('bs_cases','00000000-0000-0000-0000-00000000000a','INSERT','{{"untracked_type":"OUT_OF_NOWHERE"}}'),
 ('bs_cases','00000000-0000-0000-0000-00000000000a','UPDATE','{{"untracked_type":null}}'),
 ('bs_cases','00000000-0000-0000-0000-00000000000b','INSERT','{{"untracked_type":"OUT_OF_NOWHERE"}}'),
 ('bs_cases','00000000-0000-0000-0000-00000000000c','INSERT','{{"untracked_type":"LEGACY"}}'),
 ('bs_cases','00000000-0000-0000-0000-00000000000d','INSERT','{{"untracked_type":null}}'),
 ('qc_items','00000000-0000-0000-0000-00000000000f','INSERT','{{"untracked_type":"OUT_OF_NOWHERE"}}');
insert into erp.{b.ORIGINS}(bs_case_id,origin_type) {b.BACKFILL_SOURCE};
select right(bs_case_id::text,1) k,origin_type from erp.{b.ORIGINS} order by 1;
do $c$ begin
 if exists((select bs_case_id,origin_type from erp.{b.ORIGINS}) except ({b.BACKFILL_SOURCE}))
  or exists(({b.BACKFILL_SOURCE}) except (select bs_case_id,origin_type from erp.{b.ORIGINS}))
 then raise exception 'AV_INSTALL_ORIGIN_BACKFILL_MISMATCH';end if; raise notice 'EXACT_CHECK_PASS';
end $c$;
delete from erp.{b.ORIGINS} where right(bs_case_id::text,1)='e';
do $c$ begin
 if exists((select bs_case_id,origin_type from erp.{b.ORIGINS}) except ({b.BACKFILL_SOURCE}))
  or exists(({b.BACKFILL_SOURCE}) except (select bs_case_id,origin_type from erp.{b.ORIGINS}))
 then raise notice 'NEGATIVE_DETECTED: AV_INSTALL_ORIGIN_BACKFILL_MISMATCH'; else raise exception 'NEGATIVE_MISSED';end if;
end $c$;
rollback;
"""
r=subprocess.run(['psql','-h','/tmp','-p','55432','-U','postgres','-d','postgres','-X','-v','ON_ERROR_STOP=1','-c',sql],capture_output=True,text=True)
print(r.stdout);print(r.stderr)
