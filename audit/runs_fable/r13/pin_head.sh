#!/bin/bash
# r13: product baseline 434b182 (CP6 closure candidate per replacement auditor); runtime runner/modes/au_r1 must equal 95353aa; driver reviewed at 10a8347.
set -e
SP=/tmp/claude-0/-home-user--erp-garment-ux/2a0eb6c3-bb79-5f14-b9f8-6487e74e773f/scratchpad
cd $SP/cand && git fetch -q origin claude/new-session-deapao && H=$(git rev-parse origin/claude/new-session-deapao)
git diff --quiet 434b182 $H -- src supabase/release supabase/migrations || { echo "PRODUCT_CHANGED since 434b182 at $H"; git diff --stat 434b182 $H -- src supabase/release supabase/migrations | tail -3; exit 2; }
git diff --quiet 95353aa $H -- scripts/cp6_auditor_runner.py scripts/cp6_auditor_modes.py scripts/cp6_au_r1_probe.py || { echo "RUNTIME_CORE_CHANGED at $H"; exit 3; }
git diff --quiet 10a8347 $H -- scripts/cp6_auditor_scenario.py .github/workflows/cp6-auditor-scenario.yml || { echo "DRIVER_CHANGED since reviewed 10a8347 at $H"; exit 4; }
sed -i "s/^FROZEN='[0-9a-f]*'.*/FROZEN='$H'  # pinned by pin_head.sh r13 (product 434b182 verified, runtime core 95353aa, driver reviewed 10a8347)/" $SP/wf/dispatch_scenario.py $SP/wf/dispatch_workflow.py
echo "PINNED $H"
