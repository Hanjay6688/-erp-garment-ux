"""Bounded read measurements from actual Native fixtures, never exit cases.

The one harness case certifies emission and read isolation only. Its timings,
including SQL errors, cannot qualify F04, F05, P18 or P19. Complete Native284
remains mandatory and unmodified.
"""
from time import monotonic
import json
import uuid

import psycopg
import cp7_analysis_cases as cases
import cp7_f03_e01_cases as production
import cp7_native_compile_equivalence as equivalence

CHECKPOINTS = (0, 1, 4, 12)


def measure(cur, query, actor):
    report = dict(diagnostic_only=True, product_qualification=False, steps=[])
    cur.execute('savepoint native_read_measurements')
    try:
        cases.auth.actor(cur, actor)
        claims = cur.execute("select current_setting('request.jwt.claims',true)").fetchone()[0]
        # The ordinary fixture helper changes SESSION AUTHORIZATION, rather
        # than ROLE. Restore the isolated administrator before selecting the
        # exact private definer principal; retain the same actual actor claims.
        cases.b.api.admin(cur)
        cur.execute("select set_config('request.jwt.claims',%s,true)", (claims,))
        cur.execute('set local role cp7_capture')
        cur.execute("set local statement_timeout='8s'")
        cur.execute("set local lock_timeout='2s'")
        access = cur.execute('select cp7_schedule_native.access_now(false)::text').fetchone()[0]
        q = json.dumps(query)
        source = None

        def read(stage, sql, args):
            cur.execute('savepoint diagnostic_stage')
            start = monotonic()
            try:
                raw = cur.execute(sql, args).fetchone()[0]
                value = json.loads(raw)
                row = dict(stage=stage, status='MEASURED', elapsed_ms=round((monotonic()-start)*1000),
                           utf8_bytes=len(raw.encode('UTF8')), source_status=value.get('status'))
                if stage.startswith('COMPLETE_NATIVE_SOURCE') or stage == 'OPERATIONS_SOURCE':
                    row.update(product_count=len(value.get('facts', {}).get('products', [])),
                               fact_collections={key: len(items) for key, items in value.get('facts', {}).items()
                                                 if isinstance(items, list)})
                elif stage == 'PURE_NATIVE_COMPILER':
                    row.update(recommendations=len(value.get('recommendations', [])),
                               timeline_rows=len(value.get('timeline', [])),
                               fact_count=value.get('snapshot', {}).get('fact_count'))
                elif stage.startswith('NATIVE_REMINDER_'):
                    row.update(document_rows=len(value.get('rows', [])),
                               condition_rows=len(value.get('conditions', [])),
                               page_count=len(value.get('pages', [])))
                report['steps'].append(row)
                cur.execute('release savepoint diagnostic_stage')
                return raw
            except psycopg.Error as error:
                report['steps'].append(dict(stage=stage, status='SQL_ERROR',
                                            elapsed_ms=round((monotonic()-start)*1000),
                                            sqlstate=error.sqlstate, error=error.diag.message_primary))
                cur.execute('rollback to savepoint diagnostic_stage')
                cur.execute('release savepoint diagnostic_stage')
                return None

        source = read('COMPLETE_NATIVE_SOURCE',
                      'select cp7_analysis_native.source(cp7_planning.history_query(%s::jsonb))::text', (q,))
        if source is not None:
            # Original SQL JSON text is fed back unchanged. Never parse and
            # serialize Native decimal operands through Python floats.
            read('PURE_NATIVE_COMPILER',
                 'select cp7_analysis_native.build(%s::jsonb,cp7_planning.history_query(%s::jsonb),%s,%s::jsonb)::text',
                 (source, q, uuid.uuid4(), access))
            read('OPERATIONAL_COMPILER',
                 'select cp7_analysis_native.build_operational(%s::jsonb,cp7_planning.history_query(%s::jsonb),%s,%s::jsonb)::text',
                 (source, q, uuid.uuid4(), access))
            read('COMPOSED_NETTING',
                 'select cp7_netting_native.build(%s::jsonb,cp7_planning.history_query(%s::jsonb))::text', (source, q))
            read('COMPLETE_NATIVE_SOURCE_AGAIN',
                 'select cp7_analysis_native.source(cp7_planning.history_query(%s::jsonb))::text', (q,))
            read('NATIVE_FINANCIAL_SOURCE',
                 "select cp7_analysis_native.financial_source(cp7_planning.history_query(%s::jsonb),(%s::jsonb->>'captured_at')::timestamptz)::text",
                 (q, source))
        read('OPERATIONS_SOURCE', 'select cp7_analysis_native.source()::text', ())
        # Observe each protected Native obligation producer independently.
        # These are pure reads of the same actual actor/fixtures, with no saved
        # analysis, episode, claim or Native business write introduced.
        cur.execute('set local role cp7_reminder')
        read('NATIVE_REMINDER_SALES_AR',
             'select cp7_reminder_native.receivable_source()::text', ())
        read('NATIVE_REMINDER_MATERIAL_AP',
             'select cp7_reminder_native.payable_source()::text', ())
        read('NATIVE_REMINDER_OTHER_OBLIGATIONS',
             'select cp7_reminder_native.other_obligation_source()::text', ())
    except psycopg.Error as error:
        report.update(principal_error=dict(sqlstate=error.sqlstate, error=error.diag.message_primary))
    finally:
        # Every pure call runs inside this savepoint and is rolled back. The
        # surrounding fixture has already been prepared by actual writers.
        cur.execute('rollback to savepoint native_read_measurements')
        cur.execute('release savepoint native_read_measurements')
    return report


def cases_provider(cur, today):
    def emission():
        observations, prepared = [], 0
        cases.auth.actor(cur)
        subject = str(cur.execute('select auth.uid()').fetchone()[0])
        cases.b.api.admin(cur)
        for target in CHECKPOINTS:
            while prepared < target:
                cases.setup(cur, today)
                prepared += 1
            before = cases.b.boundary.snapshot(cur)
            originals_before = cur.execute('select count(*) from cp7_analysis_native.runs').fetchone()[0]
            observation = measure(cur, cases.previous.baseline.history.query(today), subject)
            if target in (4, 12):
                observation['experimental_pure_compile'] = equivalence.compare(
                    cur, cases.previous.baseline.history.query(today), subject)
            cases.b.api.admin(cur)
            assert cases.b.boundary.snapshot(cur) == before, 'DIAGNOSTIC_CHANGED_NATIVE_BUSINESS'
            assert cur.execute('select count(*) from cp7_analysis_native.runs').fetchone()[0] == originals_before
            observation.update(added_actual_fixture_count=prepared, Native_business_unchanged=True,
                               workload='NATIVE_PLANNER_FIXTURES',
                               saved_analyses_added=0, no_HTTP_timeout_changed=True)
            observations.append(observation)
            print('CP7_NATIVE_READ_MEASUREMENT ' + json.dumps(observation), flush=True)
        # The initial workload has no stock/sale/journal rows. Add the actual
        # qualified physical/cost/cash/return journey to expose the financial
        # source cost, while retaining all planner fixtures and their timings.
        completed = 0
        for target in CHECKPOINTS[1:]:
            while completed < target:
                production.journey(cur, today)
                completed += 1
            before = cases.b.boundary.snapshot(cur)
            originals_before = cur.execute('select count(*) from cp7_analysis_native.runs').fetchone()[0]
            observation = measure(cur, cases.previous.baseline.history.query(today), subject)
            if target in (4, 12):
                observation['experimental_pure_compile'] = equivalence.compare(
                    cur, cases.previous.baseline.history.query(today), subject)
            cases.b.api.admin(cur)
            assert cases.b.boundary.snapshot(cur) == before, 'DIAGNOSTIC_CHANGED_NATIVE_BUSINESS'
            assert cur.execute('select count(*) from cp7_analysis_native.runs').fetchone()[0] == originals_before
            observation.update(added_actual_fixture_count=prepared, completed_actual_E01_journeys=completed,
                               workload='NATIVE_PLANNER_PLUS_PHYSICAL_COST_CASH_RETURN',
                               Native_business_unchanged=True, saved_analyses_added=0,
                               no_HTTP_timeout_changed=True)
            observations.append(observation)
            print('CP7_NATIVE_READ_MEASUREMENT ' + json.dumps(observation), flush=True)
        return dict(status='PASS', diagnostic_emission_and_isolation_only=True,
                    product_qualification=False, full_P19_acceptance=False,
                    actual_fixture_checkpoints=list(CHECKPOINTS),
                    actual_E01_checkpoints=list(CHECKPOINTS[1:]), measurements=observations)
    return [('DIAGNOSTIC_EMISSION_AND_NATIVE_READ_ISOLATION', emission)]
