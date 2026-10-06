"""Exact old/current compiler comparison inside a rolled-back Native savepoint.

This strengthens the existing frozen-analysis case; it adds no case credit and
does not replace any Native, Auth, race, restoration or browser qualification.
"""
import hashlib
import subprocess
from pathlib import Path
from time import monotonic

BASE = 'ab4d8fa5a1ba640dc2fe03167aa2cabb92337cd5'
PATH = 'scripts/cp7-src/planning/analysis.sql'
SIGNATURE = 'cp7_analysis_native.build_operational(jsonb,jsonb,uuid,jsonb)'


def operational_definition(source):
    marker = 'create function cp7_analysis_native.build(c jsonb,q jsonb,p_run uuid,a jsonb)returns jsonb'
    start = source.index(marker)
    end = source.index('$$;', source.index('$$', start) + 2) + 3
    return source[start:end].replace(
        'create function cp7_analysis_native.build(',
        'create or replace function cp7_analysis_native.build_operational(', 1)


def compare(cur, run, api):
    api.admin(cur)
    facts, query, actor, expected = cur.execute(
        'select facts::text,query::text,access_at_capture::text,result::text '
        'from cp7_analysis_native.runs where id=%s', (run,)).fetchone()
    definition = cur.execute('select pg_get_functiondef(%s::regprocedure)',
                             (SIGNATURE,)).fetchone()[0]
    root = Path(__file__).resolve().parents[1]
    old_source = subprocess.check_output(
        ['git', '-C', str(root), 'show', f'{BASE}:{PATH}'], text=True)
    predecessor = operational_definition(old_source)
    sql = 'select cp7_analysis_native.build(%s::jsonb,%s::jsonb,%s,%s::jsonb)::text'
    args = (facts, query, run, actor)
    timings = {}
    cur.execute('savepoint p19_compiler_equivalence')
    try:
        cur.execute('set local role cp7_capture')
        started = monotonic()
        candidate = cur.execute(sql, args).fetchone()[0]
        timings['candidate_ms'] = round((monotonic() - started) * 1000)
        assert candidate == expected, 'P19_CANDIDATE_DIFFERS_FROM_SAVED_ORIGINAL'
        api.admin(cur)
        cur.execute(predecessor, prepare=False)
        cur.execute('set local role cp7_capture')
        started = monotonic()
        previous = cur.execute(sql, args).fetchone()[0]
        timings['predecessor_ms'] = round((monotonic() - started) * 1000)
        assert previous == candidate, 'P19_COMPLETE_COMPILER_BYTE_DIFFERENCE'
        # A deliberate added field must be detected by the same complete-body
        # comparison. The saved Original is never updated.
        needle = "return v||jsonb_build_object('semantic_hash'"
        assert definition.count(needle) == 1, 'P19_CONTROL_SOURCE_UNEXPECTED'
        negative = definition.replace(
            needle, "return (v||jsonb_build_object('p19_negative_control',true))"
                    "||jsonb_build_object('semantic_hash'", 1)
        api.admin(cur)
        cur.execute(negative, prepare=False)
        cur.execute('set local role cp7_capture')
        assert cur.execute(sql, args).fetchone()[0] != candidate, 'P19_CONTROL_NOT_DETECTED'
    finally:
        cur.execute('rollback to savepoint p19_compiler_equivalence')
        cur.execute('release savepoint p19_compiler_equivalence')
        api.admin(cur)
    assert cur.execute('select pg_get_functiondef(%s::regprocedure)',
                       (SIGNATURE,)).fetchone()[0] == definition
    assert cur.execute('select result::text from cp7_analysis_native.runs where id=%s',
                       (run,)).fetchone()[0] == expected
    return dict(status='BYTE_IDENTICAL', base=BASE,
                utf8_bytes=len(candidate.encode()),
                sha256=hashlib.sha256(candidate.encode()).hexdigest(),
                negative_control_detected=True, definition_restored=True,
                saved_original_unchanged=True, Native_case_credit_added=0,
                Native_HTTP_timeout_changed=False, **timings)
