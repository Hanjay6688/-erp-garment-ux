#!/usr/bin/env bash

set -euo pipefail

if [[ "$#" -ne 3 ]]; then
  echo 'usage: verify-cp6-disposable-clone.sh SOURCE_PGURL CLONE_PGURL PROOF_PREFIX' >&2
  exit 64
fi

source_pgurl="$1"
clone_pgurl="$2"
proof_prefix="$3"
source_erp_dump="${proof_prefix}.source-erp.sql"
clone_erp_dump="${proof_prefix}.clone-erp.sql"
diff_file="${proof_prefix}.erp.diff"
proof_file="${proof_prefix}.txt"
restrict_key='CP6CloneBoundary20260904'

mkdir -p "$(dirname "$proof_prefix")"

source_pg_cron_count="$(psql "$source_pgurl" -X -At -v ON_ERROR_STOP=1 \
  -c "select count(*) from pg_extension where extname='pg_cron'")"
clone_pg_cron_count="$(psql "$clone_pgurl" -X -At -v ON_ERROR_STOP=1 \
  -c "select count(*) from pg_extension where extname='pg_cron'")"

database_identity() {
  local pgurl="$1"
  psql "$pgurl" -X -At -v ON_ERROR_STOP=1 <<'SQL'
select jsonb_build_object(
  'owner',pg_get_userbyid(d.datdba),
  'acl',coalesce(d.datacl::text,''),
  'allow_connections',d.datallowconn,
  'connection_limit',d.datconnlimit
)::text
from pg_database d where d.datname=current_database();
SQL
}

public_schema_identity() {
  local pgurl="$1"
  psql "$pgurl" -X -At -v ON_ERROR_STOP=1 <<'SQL'
select jsonb_build_object(
  'owner',pg_get_userbyid(n.nspowner),
  'acl',coalesce(n.nspacl::text,''),
  'postgres_usage',has_schema_privilege('postgres','public','USAGE'),
  'postgres_create',has_schema_privilege('postgres','public','CREATE'),
  'anon_usage',has_schema_privilege('anon','public','USAGE'),
  'anon_create',has_schema_privilege('anon','public','CREATE'),
  'authenticated_usage',has_schema_privilege('authenticated','public','USAGE'),
  'authenticated_create',has_schema_privilege('authenticated','public','CREATE'),
  'service_role_usage',has_schema_privilege('service_role','public','USAGE'),
  'service_role_create',has_schema_privilege('service_role','public','CREATE')
)::text
from pg_namespace n where n.nspname='public';
SQL
}

source_database_identity="$(database_identity "$source_pgurl")"
clone_database_identity="$(database_identity "$clone_pgurl")"
source_public_schema_identity="$(public_schema_identity "$source_pgurl")"
clone_public_schema_identity="$(public_schema_identity "$clone_pgurl")"

test "$source_pg_cron_count" = '1'
test "$clone_pg_cron_count" = '1'
test "$source_database_identity" = "$clone_database_identity"
test "$source_public_schema_identity" = "$clone_public_schema_identity"

# PostgreSQL 17 emits a random psql restrict key unless one is supplied. A fixed
# alphanumeric key makes these local, disposable ERP extracts byte-comparable.
# The extract includes ERP DDL, owners, grants, sequences, and every ERP row.
# A physical template clone must reproduce all of them without reinterpretation.
pg_dump "$source_pgurl" \
  --schema=erp \
  --restrict-key="$restrict_key" \
  --file="$source_erp_dump"
pg_dump "$clone_pgurl" \
  --schema=erp \
  --restrict-key="$restrict_key" \
  --file="$clone_erp_dump"

if ! cmp -s "$source_erp_dump" "$clone_erp_dump"; then
  diff -u "$source_erp_dump" "$clone_erp_dump" > "$diff_file" || true
  echo 'CP6 disposable clone changed ERP schema, grants, sequences, or row data' >&2
  exit 1
fi

rm -f "$diff_file"
erp_sha256="$(sha256sum "$source_erp_dump" | awk '{print $1}')"
erp_bytes="$(wc -c < "$source_erp_dump")"

{
  printf 'source_pg_cron=%s\n' "$source_pg_cron_count"
  printf 'clone_pg_cron=%s\n' "$clone_pg_cron_count"
  printf 'erp_dump_sha256=%s\n' "$erp_sha256"
  printf 'erp_dump_bytes=%s\n' "$erp_bytes"
  printf 'erp_schema_owners_grants_sequences_rows=IDENTICAL\n'
  printf 'database_owner_acl_connectivity=IDENTICAL\n'
  printf 'public_schema_owner_acl_role_privileges=IDENTICAL\n'
  printf 'status=PASS\n'
} | tee "$proof_file"
