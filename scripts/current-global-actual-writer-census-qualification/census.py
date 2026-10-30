"""Offline actual-catalogue inventory. No connection, installation, or admission.

Structural catalog rows decide identities, contexts, RI and permission metadata.
The lexer only contributes positive SOURCE CANDIDATES; it never proves absence
of a writer, a dependency, a call, an effect, or an authorization path.
"""
from collections import defaultdict
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
import re

HERE = Path(__file__).resolve().parent
CONTRACT = 'cp7.global.actual-writer-census.v1'
ALL22 = ('schemas', 'relations', 'columns', 'constraints', 'indexes', 'triggers',
         'functions', 'aggregates', 'types', 'enums', 'sequences', 'policies',
         'extensions', 'roles', 'memberships', 'event_triggers', 'rules',
         'inheritance', 'default_privileges', 'database_authority',
         'type_implementation', 'sequence_ownership')
WIDTHS = dict(schemas=2, relations=13, columns=14, constraints=11, indexes=6,
              triggers=16, functions=19, types=10, sequences=7, policies=5,
              extensions=6, roles=10, memberships=3, event_triggers=5,
              rules=4, database_authority=9, type_implementation=17,
              sequence_ownership=3)
TABLE_KINDS = ('r', 'p', 'f')
IDENT = re.compile(r'[a-z_][a-z_0-9$]*\Z')
TABLE_PRIVILEGES = ('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE',
                    'REFERENCES', 'TRIGGER')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def digest(value):
    return sha256(canonical(value).encode()).hexdigest()


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'CENSUS_DUPLICATE_JSON_KEY:' + key)
        result[key] = value
    return result


def read_json(path):
    return json.loads(Path(path).read_bytes(), object_pairs_hook=unique_pairs)


def simple_relation(name):
    # Legacy all22 uses concatenated schema.name keys, not an identifier tuple.
    # Refuse ambiguous names for lock rendering instead of splitting guessed SQL.
    return type(name) is str and len(name.split('.')) == 2 and all(
        IDENT.fullmatch(part) for part in name.split('.'))


def validate_catalog(catalog):
    require(type(catalog) is dict and set(catalog) == set(ALL22), 'CENSUS_EXACT_ALL22_REQUIRED')
    for group in ALL22:
        values = catalog[group]
        require(type(values) is dict, 'CENSUS_TYPED_GROUP:' + group)
        for key, row in values.items():
            require(type(key) is str and bool(key), 'CENSUS_IDENTITY_REQUIRED:' + group)
            if group in WIDTHS:
                require(type(row) is list and len(row) == WIDTHS[group], 'CENSUS_ROW_ABI:' + group + ':' + key)
    for group in ('schemas', 'relations', 'columns', 'functions', 'roles', 'database_authority'):
        require(bool(catalog[group]), 'CENSUS_UNKNOWN_EMPTY:' + group)
    for name, row in catalog['relations'].items():
        require(type(row[0]) is str and row[0] in catalog['roles'], 'CENSUS_RELATION_OWNER_MISSING:' + name)
        require(row[1] in ('r', 'p', 'f', 'v', 'm', 'i', 'I', 'S', 'c', 't'), 'CENSUS_UNKNOWN_RELKIND:' + name)
        require(row[2] in ('p', 'u', 't'), 'CENSUS_UNKNOWN_PERSISTENCE:' + name)
        require(all(type(row[i]) is bool for i in (3, 4, 5, 8)) and type(row[12]) is list,
                'CENSUS_RELATION_METADATA_TYPES:' + name)
    ordinals = defaultdict(set)
    for key, row in catalog['columns'].items():
        table, separator, column = key.rpartition(':')
        require(separator and table in catalog['relations'] and row[0] == column,
                'CENSUS_COLUMN_IDENTITY:' + key)
        require(type(row[1]) is int and row[1] > 0 and type(row[2]) is str and type(row[3]) is bool,
                'CENSUS_COLUMN_TYPES:' + key)
        require(row[1] not in ordinals[table], 'CENSUS_DUPLICATE_COLUMN_ORDINAL:' + table)
        ordinals[table].add(row[1])
        require(row[12] is None or type(row[12]) is list, 'CENSUS_RAW_COLUMN_ACL_TYPE:' + key)
    for name, row in catalog['roles'].items():
        require(all(type(v) is bool for v in row[:7]) and type(row[7]) is int,
                'CENSUS_ROLE_TYPES:' + name)
    for name, row in catalog['memberships'].items():
        require(all(type(v) is bool for v in row), 'CENSUS_MEMBERSHIP_TYPES:' + name)
        parts = name.split(':')
        require(len(parts) == 3 and all(p in catalog['roles'] for p in parts),
                'CENSUS_MEMBERSHIP_IDENTITY:' + name)
    for name, row in catalog['functions'].items():
        require(type(row[0]) is str and bool(row[0]) and row[1] in catalog['roles']
                and type(row[2]) is str and row[3] in ('f', 'p', 'w')
                and all(type(row[i]) is bool for i in (4, 5, 6, 7))
                and row[8] in ('v', 's', 'i') and row[9] in ('u', 'r', 's')
                and (row[12] is None or type(row[12]) is list) and type(row[18]) is list,
                'CENSUS_FUNCTION19_TYPES:' + name)
    for group in ('constraints', 'triggers', 'policies', 'rules'):
        for key in catalog[group]:
            # Internal RI identities contain more colons; first separator is
            # the trigger's owning relation, not the referenced relation.
            owner = key.split(':', 1)[0]
            require(owner in catalog['relations'] or (group == 'constraints' and owner in catalog['types']),
                    'CENSUS_OBJECT_RELATION_MISSING:' + key)
    return catalog


def discover_contexts(catalog):
    """Use actual column identity/type metadata; never a schema/name allowlist."""
    result = {}
    for key, column in catalog['columns'].items():
        name, _, attr = key.rpartition(':')
        if attr not in ('transaction_id', 'txid'):
            continue
        relation = catalog['relations'][name]
        if relation[1] not in TABLE_KINDS:
            continue
        columns = {k.rpartition(':')[2]: v for k, v in catalog['columns'].items()
                   if k.rpartition(':')[0] == name}
        problems = []
        if column[2] != 'bigint':
            problems.append('WRONG_TRANSACTION_TYPE')
        if relation[1] != 'r' or relation[2] != 'p' or relation[5]:
            problems.append('NON_ORDINARY_PERSISTENT_TABLE')
        # History may intentionally have no backend/actor. Its transaction
        # column is evidence of a candidate, never evidence it is ephemeral.
        result[name] = dict(transaction_columns={k: v for k, v in columns.items()
                                               if k in ('txid', 'transaction_id')},
                            column_rows=columns, relation_row=relation,
                            issues=problems, active_authority='UNKNOWN', ephemeral=False)
    require(bool(result), 'CENSUS_UNKNOWN_EMPTY_CONTEXT_INVENTORY')
    return result


def tokens(text):
    """Small lossless-position SQL lexer, deliberately not a dependency parser.

    Comments and strings cannot create positive relation/call observations.
    Dollar-quoted bodies are retained as string tokens for separate scanning.
    Unexpected/unterminated syntax refuses or remains UNKNOWN; it is not safe.
    """
    out = []
    i = 0
    while i < len(text):
        start = i
        ch = text[i]
        if ch.isspace():
            i += 1
        elif text.startswith('--', i):
            end = text.find('\n', i + 2)
            i = len(text) if end < 0 else end + 1
        elif text.startswith('/*', i):
            i += 2
            depth = 1
            while i < len(text) and depth:
                if text.startswith('/*', i):
                    depth += 1; i += 2
                elif text.startswith('*/', i):
                    depth -= 1; i += 2
                else:
                    i += 1
            require(depth == 0, 'CENSUS_UNTERMINATED_SQL_COMMENT')
        elif ch in ('"', "'"):
            quote = ch
            escaped = quote == "'" and i > 0 and text[i - 1] in 'eE' and (
                i < 2 or not (text[i - 2].isalnum() or text[i - 2] in '_$'))
            i += 1
            value = ''
            while i < len(text):
                if text[i] == quote:
                    if i + 1 < len(text) and text[i + 1] == quote:
                        value += quote; i += 2
                    else:
                        i += 1; break
                elif text[i] == '\\' and escaped:
                    value += text[i:i + 2]; i += 2
                else:
                    value += text[i]; i += 1
            else:
                raise ValueError('CENSUS_UNTERMINATED_SQL_QUOTE')
            out.append(('ident' if quote == '"' else 'string', value, start))
        elif ch == '$' and (match := re.match(r'\$(?:[A-Za-z_][A-Za-z_0-9]*)?\$', text[i:])):
            marker = match[0]
            end = text.find(marker, i + len(marker))
            require(end >= 0, 'CENSUS_UNTERMINATED_DOLLAR_BODY')
            out.append(('body', text[i + len(marker):end], start))
            i = end + len(marker)
        elif ch.isalpha() or ch == '_':
            i += 1
            while i < len(text) and (text[i].isalnum() or text[i] in '_$'):
                i += 1
            out.append(('word', text[start:i].lower(), start))
        else:
            out.append(('symbol', ch, start)); i += 1
    return out


def qualified_at(stream, i):
    if i >= len(stream) or stream[i][0] not in ('word', 'ident'):
        return None, i
    pieces = [stream[i][1]]
    end = i + 1
    while end + 1 < len(stream) and stream[end][1] == '.' and stream[end + 1][0] in ('word', 'ident'):
        pieces.append(stream[end + 1][1]); end += 2
    return '.'.join(pieces), end


def function_candidates(name, row, relation_names, function_names):
    issues = set()
    try:
        outer = tokens(row[0])
    except ValueError as error:
        return dict(function=name, full_function19_row=row, row_sha256=digest(row),
                    relation_candidates=[], call_candidates=[], write_candidates=[],
                    issues=['SOURCE_LEXING_UNRESOLVED', str(error)],
                    completeness='UNKNOWN_SOURCE_CANDIDATES_ONLY')
    bodies = [token[1] for token in outer if token[0] == 'body']
    if row[2] not in ('sql', 'plpgsql'):
        issues.add('OPAQUE_LANGUAGE')
    if len(bodies) != 1:
        issues.add('BODY_NOT_SINGLE_DOLLAR_QUOTED')
    try:
        stream = tokens(bodies[0]) if len(bodies) == 1 else outer
    except ValueError as error:
        return dict(function=name, full_function19_row=row, row_sha256=digest(row),
                    relation_candidates=[], call_candidates=[], write_candidates=[],
                    issues=['SOURCE_LEXING_UNRESOLVED', str(error)],
                    completeness='UNKNOWN_SOURCE_CANDIDATES_ONLY')
    refs, calls, writes = set(), set(), []
    for i, token in enumerate(stream):
        if token[0] not in ('word', 'ident'):
            continue
        value = token[1]
        target, end = qualified_at(stream, i)
        if target in relation_names:
            refs.add(target)
        if end < len(stream) and stream[end][1] == '(' and target in function_names:
            calls.update(function_names[target])
        if token[0] == 'word' and value == 'execute':
            issues.add('DYNAMIC_EXECUTE_UNRESOLVED')
        if token[0] == 'word' and value in ('nextval', 'setval'):
            issues.add('SEQUENCE_EFFECT_CANDIDATE')
        if target in ('pg_catalog.nextval', 'pg_catalog.setval'):
            issues.add('SEQUENCE_EFFECT_CANDIDATE')
        op, offset = None, i + 1
        next_word = stream[offset][1] if offset < len(stream) else None
        if token[0] == 'word':
            if value in ('insert', 'merge') and next_word == 'into':
                op = value.upper(); offset += 1
            elif value == 'delete' and next_word == 'from':
                op = 'DELETE'; offset += 1
            elif value == 'update' and next_word not in ('of', 'set', 'or', 'skip', 'nowait'):
                op = 'UPDATE'
            elif value == 'truncate':
                op = 'TRUNCATE'; offset += next_word == 'table'
            elif value == 'copy':
                op = 'COPY_DIRECTION_UNREVIEWED'
        if op:
            if offset < len(stream) and stream[offset][1] == 'only':
                offset += 1
            relation, _ = qualified_at(stream, offset)
            if relation in relation_names:
                writes.append(dict(operation=op, relation=relation, offset=token[2]))
            else:
                issues.add('UNRESOLVED_WRITE_TARGET')
                writes.append(dict(operation=op, relation=None, token=relation, offset=token[2]))
    # Even no token hits is UNKNOWN: overloaded/unqualified calls, generated
    # SQL, operators/casts/defaults and procedural control need actual review.
    return dict(function=name, full_function19_row=row, row_sha256=digest(row),
                relation_candidates=sorted(refs), call_candidates=sorted(calls),
                write_candidates=writes, issues=sorted(issues),
                completeness='UNKNOWN_SOURCE_CANDIDATES_ONLY')


def fk_candidates(catalog):
    result = {}
    for name, row in catalog['constraints'].items():
        if row[0] != 'f':
            continue
        stream = tokens(row[10])
        target = None
        for i, token in enumerate(stream):
            if token[0] == 'word' and token[1] == 'references':
                target, _ = qualified_at(stream, i + 1)
                break
        source = name.split(':', 1)[0]
        result[name] = dict(source=source, target=target, full_constraint11_row=row,
                            resolved_in_supplied_catalog=target in catalog['relations'],
                            identity_source='ACTUAL_CONSTRAINT_ROW_PLUS_DEFINITION_TOKEN_CANDIDATE',
                            structural_confrelid_observed=False)
    return result


def raw_authority_inventory(catalog, contexts, raw):
    """Validate the existing parent runner ABI without normalizing NULL ACLs."""
    if raw is None:
        return dict(status='UNKNOWN_MISSING_RAW_AUTHORITY', captured=None,
                    covers_global_functions=False, complete_context_matrix=False)
    require(type(raw) is dict and set(raw) == {'schemas', 'relations', 'columns', 'effective_role_table_privileges'},
            'CENSUS_PARENT_RAW_AUTHORITY_ABI')
    widths = dict(schemas=3, relations=7, columns=4, effective_role_table_privileges=4)
    for group, width in widths.items():
        require(type(raw[group]) is list and all(type(row) is list and len(row) == width for row in raw[group]),
                'CENSUS_RAW_AUTHORITY_ROW_ABI:' + group)
    def keyed(rows, key):
        result = {key(row): row for row in rows}
        require(len(result) == len(rows), 'CENSUS_DUPLICATE_RAW_AUTHORITY')
        return result
    tables = keyed(raw['relations'], lambda row: row[0])
    schemas = keyed(raw['schemas'], lambda row: row[0])
    columns = keyed(raw['columns'], lambda row: (row[0], row[2]))
    privileges = keyed(raw['effective_role_table_privileges'], lambda row: tuple(row[:3]))
    require(set(tables) == set(contexts), 'CENSUS_RAW_CONTEXT_RELATION_COVERAGE')
    require(set(schemas) == {name.split('.', 1)[0] for name in contexts}, 'CENSUS_RAW_CONTEXT_SCHEMA_COVERAGE')
    expected_columns = {(key.rpartition(':')[0], key.rpartition(':')[2]) for key in catalog['columns']
                        if key.rpartition(':')[0] in contexts}
    require(set(columns) == expected_columns, 'CENSUS_RAW_CONTEXT_COLUMN_COVERAGE')
    expected_matrix = {(role, table, privilege) for role in catalog['roles'] for table in contexts
                       for privilege in TABLE_PRIVILEGES}
    require(set(privileges) == expected_matrix and all(type(row[3]) is bool for row in privileges.values()),
            'CENSUS_RAW_CONTEXT_EFFECTIVE_MATRIX_COVERAGE')
    for name, row in tables.items():
        expected = catalog['relations'][name]
        require(row[1:6] == [expected[0], expected[1], expected[2], expected[3], expected[4]],
                'CENSUS_RAW_RELATION_METADATA_DRIFT:' + name)
        require(row[6] is None or type(row[6]) is str, 'CENSUS_RAW_RELATION_ACL_TYPE:' + name)
    for name, row in schemas.items():
        require(row[1] == catalog['schemas'][name][0] and (row[2] is None or type(row[2]) is str),
                'CENSUS_RAW_SCHEMA_METADATA_DRIFT:' + name)
    for (table, column), row in columns.items():
        require(type(row[1]) is int and row[1] > 0 and (row[3] is None or type(row[3]) is str),
                'CENSUS_RAW_COLUMN_METADATA_TYPE:' + table + ':' + column)
        expected = catalog['columns'][table + ':' + column][12]
        require((row[3] is None) == (expected is None), 'CENSUS_RAW_COLUMN_NULL_STATE_DRIFT')
    return dict(status='EXACT_PARENT_CONTEXT_RAW_METADATA_ONLY', captured=deepcopy(raw),
                captured_sha256=digest(raw), raw_null_empty_preserved=True,
                complete_context_matrix=True, context_count=len(contexts),
                effective_rows=len(privileges), covers_global_functions=False,
                covers_MAINTAIN=False, covers_schema_usage_create=False,
                covers_effective_column_privileges=False, execution_permission_qualified=False)


def preview_lock_sql(names):
    require(bool(names) and len(names) == len(set(names)), 'CENSUS_UNKNOWN_EMPTY_OR_DUPLICATE_LOCKSET')
    require(all(simple_relation(name) for name in names), 'CENSUS_AMBIGUOUS_LOCK_IDENTIFIER')
    ordered = sorted(names, key=lambda name: tuple(part.encode('utf-8') for part in name.split('.')))
    targets = ', '.join('"' + name.replace('.', '"."') + '"' for name in ordered)
    return 'LOCK TABLE ' + targets + ' IN EXCLUSIVE MODE NOWAIT;'


def analyze(catalog, *, expected_contexts, raw_authority=None, supplement=None, roots=None, provenance=None):
    catalog = validate_catalog(catalog)
    require(type(expected_contexts) is list and expected_contexts
            and len(expected_contexts) == len(set(expected_contexts))
            and all(type(v) is str for v in expected_contexts), 'CENSUS_PINNED_NONEMPTY_EXPECTED_CONTEXTS_REQUIRED')
    roots = read_json(HERE / 'ROOTS.json') if roots is None else deepcopy(roots)
    require(roots.get('runtime_entry') is None and roots.get('seed_lockset_qualified') is False
            and roots.get('production_go') is False, 'CENSUS_CLOSED_ROOTS_REQUIRED')
    contexts = discover_contexts(catalog)
    missing_contexts = sorted(set(expected_contexts) - set(contexts))
    unexpected_contexts = sorted(set(contexts) - set(expected_contexts))
    by_name = defaultdict(list)
    for name in catalog['functions']:
        by_name[name.split('(', 1)[0]].append(name)
    scans = {name: function_candidates(name, row, catalog['relations'], by_name)
             for name, row in sorted(catalog['functions'].items())}
    fks = fk_candidates(catalog)
    supplemental_proof = None
    if supplement is not None:
        import importlib.util
        spec = importlib.util.spec_from_file_location('global_census_supplement_validator', HERE / 'capture.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        supplemental_proof = module.validate(supplement, catalog)
        for name, row in supplement['groups']['foreign_keys'].items():
            fks[name].update(source=row[1], target=row[2], resolved_in_supplied_catalog=True,
                             structural_confrelid_observed=True, structural_row=row,
                             identity_source='ACTUAL_PG_CONSTRAINT_OID_ENDPOINTS')
    view_refs = {}
    for name, row in catalog['relations'].items():
        if row[1] in ('v', 'm'):
            stream = tokens(row[9] or '')
            view_refs[name] = {target for i in range(len(stream))
                               if (target := qualified_at(stream, i)[0]) in catalog['relations']}
    if supplement is not None:
        for row in supplement['groups']['view_relation_dependencies'].values():
            view_refs.setdefault(row[0], set()).add(row[5])
    root_functions = roots['actual19_function_roots'] + roots['owning_hook_roots']
    missing_roots = sorted(set(root_functions) - set(scans))
    functions = set(root_functions) & set(scans)
    outward_functions = set(functions)
    while True:
        previous_count = len(outward_functions)
        outward_functions.update(called for name in tuple(outward_functions) for called in scans[name]['call_candidates'])
        if len(outward_functions) == previous_count:
            break
    outward_relations = set(roots['seed_relations']) | set(roots['read_view_roots'])
    outward_relations.update(table for name in outward_functions for table in scans[name]['relation_candidates'])
    relations = set(roots['seed_relations']) | set(roots['read_view_roots'])
    missing_relations = sorted(relations - set(catalog['relations']))
    relations &= set(catalog['relations'])
    reasons = defaultdict(set)
    for name in relations:
        reasons[name].add('REVIEW_ROOT')
    # A conservative finite superset is review material, never proof that all
    # executable calls or relationships have been discovered. Both FK endpoints
    # matter; referenced rows can be KEY SHARE owners held by another writer.
    changed = True
    while changed:
        previous = (len(functions), len(relations))
        for function in tuple(functions):
            scan = scans[function]
            functions.update(scan['call_candidates'])
            for table in scan['relation_candidates']:
                relations.add(table); reasons[table].add('FUNCTION_REFERENCE_CANDIDATE')
        for edge in fks.values():
            if edge['source'] in relations or edge['target'] in relations:
                for table in (edge['source'], edge['target']):
                    if table in catalog['relations']:
                        relations.add(table); reasons[table].add('BIDIRECTIONAL_FK_ENDPOINT_CANDIDATE')
        for name in tuple(relations):
            for table in view_refs.get(name, ()):
                if table in catalog['relations']:
                    relations.add(table); reasons[table].add('VIEW_OR_RULE_DEPENDENCY_CANDIDATE')
        for key, parent in catalog['inheritance'].items():
            child = key.rpartition(':')[0]
            if parent in relations or child in relations:
                for table in (parent, child):
                    if table in catalog['relations']:
                        relations.add(table); reasons[table].add('INHERITANCE_ENDPOINT_CANDIDATE')
        for key, trigger in catalog['triggers'].items():
            if key.split(':', 1)[0] in relations and trigger[8] in scans:
                functions.add(trigger[8])
        # Callers are candidates even if their own body has no direct write.
        for name, scan in scans.items():
            if any(write['relation'] in relations for write in scan['write_candidates']) or functions.intersection(scan['call_candidates']):
                functions.add(name)
        changed = previous != (len(functions), len(relations))
    # Include all captured metadata; no schema filter or name-based safety.
    raw = raw_authority_inventory(catalog, contexts, raw_authority)
    lockset = sorted(name for name in relations if catalog['relations'][name][1] in ('r', 'p'))
    unsupported = sorted(name for name in relations if catalog['relations'][name][1] == 'f'
                         or (catalog['relations'][name][1] in TABLE_KINDS and catalog['relations'][name][2] != 'p')
                         or not simple_relation(name))
    blockers = ['SOURCE_TOKENS_NEVER_PROVE_WRITER_OR_CALL_CLOSURE',
                'RAW_GLOBAL_FUNCTION_SCHEMA_RELATION_ACLS_NOT_CAPTURED',
                'STRUCTURAL_DEPENDENCY_OIDS_NOT_CAPTURED',
                'ACTUAL_COMPOSITE_GLOBAL_RUNTIME_AND_TWO_SESSION_PROOFS_MISSING',
                'AUTHORITY_AFTER_PRIOR_WAIT_AND_BEFORE_FIRST_EFFECT_NOT_PROVEN',
                'CATALOGUE_SCOPE_EXCLUDES_SYSTEM_AND_CRON_NO_EXTERNAL_WRITER_CLOSURE',
                'REVIEW_LOCKSET_UNAPPROVED_AND_NOT_EXECUTED']
    if missing_roots: blockers.append('CURRENT_OWNING_OR_ACTUAL19_HOOKS_MISSING')
    if missing_relations: blockers.append('REVIEW_ROOT_RELATIONS_MISSING')
    if missing_contexts or unexpected_contexts: blockers.append('EXPECTED_CONTEXT_MEMBERSHIP_CHANGED')
    if any(row['issues'] for row in contexts.values()): blockers.append('CONTEXT_TYPE_OR_PERSISTENCE_UNREVIEWED')
    if raw_authority is None: blockers.append('RAW_CONTEXT_AUTHORITY_NOT_CAPTURED')
    if unsupported: blockers.append('NONORDINARY_OR_AMBIGUOUS_RELATION_UNREVIEWED')
    if supplement is not None:
        blockers.remove('RAW_GLOBAL_FUNCTION_SCHEMA_RELATION_ACLS_NOT_CAPTURED')
        blockers.remove('STRUCTURAL_DEPENDENCY_OIDS_NOT_CAPTURED')
        blockers.append('SUPPLEMENT_CALLER_FULL_CATALOGUE_ROWS_SEQUENCES_AND_RESTORE_EVIDENCE_REQUIRED')
    dynamic = sorted(name for name, scan in scans.items() if 'DYNAMIC_EXECUTE_UNRESOLVED' in scan['issues'])
    if dynamic: blockers.append('DYNAMIC_SQL_REMAINS_UNKNOWN')
    result = dict(contract=CONTRACT, classification='ACTUAL_CATALOGUE_FINITE_REVIEW_INVENTORY_ONLY',
        provenance=provenance, catalogue_sha256=digest(catalog),
        catalogue_group_counts={name: len(catalog[name]) for name in ALL22},
        # This is the complete supplied metadata, not raw business rows.
        retained_actual_all22=catalog, raw_context_authority=raw,
        supplemental_capture=supplement, supplemental_metadata_proof=supplemental_proof,
        contexts=contexts, context_membership=dict(expected=sorted(expected_contexts),
            missing=missing_contexts, unexpected=unexpected_contexts),
        functions=scans, all_dynamic_sql_candidates=dynamic,
        fk_candidates=fks, missing_root_functions=missing_roots, missing_root_relations=missing_relations,
        review_function_candidates=sorted(functions),
        outward_root_function_candidates=sorted(outward_functions),
        outward_root_relation_candidates=sorted(outward_relations),
        inventory_layer_meanings=dict(outward='Positive reference candidates reachable from exact review roots.',
            maximal='Adds candidate callers, triggers, bidirectional FKs and inheritance; can include unrelated ERP domains.',
            neither='Neither layer is a complete or approved barrier set; both require actual review and run evidence.'),
        review_relation_candidates={name: dict(actual_row=catalog['relations'][name],
            reasons=sorted(reasons[name]), disposition='UNREVIEWED') for name in sorted(relations)},
        review_lockset=lockset, review_lockset_sha256=digest(lockset),
        lock_sql_preview=preview_lock_sql(lockset) if lockset and not unsupported else None,
        lock_sql_preview_executed=False, unsupported_relation_candidates=unsupported,
        role_inheritance_retained=True, RLS_policy_metadata_retained=True,
        view_trigger_FK_rules_retained=True, full_function19_metadata_retained=True,
        all_contexts_ephemeral=False, current_context_row_authority='UNKNOWN',
        writer_or_phantom_lock_closed=False, permission_closure='UNKNOWN',
        required_final_parent=None, runtime_entry=None, actual_Native_credit=0,
        production_go=False, independent_acceptance=False, blockers=sorted(blockers))
    result['inventory_sha256'] = digest(result)
    return result


def summary(report):
    return {key: report[key] for key in ('contract', 'classification', 'provenance',
        'catalogue_sha256', 'catalogue_group_counts', 'inventory_sha256',
        'context_membership', 'missing_root_functions', 'missing_root_relations',
        'review_lockset', 'review_lockset_sha256', 'unsupported_relation_candidates',
        'blockers', 'runtime_entry', 'actual_Native_credit', 'production_go',
        'independent_acceptance')} | dict(contexts=len(report['contexts']),
        function_candidates=len(report['review_function_candidates']),
        relation_candidates=len(report['review_relation_candidates']),
        dynamic_sql_candidates=len(report['all_dynamic_sql_candidates']),
        functions_with_write_candidates=sum(bool(row['write_candidates']) for row in report['functions'].values()),
        raw_authority_status=report['raw_context_authority']['status'])


def require_runtime(*args, **kwargs):
    raise ValueError('GLOBAL_RUNTIME_CLOSED_ACTUAL_CENSUS_IS_NOT_EXECUTION_QUALIFICATION')
