"""Bound one existing dynamic SELECT from all exact trigger argument slots.

This is a source expectation over the retained catalogue, never a runtime
allowance. Neither the trigger nor the original dispatch reviewer is changed.
"""
from hashlib import sha256
import json
import re

SIGNATURE = 'erp.guard_child_by_parent_status()'
DEFINITION = dict(bytes=2937, sha256='86080f579e1b2803d1bbf50b22b14b0bf3fa168aeabf190ab3816d4b23324fce')
QUERY = "format('SELECT status::text FROM erp.%I WHERE id=$1 FOR SHARE',TG_ARGV[0])"


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def walk(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key, child
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def bind(candidate, retained, prior):
    from pglast import parse_plpgsql
    from pglast.parser import parse_sql_json
    row = candidate['functions'].get(SIGNATURE)
    require(row == retained['functions'][SIGNATURE] and pin(row[0].encode()) == DEFINITION,
            'GLOBAL_AUTOMATIC_DYNAMIC_GUARD_EXACT_RETAINED_FULL19')
    dynamic = [value for kind, value in walk(parse_plpgsql(row[0])) if kind == 'PLpgSQL_stmt_dynexecute']
    require(len(dynamic) == 1 and dynamic[0]['query']['PLpgSQL_expr']['query'] == QUERY
            and dynamic[0]['params'] == [{'PLpgSQL_expr': {'query': 'v_parent_id', 'parseMode': 2}}],
            'GLOBAL_AUTOMATIC_ONE_EXACT_DYNAMIC_SELECT_WITH_BOUND_PARAMETER')
    triggers = {key: value for key, value in candidate['triggers'].items() if value[8] == SIGNATURE}
    require(triggers == {key: value for key, value in retained['triggers'].items() if value[8] == SIGNATURE}
            and len(triggers) == 21, 'GLOBAL_AUTOMATIC_COMPLETE_EXACT_TWENTY_ONE_TRIGGER_BINDINGS')
    bindings, statements = {}, {}
    for identity, trigger in sorted(triggers.items()):
        require(len(trigger) == 16 and trigger[3] == 3, 'GLOBAL_AUTOMATIC_TRIGGER_FULL16_AND_THREE_ARGS')
        raw = bytes.fromhex(trigger[4])
        require(raw.endswith(b'\0'), 'GLOBAL_AUTOMATIC_TRIGGER_EXACT_TERMINATED_ARGS')
        arguments = raw[:-1].decode().split('\0')
        require(len(arguments) == 3 and all(re.fullmatch(r'[a-z_][a-z0-9_]*', name) for name in arguments[:2]),
                'GLOBAL_AUTOMATIC_TRIGGER_IDENTIFIER_ARGS')
        node = json.loads(parse_sql_json(trigger[9]))['stmts'][0]['stmt']['CreateTrigStmt']
        require([item['String']['sval'] for item in node['args']] == arguments
                and '.'.join(item['String']['sval'] for item in node['funcname']) + '()' == SIGNATURE
                and identity == node['relation']['schemaname'] + '.' + node['relation']['relname'] + ':' + node['trigname'],
                'GLOBAL_AUTOMATIC_TRIGGER_DDL_AND_RAW_ARGS_MUST_AGREE')
        child = identity.split(':')[0]
        parent = 'erp.' + arguments[0]
        require(parent in candidate['relations'] and candidate['columns'][parent + ':id'][2] == 'uuid'
                and candidate['columns'][child + ':' + arguments[1]][2] == 'uuid'
                and parent + ':status' in candidate['columns'], 'GLOBAL_AUTOMATIC_TRIGGER_EXACT_TYPED_PARENT_COLUMNS')
        query = 'SELECT status::text FROM erp."' + arguments[0] + '" WHERE id=$1 FOR SHARE'
        statements[query] = dict(query=query, classification='SOURCE_ONLY_IDENTICAL_FORMAT_EXPANSION_NO_EXECUTION')
        bindings[identity] = dict(full16=pin(json.dumps(trigger, separators=(',', ':')).encode()),
                                  raw_tgargs=trigger[4], arguments=arguments, parent=parent, query=query,
                                  parent_relation=candidate['relations'][parent],
                                  parent_id=candidate['columns'][parent + ':id'],
                                  parent_status=candidate['columns'][parent + ':status'])
    require(SIGNATURE not in prior['literal_dynamic_source_bounds'], 'GLOBAL_AUTOMATIC_DYNAMIC_BOUND_MUST_BE_ADDITIVE')
    prior['literal_dynamic_source_bounds'][SIGNATURE] = dict(definition=DEFINITION, dynamic_statements=1,
                                                            statements=list(statements.values()))
    return dict(status='SOURCE_EXPECTATION_ONLY_NOT_ACTUAL_TRIGGER_ACCEPTANCE', definition=DEFINITION,
                full19=row, bindings=bindings, distinct_literal_queries=len(statements),
                all_trigger_argument_slots_reviewed=True, user_supplied_identifier_interpolation=False,
                actual_SQL_executed=0, actual_ERP_cases=0, production_go=False)
