"""Pure diagnostic proposal. Never connects or changes source expectations.

Only render already captured metadata; callers retain their existing failure
codes and rollback behavior. No result from this module authorizes a catalogue.
"""
from collections import Counter
from hashlib import sha256
import json

SEMANTIC_FK = ('relation', 'columns', 'parent', 'parent_columns',
               'update_action', 'delete_action', 'match_type', 'deferrable',
               'initially_deferred', 'validated')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False)


def counter_diff(expected, actual):
    """Exact multiset difference: preserve duplicate rows and every field."""
    wanted = Counter(canonical(row) for row in expected)
    got = Counter(canonical(row) for row in actual)
    def rows(delta):
        return [dict(row=json.loads(key), count=count)
                for key, count in sorted(delta.items()) if count]
    return dict(equal=wanted == got,
                expected_count=sum(wanted.values()), actual_count=sum(got.values()),
                missing=rows(wanted - got), unexpected=rows(got - wanted))


def function_field(expected, actual, field, phase):
    answer = dict(kind='FUNCTION_' + field.upper(), phase=phase,
                  identity=expected['identity'], source=expected.get('source'),
                  source_definition_sha256=expected.get('source_definition_sha256'),
                  actual_function_oid=actual.get('function_oid'),
                  expected=expected.get(field), actual=actual.get(field))
    if field == 'acl':
        answer['difference'] = counter_diff(expected['acl'], actual['acl'])
    else:
        answer['equal'] = expected.get(field) == actual.get(field)
    return answer


def fk_semantic(row):
    return {key: row[key] for key in SEMANTIC_FK}


def foreign_keys(manifest, phase, snapshot):
    wanted = manifest['phases'][phase]['foreign_keys']
    actual = snapshot['foreign_keys']
    difference = counter_diff([fk_semantic(row) for row in wanted],
                              [fk_semantic(row['semantic']) for row in actual])
    changed = {canonical(row['row']) for field in ('missing', 'unexpected')
               for row in difference[field]}
    # Include exact source anchors and actual OID/name/definition only for the
    # differing semantics. A count mismatch is not silently de-duplicated.
    sources = [dict(semantic=fk_semantic(row), source=row.get('source'),
                    source_line=row.get('source_line'),
                    source_fragment=row.get('source_fragment'))
               for row in wanted if canonical(fk_semantic(row)) in changed]
    objects = [row for row in actual
               if canonical(fk_semantic(row['semantic'])) in changed]
    return dict(kind='FOREIGN_KEY_SOURCE_CENSUS', phase=phase,
                difference=difference, expected_sources=sources,
                actual_constraints=objects)


def ri_record(key):
    relation, semantic, function, typ, deferred, initially, referenced = key
    return dict(relation=relation, fk_semantic=json.loads(semantic),
                function=function, trigger_type=typ, deferrable=deferred,
                initially_deferred=initially, referenced_relation=referenced)


def ri_actual_record(trigger):
    return dict(relation=trigger['relation'],
                fk_semantic=(trigger.get('constraint') or {}).get('semantic'),
                function=trigger['function'], trigger_type=trigger['trigger_type'],
                deferrable=trigger['deferrable'],
                initially_deferred=trigger['initially_deferred'],
                referenced_relation=trigger['referenced_relation'])


def internal_attachments(expected_counter, snapshot, phase):
    expected = [ri_record(key) for key, count in expected_counter.items()
                for _ in range(count)]
    triggers = [row for row in snapshot['triggers'] if row['internal']]
    difference = counter_diff(expected, [ri_actual_record(row) for row in triggers])
    changed = {canonical(row['row']) for field in ('missing', 'unexpected')
               for row in difference[field]}
    objects = [row for row in triggers if canonical(ri_actual_record(row)) in changed]
    return dict(kind='INTERNAL_ATTACHMENT_SOURCE_CENSUS', phase=phase,
                difference=difference, actual_attachments=objects)


def capture_reference(snapshot):
    raw = canonical(snapshot).encode()
    return dict(classification='ACTUAL_CAPTURE_DIAGNOSTIC_NOT_APPROVED_EXPECTED',
                canonical_capture_sha256=sha256(raw).hexdigest(), bytes=len(raw))
