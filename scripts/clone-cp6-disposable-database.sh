#!/usr/bin/env bash

set -euo pipefail

if [[ "$#" -ne 6 ]]; then
  echo 'usage: clone-cp6-disposable-database.sh SOURCE_PGURL MAINTENANCE_PGURL CLONE_PGURL CLONE_NAME DATABASE_CONTAINER PROOF_PREFIX' >&2
  exit 64
fi

source_pgurl="$1"
maintenance_pgurl="$2"
clone_pgurl="$3"
clone_name="$4"
database_container="$5"
proof_prefix="$6"
fence_proof="${proof_prefix}.connection-fence.txt"
source_fenced='0'

case "$clone_name" in
  cp6_preflight|cp6_race|cp6_auth|cp6_rollback) ;;
  *)
    echo "refusing non-CP6 disposable clone target: $clone_name" >&2
    exit 64
    ;;
esac
if [[ "$database_container" != 'supabase_db_cp5-local' ]]; then
  echo "refusing non-CP6 disposable database container: $database_container" >&2
  exit 64
fi

test "$source_pgurl" = 'postgresql://postgres:postgres@127.0.0.1:54322/postgres'
test "$maintenance_pgurl" = 'postgresql://postgres:postgres@127.0.0.1:54322/template1'
case "$clone_name|$clone_pgurl" in
  'cp6_preflight|postgresql://postgres:postgres@127.0.0.1:54322/cp6_preflight'|\
  'cp6_race|postgresql://postgres:postgres@127.0.0.1:54322/cp6_race'|\
  'cp6_auth|postgresql://postgres:postgres@127.0.0.1:54322/cp6_auth'|\
  'cp6_rollback|postgresql://postgres:postgres@127.0.0.1:54322/cp6_rollback') ;;
  *)
    echo 'refusing a clone URL outside the exact loopback CP6 disposable allowlist' >&2
    exit 64
    ;;
esac

test "$(psql "$source_pgurl" -X -At -v ON_ERROR_STOP=1 -c 'select current_database()')" = 'postgres'
test "$(psql "$maintenance_pgurl" -X -At -v ON_ERROR_STOP=1 -c 'select current_database()')" = 'template1'
test "$(docker inspect --format '{{.State.Running}}' "$database_container")" = 'true'
mkdir -p "$(dirname "$proof_prefix")"

admin_psql() {
  docker exec "$database_container" \
    psql -U supabase_admin -d template1 -X -At -v ON_ERROR_STOP=1 "$@"
}
test "$(admin_psql -c 'select current_user')" = 'supabase_admin'
source_database_owner="$(admin_psql \
  -c "select pg_get_userbyid(datdba) from pg_database where datname='postgres'")"
source_database_acl_is_null="$(admin_psql \
  -c "select datacl is null from pg_database where datname='postgres'")"
source_database_nonowner_grantors="$(admin_psql \
  -c "select count(*) from pg_database d cross join lateral aclexplode(d.datacl) a where d.datname='postgres' and a.grantor<>d.datdba")"
# pg_database_owner controls CREATE on the hardened public schema.  A template
# clone with a different database owner is therefore not privilege-identical,
# even when every ERP row, owner, and grant byte matches.
test "$source_database_owner" = 'postgres'
test "$source_database_acl_is_null" = 't' || test "$source_database_acl_is_null" = 'f'
test "$source_database_nonowner_grantors" = '0'

wait_for_admin() {
  local attempt
  for attempt in $(seq 1 60); do
    if admin_psql -c 'select 1' >/dev/null 2>&1; then return 0; fi
    sleep 1
  done
  echo 'disposable database admin did not recover after the fenced restart' >&2
  return 1
}

restore_source_connections() {
  if [[ "$source_fenced" = '1' ]]; then
    admin_psql -c 'alter database postgres with allow_connections true' >/dev/null || true
  fi
}
trap restore_source_connections EXIT

dropdb --if-exists --force --maintenance-db="$maintenance_pgurl" "$clone_name"

# CREATE DATABASE ... TEMPLATE is an exact physical database copy, but it
# requires zero source sessions. This fence is limited to the disposable local
# CI database and is restored even if termination or cloning fails.
source_fenced='1'
admin_psql -c 'alter database postgres with allow_connections false'
# Supabase preload workers reconnect to postgres immediately after a signal.
# Restart only the exact disposable DB container while datallowconn=false so
# client and extension sessions cannot race CREATE DATABASE ... TEMPLATE.
docker restart "$database_container" >/dev/null
wait_for_admin
test "$(admin_psql -c "select datallowconn from pg_database where datname='postgres'")" = 'f'
terminated_connections="$(admin_psql <<'SQL'
select count(*) filter(where terminated)
from(
  select pg_terminate_backend(pid) terminated
  from pg_stat_activity
  where datname='postgres'
) terminated_sessions;
SQL
)"
remaining_connections="$(admin_psql \
  -c "select count(*) from pg_stat_activity where datname='postgres'")"
test "$remaining_connections" = '0'

docker exec "$database_container" \
  createdb -U supabase_admin --maintenance-db=template1 --template=postgres \
    --owner="$source_database_owner" "$clone_name"
clone_database_owner="$(admin_psql \
  -c "select pg_get_userbyid(datdba) from pg_database where datname='$clone_name'")"
test "$clone_database_owner" = "$source_database_owner"

admin_psql -c 'alter database postgres with allow_connections true'
source_fenced='0'
test "$(psql "$source_pgurl" -X -At -v ON_ERROR_STOP=1 -c 'select current_database()')" = 'postgres'
test "$(psql "$clone_pgurl" -X -At -v ON_ERROR_STOP=1 -c 'select current_database()')" = "$clone_name"

# CREATE DATABASE ... TEMPLATE copies the physical database contents but not
# an explicit pg_database.datacl. Replay that ACL only when the source has one.
# The source audit above refuses foreign grantors so the database owner can
# reproduce every grant without silently changing grant provenance.
if [[ "$source_database_acl_is_null" = 'f' ]]; then
  psql "$source_pgurl" -X -At -v ON_ERROR_STOP=1 -v clone_name="$clone_name" <<'SQL'
with clone_principals as(
  select distinct a.grantee
  from pg_database d
  cross join lateral aclexplode(coalesce(d.datacl,acldefault('d',d.datdba))) a
  where d.datname=:'clone_name'
)
select format(
  'revoke all privileges on database %I from %s',
  :'clone_name',
  case when grantee=0 then 'public' else quote_ident(pg_get_userbyid(grantee)) end
)
from clone_principals
order by grantee
\gexec

with source_acl_groups as(
  select
    a.grantee,
    a.is_grantable,
    string_agg(a.privilege_type,', ' order by a.privilege_type) privileges
  from pg_database d
  cross join lateral aclexplode(d.datacl) a
  where d.datname=current_database()
  group by a.grantee,a.is_grantable
)
select format(
  'grant %s on database %I to %s%s',
  privileges,
  :'clone_name',
  case when grantee=0 then 'public' else quote_ident(pg_get_userbyid(grantee)) end,
  case when is_grantable then ' with grant option' else '' end
)
from source_acl_groups
order by grantee,is_grantable
\gexec
SQL
fi

bash scripts/verify-cp6-disposable-clone.sh "$source_pgurl" "$clone_pgurl" "$proof_prefix"

{
  printf 'source_database=postgres\n'
  printf 'clone_database=%s\n' "$clone_name"
  printf 'database_container=%s\n' "$database_container"
  printf 'database_admin=supabase_admin\n'
  printf 'source_database_owner=%s\n' "$source_database_owner"
  printf 'clone_database_owner=%s\n' "$clone_database_owner"
  printf 'database_owner_preserved=PASS\n'
  printf 'source_database_acl_is_null=%s\n' "$source_database_acl_is_null"
  printf 'source_database_nonowner_grantors=%s\n' "$source_database_nonowner_grantors"
  printf 'database_acl_replayed=PASS\n'
  printf 'clone_strategy=TEMPLATE_POSTGRES\n'
  printf 'source_restart_under_fence=PASS\n'
  printf 'terminated_source_connections=%s\n' "$terminated_connections"
  printf 'remaining_source_connections_during_clone=%s\n' "$remaining_connections"
  printf 'source_connections_restored=PASS\n'
  printf 'status=PASS\n'
} | tee "$fence_proof"
