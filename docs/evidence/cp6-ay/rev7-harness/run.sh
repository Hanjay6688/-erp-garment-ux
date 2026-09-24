#!/bin/bash
# AY rev7 stub harness (T1_FAMILY evidence helper; NOT release evidence). Local disposable PostgreSQL only.
# Usage: PGHOST=127.0.0.1 PGUSER=postgres bash docs/evidence/cp6-ay/rev7-harness/run.sh [db_name]
# Builds a minimal stub schema, installs the AY tables, helper, targets function and erp.sync_po_hpp_to_gl extracted
# from supabase/dev/cp6_ay_t1_family.sql, then runs every scenario with the parameters in its header.
set -euo pipefail
DB=${1:-ay_rev7_harness}
H=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$H/../../../.." && pwd)
python3 - "$ROOT" "$H" <<'PY'
import sys
root,h=sys.argv[1],sys.argv[2]
t=open(root+'/supabase/dev/cp6_ay_t1_family.sql').read()
tbl=t[t.index('create table erp.po_hpp_gl_lot_state_v1'):t.index('CREATE OR REPLACE FUNCTION erp.po_hpp_gl_leg_add_v1')]
hs=t.index('CREATE OR REPLACE FUNCTION erp.po_hpp_gl_leg_add_v1');helper=t[hs:t.index('$function$;',t.index('AS $function$',hs)+14)+11]
f=t.index('CREATE OR REPLACE FUNCTION erp.sync_po_hpp_to_gl(');fn=t[f:t.index('$function$;',t.index('AS $function$',f)+14)+11]
tf=open(h+'/targets_fn.sql').read().replace('alter function erp.compute_po_hpp_gl_targets_v2620d(uuid) owner to postgres;','')
open('/tmp/ay_rev7_harness_install.sql','w').write(tbl.replace('revoke all on','-- revoke all on')+'\n'+tf+'\n'+helper+'\n'+fn+'\n')
PY
psql -qc "drop database if exists $DB" -c "create database $DB" >/dev/null
psql -d $DB -v ON_ERROR_STOP=1 -q -f "$H/schema.sql" -f /tmp/ay_rev7_harness_install.sql -f "$H/scenarios/helper.sql"
cd "$H/scenarios"
run(){ echo "=== $*"; psql -d $DB -v ON_ERROR_STOP=1 "${@:2}" -f $1.sql 2>&1 | grep -v '^$' | grep -v 'sync_po_hpp_to_gl\|^-*$\|^(1 row)' || true; }
run r1_return -v old=8 -v new=6.6
run r2_contractor -v old=8 -v new=6.6
run r3_pool_po -v old=8 -v new=6.6
run r4_relabel_reversed -v old=10 -v new=8.25
run r4b_relabel_posted -v old=10 -v new=8.25
run r5_voided
run r6_batch_sale -v st='1 hour'
run r6_batch_sale -v st='1 minute'
run r7_writeoff -v old=10 -v new=8.25
run r8_rounding -v old=10 -v new=11.745
run r9_batch_two_pos -v st='1 hour'
run r10_contractor_new -v old=10 -v new=10 -v marker=yes
run r10_contractor_new -v old=10 -v new=10 -v marker=no
run r12_fresh_state -v old=10 -v new=10 -v marker=yes
run r13_no_state_derived -v old=8 -v new=6.6
run r14_relabel_chain
run r15_batch_dilution
run r16_queued_recost -v old=10 -v new=8.25
run r17_pocket_part -v old=12 -v new=11
for f in f1 m2 f1_noninv f1_closed; do run $f; done
