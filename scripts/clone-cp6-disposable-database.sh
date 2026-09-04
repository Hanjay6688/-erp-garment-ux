#!/usr/bin/env bash

set -euo pipefail

if [[ "$#" -ne 5 ]]; then
  echo 'usage: clone-cp6-disposable-database.sh SOURCE_PGURL MAINTENANCE_PGURL CLONE_PGURL CLONE_NAME PROOF_PREFIX' >&2
  exit 64
fi

source_pgurl="$1"
maintenance_pgurl="$2"
clone_pgurl="$3"
clone_name="$4"
proof_prefix="$5"
fence_proof="${proof_prefix}.connection-fence.txt"
source_fenced='0'

case "$clone_name" in
  cp6_preflight|cp6_race) ;;
  *)
    echo "refusing non-CP6 disposable clone target: $clone_name" >&2
    exit 64
    ;;
esac

test "$source_pgurl" = 'postgresql://postgres:postgres@127.0.0.1:54322/postgres'
test "$maintenance_pgurl" = 'postgresql://postgres:postgres@127.0.0.1:54322/template1'
case "$clone_name|$clone_pgurl" in
  'cp6_preflight|postgresql://postgres:postgres@127.0.0.1:54322/cp6_preflight'|\
  'cp6_race|postgresql://postgres:postgres@127.0.0.1:54322/cp6_race') ;;
  *)
    echo 'refusing a clone URL outside the exact loopback CP6 disposable allowlist' >&2
    exit 64
    ;;
esac

test "$(psql "$source_pgurl" -X -At -v ON_ERROR_STOP=1 -c 'select current_database()')" = 'postgres'
test "$(psql "$maintenance_pgurl" -X -At -v ON_ERROR_STOP=1 -c 'select current_database()')" = 'template1'
mkdir -p "$(dirname "$proof_prefix")"

restore_source_connections() {
  if [[ "$source_fenced" = '1' ]]; then
    psql "$maintenance_pgurl" -X -v ON_ERROR_STOP=1 \
      -c 'alter database postgres with allow_connections true' >/dev/null || true
  fi
}
trap restore_source_connections EXIT

dropdb --if-exists --force --maintenance-db="$maintenance_pgurl" "$clone_name"

# CREATE DATABASE ... TEMPLATE is an exact physical database copy, but it
# requires zero source sessions. This fence is limited to the disposable local
# CI database and is restored even if termination or cloning fails.
source_fenced='1'
psql "$maintenance_pgurl" -X -v ON_ERROR_STOP=1 \
  -c 'alter database postgres with allow_connections false'
terminated_connections="$(psql "$maintenance_pgurl" -X -At -v ON_ERROR_STOP=1 <<'SQL'
select count(*) filter(where terminated)
from(
  select pg_terminate_backend(pid) terminated
  from pg_stat_activity
  where datname='postgres'
) terminated_sessions;
SQL
)"
remaining_connections="$(psql "$maintenance_pgurl" -X -At -v ON_ERROR_STOP=1 \
  -c "select count(*) from pg_stat_activity where datname='postgres'")"
test "$remaining_connections" = '0'

createdb --maintenance-db="$maintenance_pgurl" --template=postgres "$clone_name"

psql "$maintenance_pgurl" -X -v ON_ERROR_STOP=1 \
  -c 'alter database postgres with allow_connections true'
source_fenced='0'
test "$(psql "$source_pgurl" -X -At -v ON_ERROR_STOP=1 -c 'select current_database()')" = 'postgres'
test "$(psql "$clone_pgurl" -X -At -v ON_ERROR_STOP=1 -c 'select current_database()')" = "$clone_name"

bash scripts/verify-cp6-disposable-clone.sh "$source_pgurl" "$clone_pgurl" "$proof_prefix"

{
  printf 'source_database=postgres\n'
  printf 'clone_database=%s\n' "$clone_name"
  printf 'clone_strategy=TEMPLATE_POSTGRES\n'
  printf 'terminated_source_connections=%s\n' "$terminated_connections"
  printf 'remaining_source_connections_during_clone=%s\n' "$remaining_connections"
  printf 'source_connections_restored=PASS\n'
  printf 'status=PASS\n'
} | tee "$fence_proof"
