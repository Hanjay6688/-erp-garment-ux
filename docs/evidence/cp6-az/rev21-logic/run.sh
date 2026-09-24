#!/bin/bash
# AZ rev2.1 stub logic test (T1_FAMILY helper; NOT release evidence). Local disposable PostgreSQL only.
set -euo pipefail
DB=${1:-az_rev21_logic}; H=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$H/../../../.." && pwd)
python3 - "$ROOT" > /tmp/az_rev21_fn.sql <<'PY'
import sys
t=open(sys.argv[1]+'/supabase/dev/cp6_az_t1_family.sql').read()
i=t.index('CREATE OR REPLACE FUNCTION erp.sync_material_cost_revaluation(');j=t.index('$function$',t.index('AS $function$',i)+14)
print(t[i:t.index('\n',j)])
PY
psql -qc "drop database if exists $DB" -c "create database $DB" >/dev/null
psql -d $DB -v ON_ERROR_STOP=1 -q -f "$H/schema.sql" -f /tmp/az_rev21_fn.sql
for m in open closed noninv; do echo "=== mode=$m"; psql -d $DB -v ON_ERROR_STOP=1 -v mode=$m -f "$H/scenario.sql" 2>&1 | grep -v '^$\|^(.* rows\?)\|sync_material_cost_revaluation\|^-*$' || true; done
