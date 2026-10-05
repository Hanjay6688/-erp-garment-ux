"""Exact before/after comparison of a bounded pure-compiler candidate.

The experimental definition exists only inside a rolled-back diagnostic
savepoint. No installed product definition, grant, result or Native fact is
changed. Both compilers receive the same raw SQL JSON and run UUID.
"""
import hashlib
import json
from time import monotonic
import uuid
from pathlib import Path

import psycopg
import cp7_analysis_cases as cases


def compare_history(cur, query, actor):
    """Compare complete old/new history JSON on the same actual Native capture.

    Both observations run under the unchanged read principal and 8s/2s limits.
    The older definition is confined to a rolled-back diagnostic savepoint.
    This measures only the private compiler; it is not full P19 acceptance.
    """
    previous_path = Path(__file__).resolve().parents[1] / 'tests/cp7/fixtures/history-availability-before-e206.sql'
    previous = previous_path.read_text()
    assert hashlib.sha256(previous.encode()).hexdigest() == '82b49380ecb8f0ae61415414fa0cc4fce08718012b795cd19c2c22754fd50c95'
    signature = 'cp7_planning.history_availability(jsonb,jsonb)'
    report = dict(diagnostic_only=True, product_qualification=False,
                  full_P19_acceptance=False, status='DIAGNOSTIC_INCOMPLETE',
                  observations=[], definition_restored=False,
                  Native_HTTP_timeout_changed=False, source_caps_changed=False)
    cases.b.api.admin(cur)
    original = cur.execute('select pg_get_functiondef(%s::regprocedure)', (signature,)).fetchone()[0]
    assert 'Parse the whole immutable Native stock collection once.' in original, 'UNEXPECTED_HISTORY_CANDIDATE'
    report.update(candidate_definition_sha256=hashlib.sha256(original.encode()).hexdigest(),
                  previous_source_sha256=hashlib.sha256(previous.encode()).hexdigest())
    cur.execute('savepoint history_compile_equivalence')
    try:
        cases.auth.actor(cur, actor)
        claims = cur.execute("select current_setting('request.jwt.claims',true)").fetchone()[0]

        def principal():
            cases.b.api.admin(cur)
            cur.execute("select set_config('request.jwt.claims',%s,true)", (claims,))
            cur.execute('set local role cp7_capture')
            cur.execute("set local statement_timeout='8s'")
            cur.execute("set local lock_timeout='2s'")

        principal()
        q = json.dumps(query)
        source = cur.execute('select cp7_analysis_native.source(cp7_planning.history_query(%s::jsonb))::text', (q,)).fetchone()[0]
        parsed = json.loads(source)
        report.update(actual_Native_capture_sha256=hashlib.sha256(source.encode()).hexdigest(),
                      Native_product_count=len(parsed['facts']['products']), Native_stock_count=len(parsed['facts']['stock']))

        def observe(label):
            start = monotonic()
            raw = cur.execute('select cp7_planning.history_availability(%s::jsonb,cp7_planning.history_query(%s::jsonb))::text', (source, q)).fetchone()[0]
            report['observations'].append(dict(label=label, elapsed_ms=round((monotonic()-start)*1000, 3),
                utf8_bytes=len(raw.encode()), full_JSON_sha256=hashlib.sha256(raw.encode()).hexdigest(),
                row_count=len(json.loads(raw))))
            return raw

        candidate_first = observe('INSTALLED_CANDIDATE_FIRST')
        cases.b.api.admin(cur)
        cur.execute('savepoint prior_history_definition')
        cur.execute(previous.replace('create function ', 'create or replace function ', 1), prepare=False)
        principal()
        previous_first = observe('PRIOR_COMPLETE_SQL_FIRST')
        previous_warmed = observe('PRIOR_COMPLETE_SQL_WARMED')
        cur.execute('rollback to savepoint prior_history_definition')
        cur.execute('release savepoint prior_history_definition')
        principal()
        candidate_warmed = observe('RESTORED_CANDIDATE_WARMED')
        report['full_paired_Originals'] = dict(actual_Native_capture_SQL_JSON_text=source,
            candidate_SQL_JSON_text=candidate_first, previous_SQL_JSON_text=previous_first)
        report['complete_SQL_JSON_text_equal'] = candidate_first == previous_first == previous_warmed == candidate_warmed
        assert report['complete_SQL_JSON_text_equal'], 'HISTORY_COMPLETE_PRIOR_SQL_DIFFERENCE'
        report['status'] = 'EXACT_ACTUAL_NATIVE_CAPTURE_HISTORY_COMPILER_EQUIVALENCE'
    except psycopg.Error as error:
        report.update(sqlstate=error.sqlstate, error=error.diag.message_primary)
    finally:
        cur.execute('rollback to savepoint history_compile_equivalence')
        cur.execute('release savepoint history_compile_equivalence')
        cases.b.api.admin(cur)
        restored = cur.execute('select pg_get_functiondef(%s::regprocedure)', (signature,)).fetchone()[0]
        assert restored == original, 'DIAGNOSTIC_HISTORY_DEFINITION_NOT_RESTORED'
        report['definition_restored'] = True
    return report


OLD_MATRIX = """ for p in select value from jsonb_array_elements(wip->'positions')where value->'eligible_company_wip'='true'::jsonb loop
  for r in select value from jsonb_array_elements(scenario->'supply_run_result'->'baseline_run_result'->'rows')loop
   m:=cp7_netting_native.matches(c,p,r,matching);
   matches:=matches||jsonb_build_array(jsonb_build_object('position_key',p->'key','target_key',r->'target_key','result',m));
  end loop;
 end loop;"""

NEW_MATRIX = """ -- Evaluate each immutable pair once and aggregate in the original array
 -- order. The local index never enters the returned matching/result contract.
 with pair_results as materialized(
  select pp.position->'key' position_key,rr.target->'target_key' target_key,
   pp.p_ordinal,rr.t_ordinal,
   jsonb_build_array(pp.position->>'key',rr.target->>'target_key')::text pair_key,
   cp7_netting_native.matches(c,pp.position,rr.target,matching) pair_result
  from jsonb_array_elements(wip->'positions')with ordinality pp(position,p_ordinal)
  cross join jsonb_array_elements(scenario->'supply_run_result'->'baseline_run_result'->'rows')with ordinality rr(target,t_ordinal)
  where pp.position->'eligible_company_wip'='true'::jsonb)
 select coalesce(jsonb_agg(jsonb_build_object('position_key',pr.position_key,'target_key',pr.target_key,
   'result',pr.pair_result)order by pr.p_ordinal,pr.t_ordinal),'[]'::jsonb),
  coalesce(jsonb_object_agg(pr.pair_key,pr.pair_result),'{}'::jsonb),
  count(*)=count(distinct pr.pair_key)
 into matches,match_index,match_index_unique from pair_results pr;"""

OLD_REPEAT = "m:=cp7_netting_native.matches(c,p,r,matching);eta:="
NEW_REPEAT = """m:=case when match_index_unique then
     match_index->(jsonb_build_array(p->>'key',r->>'target_key')::text)
     else cp7_netting_native.matches(c,p,r,matching)end;eta:="""


def optimized_definition(original):
    """Refuse an unexpected predecessor rather than alter a guessed body."""
    for fragment in (OLD_MATRIX, OLD_REPEAT, 'directed_edges jsonb;'):
        assert original.count(fragment) == 1, 'UNEXPECTED_NETTING_PREDECESSOR'
    return original.replace('directed_edges jsonb;',
                            'directed_edges jsonb;match_index jsonb;match_index_unique boolean;') \
        .replace(OLD_MATRIX, NEW_MATRIX).replace(OLD_REPEAT, NEW_REPEAT)


def compare(cur, query, actor):
    report = dict(diagnostic_only=True, product_qualification=False,
                  status='DIAGNOSTIC_INCOMPLETE', comparisons=[],
                  definition_restored=False, Native_HTTP_timeout_changed=False)
    cases.b.api.admin(cur)
    signature = 'cp7_netting_native.build(jsonb,jsonb)'
    original = cur.execute('select pg_get_functiondef(%s::regprocedure)', (signature,)).fetchone()[0]
    if NEW_MATRIX in original and NEW_REPEAT in original:
        # The complete retained comparison belongs to the pre-repair source.
        # Later measurements must not relabel the installed candidate as an
        # independently rerun before/after comparison or mutate it again.
        report.update(status='CANDIDATE_ALREADY_INSTALLED_USE_RETAINED_COMPARISON',
                      definition_restored=True, comparison_rerun=False,
                      retained_comparison_source='4c726f33694b7f0c6ec25397b79bcc81fdc8e645')
        return report
    candidate = optimized_definition(original)
    report.update(original_definition_sha256=hashlib.sha256(original.encode()).hexdigest(),
                  experimental_definition_sha256=hashlib.sha256(candidate.encode()).hexdigest())
    cur.execute('savepoint pure_compile_equivalence')
    try:
        cases.auth.actor(cur, actor)
        claims = cur.execute("select current_setting('request.jwt.claims',true)").fetchone()[0]
        cases.b.api.admin(cur)
        cur.execute("select set_config('request.jwt.claims',%s,true)", (claims,))
        cur.execute('set local role cp7_capture')
        cur.execute("set local statement_timeout='8s'")
        cur.execute("set local lock_timeout='2s'")
        q = json.dumps(query)
        source = cur.execute('select cp7_analysis_native.source(cp7_planning.history_query(%s::jsonb))::text',
                             (q,)).fetchone()[0]
        access = cur.execute('select cp7_schedule_native.access_now(false)::text').fetchone()[0]
        run_id = uuid.uuid4()
        statements = (
            ('COMPOSED_NETTING', 'select cp7_netting_native.build(%s::jsonb,cp7_planning.history_query(%s::jsonb))::text',
             (source, q)),
            ('OPERATIONAL_COMPILER', 'select cp7_analysis_native.build_operational(%s::jsonb,cp7_planning.history_query(%s::jsonb),%s,%s::jsonb)::text',
             (source, q, run_id, access)),
            ('PURE_NATIVE_COMPILER', 'select cp7_analysis_native.build(%s::jsonb,cp7_planning.history_query(%s::jsonb),%s,%s::jsonb)::text',
             (source, q, run_id, access)),
        )
        outputs = {}
        for stage, sql, args in statements:
            start = monotonic()
            raw = cur.execute(sql, args).fetchone()[0]
            outputs[stage] = (raw, round((monotonic()-start)*1000))
        cases.b.api.admin(cur)
        cur.execute('savepoint experimental_compile_definition')
        # CREATE OR REPLACE preserves the exact existing owner and ACL. Restore
        # the complete prior definition by rollback before returning any result.
        cur.execute(candidate, prepare=False)
        cur.execute("select set_config('request.jwt.claims',%s,true)", (claims,))
        cur.execute('set local role cp7_capture')
        for stage, sql, args in statements:
            start = monotonic()
            raw = cur.execute(sql, args).fetchone()[0]
            elapsed = round((monotonic()-start)*1000)
            old, old_elapsed = outputs[stage]
            equal = raw == old
            report['comparisons'].append(dict(stage=stage, status='BYTE_IDENTICAL' if equal else 'DIFFERENT',
                original_ms=old_elapsed, experimental_ms=elapsed, utf8_bytes=len(raw.encode()),
                original_sha256=hashlib.sha256(old.encode()).hexdigest(),
                experimental_sha256=hashlib.sha256(raw.encode()).hexdigest()))
        cur.execute('rollback to savepoint experimental_compile_definition')
        cur.execute('release savepoint experimental_compile_definition')
        cur.execute("select set_config('request.jwt.claims',%s,true)", (claims,))
        cur.execute('set local role cp7_capture')
        # Bracket the experiment with another old-definition read: a warmed
        # plan alone must not be presented as the candidate's speed improvement.
        for row, (stage, sql, args) in zip(report['comparisons'], statements):
            start = monotonic()
            raw = cur.execute(sql, args).fetchone()[0]
            row['restored_original_ms'] = round((monotonic()-start)*1000)
            row['restored_original_sha256'] = hashlib.sha256(raw.encode()).hexdigest()
            if raw != outputs[stage][0]:
                row['status'] = 'DIFFERENT_RESTORED_BASELINE'
        report['status'] = ('EXACT_PURE_RESULT_EQUIVALENCE' if all(
            row['status'] == 'BYTE_IDENTICAL' for row in report['comparisons']) else 'DIFFERENT')
    except psycopg.Error as error:
        report.update(sqlstate=error.sqlstate, error=error.diag.message_primary)
    finally:
        cur.execute('rollback to savepoint pure_compile_equivalence')
        cur.execute('release savepoint pure_compile_equivalence')
        cases.b.api.admin(cur)
        restored = cur.execute('select pg_get_functiondef(%s::regprocedure)', (signature,)).fetchone()[0]
        assert restored == original, 'DIAGNOSTIC_NETTING_DEFINITION_NOT_RESTORED'
        report['definition_restored'] = True
    return report
