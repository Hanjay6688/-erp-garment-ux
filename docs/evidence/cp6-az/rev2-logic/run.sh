#!/bin/bash
# AZ rev2 logic stubs (T1_FAMILY helper, NOT release evidence): minimal stub schema + the AZ rev2 functions extracted from
# supabase/dev/cp6_az_t1_family.sql, numeric scenarios per function and mode (open E, closed E, no invoice).
# Usage: PGHOST=127.0.0.1 PGUSER=postgres bash docs/evidence/cp6-az/rev2-logic/run.sh [db]
set -euo pipefail
DB=${1:-az_rev2_logic}; H=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$H/../../../.." && pwd)
python3 - "$ROOT" <<'PY'
import re,sys
t=open(sys.argv[1]+'/supabase/dev/cp6_az_t1_family.sql').read()
def fn(name):
    s=re.search(r'(?i)create or replace function '+re.escape(name)+r'\(',t).start()
    a=re.compile(r'(?i)\bas \$function\$').search(t,s).end();return t[s:t.index('$function$;',a)+11]
open('/tmp/az_rev2_logic_fns.sql','w').write('\n'.join(fn(n) for n in ['erp.sync_non_po_product_hpp_to_gl_v2620f',
  'erp.sync_initial_import_bs_value_v1','erp.refresh_accessory_hpp_after_material_recost','erp.guard_pocket_period_v1'])+'\n')
PY
psql -qc "drop database if exists $DB" -c "create database $DB" >/dev/null
psql -d $DB -v ON_ERROR_STOP=1 -q -f "$H/schema.sql" -f "$H/acc_schema.sql" -f "$H/pocket_schema.sql" -f /tmp/az_rev2_logic_fns.sql \
  -c "create trigger g after insert on erp.material_adjustment_revaluation_facts for each row execute function erp.guard_pocket_period_v1()"
for s in nonpo nonpo_two_recosts bsv acc pocket; do for m in open closed noninv; do
  { [ "$s" = bsv ] || [ "$s" = nonpo_two_recosts ]; } && [ "$m" = noninv ] && continue
  echo "=== $s $m"; psql -d $DB -v ON_ERROR_STOP=1 -v mode=$m -f "$H/$s.sql" 2>&1 | grep -v '^$\|^-*$\|^(1 row)' || true
done; done
