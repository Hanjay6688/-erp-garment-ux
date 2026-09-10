#!/usr/bin/env bash
set -euo pipefail

: "${PGURL:?PGURL is required}"
: "${CP6_MAINTENANCE_PGURL:?CP6_MAINTENANCE_PGURL is required}"
: "${CP6_ROLLBACK_RACE_PGURL:?CP6_ROLLBACK_RACE_PGURL is required}"
: "${CP6_DATABASE_CONTAINER:?CP6_DATABASE_CONTAINER is required}"

database_name='cp6_rollback'
remaining_databases='UNKNOWN'
proof_dir='cp6-proof'
migration='supabase/migrations/20260907190000_erp_v2_6_20c_cp6_deep_business_reliability.sql'
rollback='supabase/rollbacks/20260907190000_erp_v2_6_20c_cp6_deep_business_reliability.rollback.sql'
mkdir -p "$proof_dir"

drop_clone() {
  if ! docker exec "$CP6_DATABASE_CONTAINER" \
    dropdb -U supabase_admin --if-exists --force --maintenance-db=template1 "$database_name"; then
    remaining_databases='UNKNOWN'
    return 1
  fi
  if ! remaining_databases="$(docker exec "$CP6_DATABASE_CONTAINER" \
    psql -U supabase_admin -d template1 -X -At -v ON_ERROR_STOP=1 \
    -c "select count(*) from pg_database where datname='$database_name'")"; then
    remaining_databases='UNKNOWN'
    return 1
  fi
  test "$remaining_databases" = '0'
}

cleanup() {
  prior_status=$?
  trap - EXIT
  set +e
  drop_clone
  cleanup_exit=$?
  set -e
  cleanup_status=FAIL
  if test "$cleanup_exit" -eq 0 && test "$remaining_databases" = '0'; then
    cleanup_status=PASS
  else
    prior_status=1
  fi
  printf 'clone_database=%s\nremaining_databases=%s\nstatus=%s\n' \
    "$database_name" "$remaining_databases" "$cleanup_status" \
    | tee "$proof_dir/V2620C_LIVE_ROLLBACK_CLONE_CLEANUP.txt"
  exit "$prior_status"
}
trap cleanup EXIT

prepare_clone() {
  boundary_prefix=$1
  bash scripts/clone-cp6-disposable-database.sh \
    "$PGURL" "$CP6_MAINTENANCE_PGURL" "$CP6_ROLLBACK_RACE_PGURL" "$database_name" \
    "$CP6_DATABASE_CONTAINER" "$proof_dir/$boundary_prefix"

  # Seed under the exact v20b predecessor. Seed rows predate v20c installed_at
  # and therefore cannot masquerade as post-install use.
  psql "$CP6_ROLLBACK_RACE_PGURL" -X -v ON_ERROR_STOP=1 -f "$rollback" \
    > "$proof_dir/${boundary_prefix}_PREP_ROLLBACK.log" 2>&1
  psql "$CP6_ROLLBACK_RACE_PGURL" -X -v ON_ERROR_STOP=1 \
    -f supabase/tests/cp3_r4_full_schema_seed.sql \
    > "$proof_dir/${boundary_prefix}_FOUNDATION_SEED.log" 2>&1
  psql "$CP6_ROLLBACK_RACE_PGURL" -X -v ON_ERROR_STOP=1 \
    -f supabase/tests/cp6_laundry_qc_concurrency_seed.sql \
    > "$proof_dir/${boundary_prefix}_BUSINESS_SEED.log" 2>&1
  psql "$CP6_ROLLBACK_RACE_PGURL" -X -v ON_ERROR_STOP=1 -f "$migration" \
    > "$proof_dir/${boundary_prefix}_REAPPLY.log" 2>&1
  psql "$CP6_ROLLBACK_RACE_PGURL" -X -v ON_ERROR_STOP=1 <<'SQL'
  \set migration_source_b64 `python3 -c "import base64,pathlib; p=pathlib.Path('supabase/migrations/20260907190000_erp_v2_6_20c_cp6_deep_business_reliability.sql').read_bytes(); assert p.endswith(b'\\n'); print(base64.b64encode(p[:-1]).decode())"`
  insert into supabase_migrations.schema_migrations(version,name,statements)
  values(
    '20260907190000','erp_v2_6_20c_cp6_deep_business_reliability',
    array[convert_from(decode(:'migration_source_b64','base64'),'UTF8')]
  );
SQL
  test "$(psql "$CP6_ROLLBACK_RACE_PGURL" -X -At -v ON_ERROR_STOP=1 \
    -c "select count(*) from erp.schema_migrations where version='v2.6.20c'")" = '1'
  test "$(psql "$CP6_ROLLBACK_RACE_PGURL" -X -At -v ON_ERROR_STOP=1 \
    -c "select count(*) from erp.idempotency_requests where created_at>=(select installed_at from erp.schema_migrations where version='v2.6.20c')")" = '0'
}

prepare_clone V2620C_WRITER_FIRST_BOUNDARY
CP6_ROLLBACK_RACE_MODE=WRITER_FIRST \
CP6_ROLLBACK_RACE_REPORT="$proof_dir/V2620C_LIVE_ROLLBACK_WRITER_FIRST.json" \
python scripts/cp6_v2620c_live_rollback_race.py \
  2>&1 | tee "$proof_dir/V2620C_LIVE_ROLLBACK_WRITER_FIRST.log"
drop_clone

prepare_clone V2620C_ROLLBACK_FIRST_BOUNDARY
CP6_ROLLBACK_RACE_MODE=ROLLBACK_FIRST \
CP6_ROLLBACK_RACE_REPORT="$proof_dir/V2620C_LIVE_ROLLBACK_ROLLBACK_FIRST.json" \
python scripts/cp6_v2620c_live_rollback_race.py \
  2>&1 | tee "$proof_dir/V2620C_LIVE_ROLLBACK_ROLLBACK_FIRST.log"

python - <<'PY'
import json
from pathlib import Path

writer=json.loads(Path('cp6-proof/V2620C_LIVE_ROLLBACK_WRITER_FIRST.json').read_text())
rollback=json.loads(Path('cp6-proof/V2620C_LIVE_ROLLBACK_ROLLBACK_FIRST.json').read_text())
assert writer['status']=='PASS' and rollback['status']=='PASS',(writer,rollback)
assert writer['actual_facade']=='public.erp_save_laundry_qc_action_v1',writer
assert rollback['actual_facade']=='public.erp_save_laundry_qc_action_v1',rollback
assert writer['synthetic_business_marker_used'] is False,writer
assert rollback['synthetic_business_marker_used'] is False,rollback
assert writer['pg_blocking_pids_observed'] is True,writer
assert writer['rollback_refused_post_use'] is True,writer
assert rollback['writer_blocked_by_exact_rollback_pid'] is True,rollback
assert rollback['pre_use_rollback_committed'] is True,rollback
assert writer['production_go'] is False and rollback['production_go'] is False
PY
