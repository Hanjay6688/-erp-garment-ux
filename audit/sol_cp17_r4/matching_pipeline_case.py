"""One Native-source matcher/allocator/plan/public-command integration control."""
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parent
PRODUCT = ROOT.parents[2] / 'auditor'
sys.path.insert(0, str(PRODUCT / 'scripts'))
import cp7_analysis_cases as analysis
import cp7_plan_native_cases as plan
import cp7_wip_cases as kernel

ID = 'SOL_R4_SKN24_NATIVE_MATCH_ALLOCATE_PLAN_COMMAND'


def cases(cur, today):
    def pipeline():
        observed = dict(case_id=ID, oracle_origin='SOL_MATCHER_REFUSAL_AND_IMMUTABLE_NATIVE_SOURCE_BINDING', negative_facts_are_explicit_copy=True, product_guard_changed=False)
        try:
            # Ordinary receipt plus accepted eight-piece opening WIP, all before
            # the immutable Native Original. No quantity/cost ledger injection.
            fabric = plan.receipt.fixture(cur, today, qty='10', price='10')
            posted = plan.receipt.post(cur, plan.receipt.command(cur, 'SAVE_DRAFT', fabric['payload']))
            f, root, _, _ = analysis.setup(cur, today, True)
            plan.b.api.admin(cur)
            model = cur.execute('select model_id from erp.products where id=%s', (root,)).fetchone()[0]
            po = str(uuid.uuid4())
            now = cur.execute('select clock_timestamp()').fetchone()[0]
            cur.execute("insert into erp.production_orders(id,po_number,model_id,target_qty_pcs,status,current_stage,physical_start_at,notes)values(%s,%s,%s,2,'CUTTING','CUTTING',%s,'Sol matcher public-command control master only')", (po, 'SOLR4-MATCH-' + po, model, now - timedelta(hours=2)))
            original = analysis.capture(cur, today)
            target = analysis.recommendation(original['analysis'], root)['target']['key']
            facts, query = cur.execute('select facts,query from cp7_analysis_native.runs where id=%s', (original['run_id'],)).fetchone()
            n = cur.execute('select cp7_netting_native.build(%s::jsonb,%s::jsonb)', (json.dumps(facts), json.dumps(query))).fetchone()[0]
            row = next(x for x in n['rows'] if x['target_key'] == target)
            assert row['raw_gap_pcs'] == '100' and row['directed_on_time_good_pcs'] == '7' and row['conditional_gap_pcs'] == '93', row
            edge = next(x for x in n['allocation']['allocation']['edges'] if x['target_key'] == target)
            assert edge['input_pcs'] == '8' and edge['projected_good_pcs'] == '7'
            matching = deepcopy(n['matching'])
            source = next(x for x in matching['sources'] if x['key'] == edge['position_key'])
            matched_target = next(x for x in matching['targets'] if x['key'] == target)
            compatible = kernel.call(cur, 'match', source, matched_target)
            assert compatible['match'] == 'CONFIRMED_TARGET', compatible
            allocation = dict(scenario_id=n['allocation']['scenario_id'], scope_id=n['allocation']['scope_id'], complete_scope=True, edges=[deepcopy(edge)], matching=matching)
            positions = n['schedule_run_result']['wip']
            positive = kernel.call(cur, 'allocate', positions, allocation)
            assert positive['status'] == 'FEASIBLE'
            observed.update(original_run=original['run_id'], root=root, target=target, native_netting=n, matching_source=source, compatible_match=compatible, compatible_allocation=positive, lawful_receipt=posted)
            bad = deepcopy(allocation)
            bad_target = next(x for x in bad['matching']['targets'] if x['key'] == target)
            color = next(x for x in bad_target['constraints'] if x['field'] == 'color')
            assert color['basis'] == 'FACT' and color['value'] is not None
            color['value'] = 'SOL_R4_DIFFERENT_COLOR'
            mismatch = kernel.call(cur, 'match', source, bad_target)
            assert mismatch == dict(match='INCOMPATIBLE', reasons=['COLOR_MISMATCH']), mismatch
            bad['edges'][0]['match'] = 'CANDIDATE_MATCH'
            before = plan.monetary_state(cur)
            allocator_refusal = plan.auth.refused(cur, lambda: kernel.call(cur, 'allocate', positions, bad), 'CP7_WIP_INELIGIBLE_ALLOCATION')
            assert plan.monetary_state(cur) == before
            # Public plan has no client match/allocation input. It re-reads and
            # recomputes this same own Original in analysis_source/preflight.
            q = dict(run_id=original['run_id'], target_key=target, location_id=fabric['location'], po_query='', roll_query='', po_offset='0', roll_offset='0', pattern_offset='0', limit='50')
            options = plan.options(cur, q)
            roll = next(x for x in options['rolls'] if x['material_id'] == fabric['material'])
            assert Decimal(roll['available']) == 10
            p = dict(run_id=original['run_id'], target_key=target, plan_id=None, expected_revision=None, source_hash=options['source_hash'], reason='Sol exact Native-source matching integration control', reviewed_assumption_ids=[x['id'] for x in options['assumptions']], cutting=dict(po_id=po, pattern_id=options['patterns'][0]['id'], source_location_id=fabric['location'], cut_at=(now - timedelta(hours=1)).isoformat(), notes='Sol two-piece unposted integration control', size_slots=[dict(slot_no='1', size_id=options['size_id'], drawing_no='1')], rolls=[dict(roll_id=roll['id'], qty_issued='1', qty_consumed='0.5', qty_reported_remaining='0.5', yields=[dict(slot_no='1', qty_pcs='2')])]))
            original_row = cur.execute('select facts,result,dependency_hash from cp7_analysis_native.runs where id=%s', (original['run_id'],)).fetchone()
            drafts_before = cur.execute('select count(*) from cp7_plan_native.drafts').fetchone()[0]
            bad_payload = deepcopy(p); bad_payload['matching'] = bad['matching']
            public_save_refusal = plan.auth.refused(cur, lambda: plan.save(cur, bad_payload), 'CP7_PLAN_FIELDS')
            assert cur.execute('select count(*) from cp7_plan_native.drafts').fetchone()[0] == drafts_before
            assert plan.monetary_state(cur) == before
            saved = plan.save(cur, p)
            preview = plan.preview(cur, saved['draft_id'])
            assert Decimal(preview['needed_pcs']) == 93 and Decimal(preview['selected_new_pcs']) == 2
            assert plan.monetary_state(cur) == before
            bad_action = plan.action(saved, matching=bad['matching'])
            public_apply_refusal = plan.auth.refused(cur, lambda: plan.apply(cur, bad_action), 'CP7_PLAN_FIELDS')
            assert cur.execute('select count(*) from cp7_plan_native.intents').fetchone()[0] == 0
            assert plan.monetary_state(cur) == before
            groups_before = cur.execute('select count(*) from erp.cutting_groups').fetchone()[0]
            committed = plan.apply(cur, plan.action(saved))
            assert committed['state'] == 'NATIVE_DRAFT_CREATED' and committed['native']['material_issue_posted'] is False
            assert Decimal(str(committed['native']['total_pieces'])) == 2
            assert cur.execute('select count(*) from erp.cutting_groups').fetchone()[0] == groups_before + 1
            assert cur.execute('select count(*) from cp7_plan_native.intents').fetchone()[0] == 1
            assert cur.execute('select facts,result,dependency_hash from cp7_analysis_native.runs where id=%s', (original['run_id'],)).fetchone() == original_row
            assert plan.monetary_state(cur) == before
            observed.update(status='PASS', mismatch=mismatch, rejected_allocation=bad, allocator_refusal=allocator_refusal, public_save_refusal=public_save_refusal, public_apply_refusal=public_apply_refusal, legal_payload=p, saved=saved, preview=preview, committed=committed, same_original_unchanged=True, physical_stock_money_HPP_unchanged=True, actual_native_drafts_added=1, selected_new_pcs=2, new_race_credit=0)
            return observed
        finally:
            out = PRODUCT / 'cp6-proof/t3' / (ID + '_OBSERVATIONS.json')
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(observed, indent=2, default=str) + '\n')
    return [(ID, pipeline)]
