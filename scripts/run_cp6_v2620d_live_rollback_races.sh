#!/usr/bin/env bash
set -euo pipefail

: "${PGURL:?PGURL is required}"
: "${CP6_MAINTENANCE_PGURL:?CP6_MAINTENANCE_PGURL is required}"
: "${CP6_ROLLBACK_RACE_PGURL:?CP6_ROLLBACK_RACE_PGURL is required}"
: "${CP6_DATABASE_CONTAINER:?CP6_DATABASE_CONTAINER is required}"

database_name='cp6_rollback'
remaining_databases='UNKNOWN'
proof_dir='cp6-proof'
migration='supabase/migrations/20260908160000_erp_v2_6_20d_cp6_reaudit_business_closure.sql'
rollback='supabase/rollbacks/20260908160000_erp_v2_6_20d_cp6_reaudit_business_closure.rollback.sql'
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
    | tee "$proof_dir/V2620D_LIVE_ROLLBACK_CLONE_CLEANUP.txt"
  exit "$prior_status"
}
trap cleanup EXIT

prepare_clone() {
  boundary_prefix=$1
  bash scripts/clone-cp6-disposable-database.sh \
    "$PGURL" "$CP6_MAINTENANCE_PGURL" "$CP6_ROLLBACK_RACE_PGURL" "$database_name" \
    "$CP6_DATABASE_CONTAINER" "$proof_dir/$boundary_prefix"

  # Seed under the exact v20c predecessor. These rows predate the fresh v20d
  # capsule and therefore cannot masquerade as post-install use.
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
  \set migration_source_b64 `python3 -c "import base64,pathlib; p=pathlib.Path('supabase/migrations/20260908160000_erp_v2_6_20d_cp6_reaudit_business_closure.sql').read_bytes(); assert p.endswith(b'\\n'); print(base64.b64encode(p[:-1]).decode())"`
  insert into supabase_migrations.schema_migrations(version,name,statements)
  values(
    '20260908160000','erp_v2_6_20d_cp6_reaudit_business_closure',
    array[convert_from(decode(:'migration_source_b64','base64'),'UTF8')]
  );
SQL
  test "$(psql "$CP6_ROLLBACK_RACE_PGURL" -X -At -v ON_ERROR_STOP=1 \
    -c "select count(*) from erp.schema_migrations where version='v2.6.20d'")" = '1'
  test "$(psql "$CP6_ROLLBACK_RACE_PGURL" -X -At -v ON_ERROR_STOP=1 \
    -c "select count(*) from erp.idempotency_requests where created_at>=(select installed_at from erp.schema_migrations where version='v2.6.20d')")" = '0'
}

run_race() {
  mode=$1
  report=$2
  CP6_ROLLBACK_RACE_MODE="$mode" \
  CP6_ROLLBACK_RACE_REPORT="$proof_dir/$report" \
  CP6_ROLLBACK_TARGET_VERSION='v2.6.20d' \
  CP6_ROLLBACK_PLATFORM_NAME='erp_v2_6_20d_cp6_reaudit_business_closure' \
  CP6_ROLLBACK_PREDECESSOR_VERSION='v2.6.20c' \
  CP6_ROLLBACK_TARGET_REG_KIND='class' \
  CP6_ROLLBACK_TARGET_REG_IDENTITY='erp.laundry_redispatch_participant_allocations' \
  CP6_ROLLBACK_POST_USE_REFUSAL='v2.6.20d rollback refused: post-install lineage/business/HPP history exists' \
  CP6_ROLLBACK_EVIDENCE_TAG='V2620D' \
  CP6_ROLLBACK_GATE_RELATION='erp.laundry_failed_wash_batch_size_lines' \
  CP6_ROLLBACK_SQL_PATH="$rollback" \
  python scripts/cp6_v2620c_live_rollback_race.py
}

prepare_clone V2620D_WRITER_FIRST_BOUNDARY
run_race WRITER_FIRST V2620D_LIVE_ROLLBACK_WRITER_FIRST.json \
  2>&1 | tee "$proof_dir/V2620D_LIVE_ROLLBACK_WRITER_FIRST.log"
drop_clone

prepare_clone V2620D_ROLLBACK_FIRST_BOUNDARY
run_race ROLLBACK_FIRST V2620D_LIVE_ROLLBACK_ROLLBACK_FIRST.json \
  2>&1 | tee "$proof_dir/V2620D_LIVE_ROLLBACK_ROLLBACK_FIRST.log"

python - <<'PY'
import json
from pathlib import Path

writer=json.loads(Path('cp6-proof/V2620D_LIVE_ROLLBACK_WRITER_FIRST.json').read_text())
rollback=json.loads(Path('cp6-proof/V2620D_LIVE_ROLLBACK_ROLLBACK_FIRST.json').read_text())
assert writer['status']=='PASS' and rollback['status']=='PASS',(writer,rollback)
assert writer['actual_facade']=='public.erp_save_laundry_qc_action_v1',writer
assert rollback['actual_facade']=='public.erp_save_laundry_qc_action_v1',rollback
assert writer['synthetic_business_marker_used'] is False,writer
assert rollback['synthetic_business_marker_used'] is False,rollback
assert writer['pg_blocking_pids_observed'] is True,writer
assert writer['rollback_refused_post_use'] is True,writer
assert rollback['writer_blocked_by_exact_rollback_pid'] is True,rollback
assert rollback['pre_use_rollback_committed'] is True,rollback
assert rollback['writer_committed_under_restored_predecessor']=='v2.6.20c',rollback
assert writer['production_go'] is False and rollback['production_go'] is False
PY
