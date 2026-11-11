#!/usr/bin/env bash
set -euo pipefail
lab="$(realpath "$1")"
source="$(realpath "$2")"
attempt="$3"
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
pg="$lab/pg17/package/native/bin"
out="$lab/$attempt"
mkdir -- "$out"
data="$out/data"
"$pg/initdb" -D "$data" -U cp7_b_lab --locale=C --encoding=UTF8 --auth-host=trust --auth-local=trust > "$out/INITDB.log"
"$pg/pg_ctl" -D "$data" -l "$out/POSTGRES.log" -o "-h 127.0.0.1 -p 55428 -k '' -c max_connections=8" -w start
trap '"$pg/pg_ctl" -D "$data" -m fast -w stop; "$pg/pg_ctl" -D "$data" status || test "$?" = 3' EXIT
PYTHONPATH="$lab/python" python -B "$here/snapshot_report_probe.py" "$source"  "$lab/native27/CP7_SKU_MANAGED_RECOVERY_NATIVE27.json" "$data" "$out/RESULT.json"
