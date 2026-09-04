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
source_realtime_schema_count="$(psql "$source_pgurl" -X -At -v ON_ERROR_STOP=1 \
  -c "select count(*) from pg_namespace where nspname='realtime'")"
clone_realtime_schema_count="$(psql "$clone_pgurl" -X -At -v ON_ERROR_STOP=1 \
  -c "select count(*) from pg_namespace where nspname='realtime'")"

test "$source_pg_cron_count" = '1'
test "$clone_pg_cron_count" = '0'
test "$source_realtime_schema_count" = '1'
test "$clone_realtime_schema_count" = '0'

# PostgreSQL 17 emits a random psql restrict key unless one is supplied. A fixed
# alphanumeric key makes these local, disposable ERP extracts byte-comparable.
# The extract includes ERP DDL, grants, sequences, and every ERP row; ownership
# is intentionally normalized because the clone restore itself uses --no-owner.
pg_dump "$source_pgurl" \
  --schema=erp \
  --no-owner \
  --restrict-key="$restrict_key" \
  --file="$source_erp_dump"
pg_dump "$clone_pgurl" \
  --schema=erp \
  --no-owner \
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
  printf 'source_realtime_schema=%s\n' "$source_realtime_schema_count"
  printf 'clone_realtime_schema=%s\n' "$clone_realtime_schema_count"
  printf 'erp_dump_sha256=%s\n' "$erp_sha256"
  printf 'erp_dump_bytes=%s\n' "$erp_bytes"
  printf 'erp_schema_grants_sequences_rows=IDENTICAL\n'
  printf 'status=PASS\n'
} | tee "$proof_file"
