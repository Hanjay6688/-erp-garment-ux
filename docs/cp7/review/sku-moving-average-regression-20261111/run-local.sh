#!/usr/bin/env bash
set -euo pipefail
lab="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
pg="$lab/pg17/package/native/bin"
attempt="$(realpath -- "$1")"
data="$attempt/data"
"$pg/initdb" -D "$data" -U movavg_lab --locale=C --encoding=UTF8 --auth-host=trust --auth-local=trust > "$attempt/INITDB.log"
"$pg/pg_ctl" -D "$data" -l "$attempt/POSTGRES.log" -o "-h 127.0.0.1 -p 55427 -k '' -c max_connections=8" -w start
trap '"$pg/pg_ctl" -D "$data" -m fast -w stop; "$pg/pg_ctl" -D "$data" status || test "$?" = 3' EXIT
CP7_PG_MODULE="$lab/node_modules/pg" CP7_LAB_PORT=55427 CP7_LAB_PGDATA="$data"  CP7_FOCUSED_PROBE="$lab/handoff/focused_probe.mjs"  CP7_CONSUMER_MODEL_INPUT="$attempt/${2:-COST_MODEL_INPUT.json}"  CP7_FIRST_FAILURE="$attempt/FIRST_RUNTIME_FAILURE.json" CP7_REPORT="$attempt/RESULT.json"  node "$attempt/focused.mjs"
