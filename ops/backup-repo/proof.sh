#!/usr/bin/env bash
# Off-site backup proof on disposable servers (owner decision 13 Oct 2026, D13-8d): the 11 cases of
# scripts/cp7_offsite_backup_cases.py against the given rclone remote folder, with a source and a scratch server made
# here from the same Supabase Postgres image. With the owner's Google Drive remote this is the real Drive proof
# (upload, fetch back, hash, restore, compare data, structure and privileges); with an emulator or a directory it only
# checks this script. Nothing here touches Enteng or any hosted database. The proof folder is emptied at the end.
#   IMAGE      Supabase Postgres image (the production version)
#   REMOTE     rclone remote folder whose last part is proof-<id>; it is emptied
#   PASS_FILE  passphrase file
#   OUT        result JSON path (synthetic data only)
#   TOOL       checkout of Hanjay6688/-erp-garment-ux at the pinned tool commit
set -euo pipefail
: "${IMAGE:?}" "${REMOTE:?}" "${PASS_FILE:?}" "${OUT:?}" "${TOOL:?}"
case "$REMOTE" in */proof-*|*:proof-*) ;; *) echo 'CP7_PROOF_REMOTE_MUST_BE_A_PROOF_FOLDER'; exit 64 ;; esac
src_pw="$(openssl rand -hex 16)"; scr_pw="$(openssl rand -hex 16)"
if [ -n "${GITHUB_ACTIONS:-}" ]; then echo "::add-mask::$src_pw"; echo "::add-mask::$scr_pw"; fi
cleanup() {
  docker rm -f cp7_proof_source cp7_proof_scratch >/dev/null 2>&1 || true
  rclone purge "$REMOTE" >/dev/null 2>&1 || true
}
trap cleanup EXIT
for name in cp7_proof_source:54331 cp7_proof_scratch:54339; do
  docker run -d --name "${name%%:*}" -p "127.0.0.1:${name##*:}:5432" -e POSTGRES_PASSWORD="$(openssl rand -hex 16)" "$IMAGE" >/dev/null
done
ready() {  # the image restarts once while its init scripts run: wait for the Supabase roles to exist
  for i in $(seq 1 120); do
    if docker exec "$1" psql -U supabase_admin -d postgres -XAtc "select 1 from pg_roles where rolname='authenticated'" 2>/dev/null | grep -q 1; then
      sleep 3
      docker exec "$1" psql -U supabase_admin -d postgres -XAtc 'select 1' >/dev/null 2>&1 && return 0
    fi
    sleep 2
  done
  docker logs --tail 40 "$1"; return 1
}
ready cp7_proof_source; ready cp7_proof_scratch
docker exec -i cp7_proof_source psql -U supabase_admin -d postgres -X -q -v ON_ERROR_STOP=1 -v pw="$src_pw" \
  <<< "create role cp7_proof_admin login superuser password :'pw';"
docker exec -i cp7_proof_scratch psql -U supabase_admin -d postgres -X -q -v ON_ERROR_STOP=1 -v pw="$scr_pw" \
  <<< "create role cp7_scratch_admin login superuser password :'pw';"
src_url="postgresql://cp7_proof_admin:$src_pw@127.0.0.1:54331/postgres"
scr_url="postgresql://cp7_scratch_admin:$scr_pw@127.0.0.1:54339/postgres"
psql "$src_url" -X -q -v ON_ERROR_STOP=1 -f "$TOOL/ops/backup-repo/proof_seed.sql"
psql "$scr_url" -XAtc "select 'scratch '||current_setting('server_version')"
psql "$src_url" -XAtc "select 'source '||current_setting('server_version')"
case "$REMOTE" in *:*) rclone about "${REMOTE%%:*}:" 2>/dev/null | head -4 || true ;; esac
python "$TOOL/scripts/cp7_offsite_backup_cases.py" "$src_url" "$scr_url" "$REMOTE" "$PASS_FILE" "$OUT"
