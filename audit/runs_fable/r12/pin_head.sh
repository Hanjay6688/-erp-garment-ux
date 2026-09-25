#!/bin/bash
# pin_head.sh: fetch writer branch; refuse unless product (src, supabase) == 27e1a05 and auditor runtime == 95353aa; pin dispatchers to the head.
set -e
SP=/tmp/claude-0/-home-user--erp-garment-ux/2a0eb6c3-bb79-5f14-b9f8-6487e74e773f/scratchpad
cd $SP/cand && git fetch -q origin claude/new-session-deapao && H=$(git rev-parse origin/claude/new-session-deapao)
git diff --quiet 27e1a05 $H -- src supabase || { echo "PRODUCT_CHANGED since 27e1a05 at $H"; git diff --stat 27e1a05 $H -- src supabase | tail -3; exit 2; }
git diff --quiet 95353aa $H -- .github/workflows/cp6-auditor-scenario.yml scripts/cp6_auditor_runner.py scripts/cp6_auditor_modes.py scripts/cp6_auditor_scenario.py || { echo "RUNTIME_CHANGED at $H"; exit 3; }
sed -i "s/^FROZEN='[0-9a-f]*'.*/FROZEN='$H'  # pinned by pin_head.sh (product 27e1a05, DB package e21d15b, runtime 95353aa verified)/" $SP/wf/dispatch_scenario.py $SP/wf/dispatch_workflow.py
echo "PINNED $H (product 27e1a05 verified)"
