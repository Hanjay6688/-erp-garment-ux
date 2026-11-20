#!/usr/bin/env bash
set -euo pipefail
container="$AUDIT_PG_CONTAINER"
image=$(docker inspect --format '{{.Config.Image}}' "$container")
case "$image" in *@sha256:*) ;; *) exit 1 ;; esac
base="$RUNNER_TEMP/a25-recovery"
mkdir -m 700 "$base"
script="$AUDIT_CODE/recovery.py"
python "$script" seed
docker stop -t 100 "$container" >/dev/null
docker run --rm --network none --volumes-from "$container":ro --entrypoint sh "$image" -ec 'cd /; tar -czf - var/lib/postgresql/data etc/postgresql-custom' >"$base/recovery.tar.gz"
digest=$(sha256sum "$base/recovery.tar.gz" | cut -d' ' -f1)
tar -tzf "$base/recovery.tar.gz" >"$base/members"
grep -Fxq 'var/lib/postgresql/data/global/pg_control' "$base/members"
grep -E -q '^etc/postgresql-custom/.+' "$base/members"
docker start "$container" >/dev/null
for attempt in $(seq 1 70); do if docker exec -u postgres "$container" pg_isready -q -U supabase_admin -d cp6_rollback;then break;fi;sleep 1;done
python "$script" advance
tag="astra25-restored-$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT"
vol_data="$tag-data"; vol_config="$tag-config"
cleanup(){
  docker rm -f "$tag" >/dev/null 2>&1 || true
  docker volume rm "$vol_data" "$vol_config" >/dev/null 2>&1 || true
  rm -f "$base/recovery.tar.gz"
}
trap cleanup EXIT
docker volume create "$vol_data" >/dev/null
docker volume create "$vol_config" >/dev/null
socket="$base/socket"; mkdir -m 755 "$socket"
docker run --rm --network none -i -v "$vol_data":/var/lib/postgresql/data -v "$vol_config":/etc/postgresql-custom -v "$socket":/socket --entrypoint sh "$image" -ec 'tar -C / -xzf -; chmod 700 /var/lib/postgresql/data; chown postgres:postgres /var/lib/postgresql/data /socket; chmod 755 /socket' <"$base/recovery.tar.gz"
docker run --rm --network none -v "$vol_data":/var/lib/postgresql/data:ro --entrypoint sh "$image" -ec '"$(pg_config --bindir)/pg_controldata" /var/lib/postgresql/data' >"$base/control"
grep -Eq 'Database cluster state: +shut down' "$base/control"
export POSTGRES_PASSWORD
POSTGRES_PASSWORD=$(openssl rand -hex 32)
docker run --name "$tag" --network none -d -e POSTGRES_PASSWORD -v "$vol_data":/var/lib/postgresql/data -v "$vol_config":/etc/postgresql-custom -v "$socket":/var/run/postgresql "$image" postgres -c config_file=/etc/postgresql/postgresql.conf -c cron.database_name=cp6_rollback -c cron.launch_active_jobs=off >/dev/null
unset POSTGRES_PASSWORD
for attempt in $(seq 1 80); do if docker exec -u postgres "$tag" pg_isready -q -U supabase_admin -d cp6_rollback;then break;fi;sleep 1;done
test "$(docker inspect "$tag" --format '{{.HostConfig.NetworkMode}}')" = none
PGHOST="$socket" python "$script" restore
python - "$digest" "$base/members" "$AUDIT_RESULTS/recovery-physical.json" <<'PY'
import json,pathlib,sys
names=pathlib.Path(sys.argv[2]).read_text().splitlines()
result=dict(sha256=sys.argv[1],entries=len(names),config_entries=sum(n.startswith('etc/postgresql-custom/')for n in names),clean_shutdown=True,new_data_volume=True,new_config_volume=True,network='none')
pathlib.Path(sys.argv[3]).write_text(json.dumps(result,indent=2)+'\n')
PY
