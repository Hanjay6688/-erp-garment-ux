"""Keep each Native126 disposable mode copy's database authority identical.

CREATE DATABASE TEMPLATE copies database contents, but defaults the new owner,
database ACL and database/role GUCs. Do not relax the 22-group oracle to accept
that difference. Repair only the three explicitly named local test copies,
before the unchanged mode setup/verifier runs. No A harness file is edited.
"""
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit
import json
import subprocess
import psycopg
from cp7_ow04_restore_bundle import QUERIES, _catalog

NAMES={'cp6_auditor_race','cp6_auditor_http','cp6_auditor_browser'}
RECEIPTS=[]


def authority(cur):
    with _catalog(cur):
        return dict(cur.execute(QUERIES['database_authority']).fetchall())


def replay_sql(name):
    if name not in NAMES:
        raise ValueError('OW13A_CLONE_NAME_REFUSED')
    # name comes from the exact static allowlist above, never caller SQL.
    return """do $ow13a_clone$
declare target_db constant text := '"""+name+"""'; source_db constant text := 'cp6_rollback';
 source_owner oid;source_limit integer;gr record;st record;item text;setting_name text;setting_value text;
begin
 select datdba,datconnlimit into source_owner,source_limit from pg_database
  where datname=source_db and not datistemplate and datallowconn;
 if source_owner is null or pg_get_userbyid(source_owner)<>'postgres' then raise exception 'OW13A_CLONE_SOURCE_OWNER_REFUSED';end if;
 if exists(select 1 from pg_database d cross join lateral aclexplode(coalesce(d.datacl,acldefault('d',d.datdba)))a
  where d.datname=source_db and a.grantor<>source_owner)then raise exception 'OW13A_CLONE_FOREIGN_GRANTOR_REFUSED';end if;
 if not exists(select 1 from pg_database where datname=target_db and not datistemplate and datallowconn)then raise exception 'OW13A_CLONE_TARGET_REFUSED';end if;
 execute format('alter database %I owner to postgres',target_db);
 execute format('alter database %I connection limit %s',target_db,source_limit);
 -- Grants must have the SOURCE owner as grantor, not the maintenance role.
 set local role postgres;
 for gr in select distinct a.grantee from pg_database d
  cross join lateral aclexplode(coalesce(d.datacl,acldefault('d',d.datdba)))a where d.datname=target_db loop
  execute format('revoke all privileges on database %I from %s',target_db,
   case when gr.grantee=0 then 'public'else quote_ident(pg_get_userbyid(gr.grantee))end);
 end loop;
 for gr in select a.grantee,a.privilege_type,a.is_grantable from pg_database d
  cross join lateral aclexplode(coalesce(d.datacl,acldefault('d',d.datdba)))a
  where d.datname=source_db order by a.grantee,a.privilege_type,a.is_grantable loop
  if gr.privilege_type not in('CONNECT','CREATE','TEMPORARY')then raise exception 'OW13A_CLONE_PRIVILEGE_REFUSED';end if;
  execute format('grant %s on database %I to %s%s',gr.privilege_type,target_db,
   case when gr.grantee=0 then 'public'else quote_ident(pg_get_userbyid(gr.grantee))end,
   case when gr.is_grantable then ' with grant option'else ''end);
 end loop;
 reset role;
 execute format('alter database %I reset all',target_db);
 for st in select s.setrole from pg_db_role_setting s join pg_database d on d.oid=s.setdatabase
  where d.datname=target_db and s.setrole<>0 loop
  execute format('alter role %I in database %I reset all',pg_get_userbyid(st.setrole),target_db);
 end loop;
 -- Values stay inside PostgreSQL; only their catalogue hashes are retained.
 for st in select s.setrole,s.setconfig from pg_db_role_setting s join pg_database d on d.oid=s.setdatabase
  where d.datname=source_db order by s.setrole loop
  foreach item in array st.setconfig loop
   setting_name:=split_part(item,'=',1);setting_value:=substring(item from length(setting_name)+2);
   if st.setrole=0 then execute format('alter database %I set %I to %L',target_db,setting_name,setting_value);
   else execute format('alter role %I in database %I set %I to %L',pg_get_userbyid(st.setrole),target_db,setting_name,setting_value);end if;
  end loop;
 end loop;
end $ow13a_clone$;"""


def copied_with_authority(original_copy,name,receipt_path):
    if name not in NAMES:
        raise ValueError('OW13A_CLONE_NAME_REFUSED')
    url=original_copy(name)
    parsed=urlsplit(url)
    if parsed.scheme not in('postgres','postgresql')or parsed.hostname!='127.0.0.1'or parsed.port!=54322 or parsed.path!='/'+name:
        raise ValueError('OW13A_CLONE_LOCAL_URL_REFUSED')
    source_url=url.rsplit('/',1)[0]+'/cp6_rollback'
    def read(local_url):
        with psycopg.connect(local_url)as conn,conn.cursor()as cur:
            return authority(cur)
    expected,before=read(source_url),read(url)
    command=replay_sql(name)
    result=subprocess.run(['docker','exec','supabase_db_cp5-local','psql','-U','supabase_admin','-d','template1',
        '-XqAt','-v','ON_ERROR_STOP=1','-c',command],capture_output=True,text=True,timeout=60)
    if result.returncode:
        first=next((line for line in result.stderr.splitlines()if line.startswith('ERROR:')),'no PostgreSQL error line')
        raise ValueError('OW13A_CLONE_AUTHORITY_REPLAY_FAILED: '+first[:300])
    after=read(url)
    if after!=expected:
        raise ValueError('OW13A_CLONE_AUTHORITY_NOT_EXACT')
    digest=lambda value:sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    receipt=dict(database=name,source='cp6_rollback',source_owner=expected['CURRENT'][0],
        previous_owner=before['CURRENT'][0],current_owner=after['CURRENT'][0],
        source_authority_sha256=digest(expected),before_authority_sha256=digest(before),after_authority_sha256=digest(after),
        authority_exact=True,oracle_relaxed=False,primary_modified=False)
    RECEIPTS.append(receipt)
    Path(receipt_path).write_text(json.dumps(dict(contract_version='cp7.initial-clone-authority.v1',
        copies=RECEIPTS,production_go=False),indent=2)+'\n')
    return url
