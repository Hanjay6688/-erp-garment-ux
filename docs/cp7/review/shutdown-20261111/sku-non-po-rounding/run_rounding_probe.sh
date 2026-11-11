#!/usr/bin/env bash
set -euo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
attempt="$(realpath -- "$1")"
lab="$(realpath -- "$2")"
pg="$lab/pg17/package/native/bin"
data="$attempt/data"
test ! -e "$data"
port="$(python -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])')"
"$pg/initdb" -D "$data" -U movavg_lab --locale=C --encoding=UTF8 --auth-host=trust --auth-local=trust > "$attempt/INITDB.log"
stop() {
  "$pg/pg_ctl" -D "$data" -m fast -w stop
  if "$pg/pg_ctl" -D "$data" status; then
    return 1
  else
    test "$?" = 3
  fi
}
trap stop EXIT
"$pg/pg_ctl" -D "$data" -l "$attempt/POSTGRES.log" -o "-h 127.0.0.1 -p $port -k '' -c max_connections=8" -w start
CP7_PG_MODULE="$lab/node_modules/pg" CP7_LAB_PORT="$port" CP7_LAB_PGDATA="$data" \
  CP7_FOCUSED_PROBE="$lab/handoff/focused_probe.mjs" CP7_ROUNDING_CATALOGUE_PROBE="$here/check_rounding_catalogue.mjs" \
  CP7_CONSUMER_MODEL_INPUT="$attempt/COST_MODEL_INPUT.json" CP7_FIRST_FAILURE="$attempt/FIRST_RUNTIME_FAILURE.json" \
  CP7_REPORT="$attempt/RESULT.json" node "$attempt/focused.mjs"
