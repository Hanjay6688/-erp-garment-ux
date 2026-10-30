"""Mutation controls for the offline census; synthetic inputs are NOT ERP proof."""
from copy import deepcopy
from types import SimpleNamespace
import json
import unittest
import census
import capture


def function(body='begin insert into erp.lots(id) values(1); end', **changes):
    row = ['CREATE OR REPLACE FUNCTION erp.writer() RETURNS void LANGUAGE plpgsql AS $fn$' + body + '$fn$;',
           'owner', 'plpgsql', 'f', True, False, False, False, 'v', 'u', '100', '0',
           ['search_path=""'], None, None, '', 'void', '-', [['owner', 'owner', 'EXECUTE', False]]]
    for key, value in changes.items():
        row[int(key)] = value
    return row


def fixture():
    catalog = {name: {} for name in census.ALL22}
    catalog['schemas'] = {'erp': ['owner', []]}
    catalog['roles'] = {'owner': [False, True, False, False, False, False, False, -1, None, 'hash'],
                        'reader': [False, True, False, False, True, False, False, -1, None, 'hash']}
    catalog['database_authority'] = {'CURRENT': ['owner', 'UTF8', 'C', 'C', -1, False, True, [], None]}
    catalog['relations'] = {name: ['owner', 'r', 'p', False, False, False, 'd', None, True, None, None, None, []]
                            for name in ('erp.lots', 'erp.history')}
    def column(name, ordinal, kind):
        return [name, ordinal, kind, True, '', '', 'p', '', -1, None, None, '-', None, None]
    catalog['columns'] = {'erp.lots:id': column('id', 1, 'bigint'),
                          'erp.history:transaction_id': column('transaction_id', 1, 'bigint')}
    catalog['functions'] = {'erp.writer()': function()}
    return catalog


ROOTS = dict(seed_relations=['erp.lots'], actual19_function_roots=['erp.writer()'],
             owning_hook_roots=[], read_view_roots=[], seed_lockset_qualified=False,
             runtime_entry=None, production_go=False)


def run(catalog=None, **kwargs):
    return census.analyze(fixture() if catalog is None else catalog,
                          expected_contexts=kwargs.pop('expected_contexts', ['erp.history']),
                          roots=kwargs.pop('roots', ROOTS), **kwargs)


def raw_authority(catalog, relation_acl=None):
    names = census.discover_contexts(catalog)
    return dict(schemas=[['erp', 'owner', None]],
        relations=[[name, *catalog['relations'][name][:5], relation_acl] for name in names],
        columns=[[key.rpartition(':')[0], row[1], row[0], None] for key, row in catalog['columns'].items()
                 if key.rpartition(':')[0] in names],
        effective_role_table_privileges=[[role, table, p, False] for role in catalog['roles']
            for table in names for p in census.TABLE_PRIVILEGES])


def supplemental_fixture(catalog):
    """A validator control, never actual metadata or an ERP witness."""
    groups = {name: {} for name in capture.QUERIES}
    groups['schemas'] = {name: ['100', row[0], None] for name, row in catalog['schemas'].items()}
    groups['relations'] = {name: [str(200 + i), *name.split('.'), *row[:6], None]
                           for i, (name, row) in enumerate(catalog['relations'].items())}
    groups['columns'] = {name: [groups['relations'][name.rpartition(':')[0]][0], row[1], row[0], row[2], None]
                         for name, row in catalog['columns'].items()}
    groups['functions'] = {name: [str(300 + i), name.split('.')[0], row[1], None]
                           for i, (name, row) in enumerate(catalog['functions'].items())}
    groups['roles'] = {name: [str(400 + i), *row] for i, (name, row) in enumerate(catalog['roles'].items())}
    groups['memberships'] = {name: ['400', '401', '400', *row] for name, row in catalog['memberships'].items()}
    groups['database_authority'] = {'CURRENT': ['500', 'owner', None]}
    groups['dependencies'] = {name: ['pg_proc', row[0], 0, 'pg_namespace', '100', 0, 'n', name, 'schema erp']
                              for name, row in groups['functions'].items()}
    for role in catalog['roles']:
        for schema in catalog['schemas']:
            for p in ('USAGE', 'CREATE'):
                groups['effective_schema_privileges'][role + ':' + schema + ':' + p] = False
        for table in catalog['relations']:
            for p in (*census.TABLE_PRIVILEGES, 'MAINTAIN'):
                groups['effective_table_privileges'][role + ':' + table + ':' + p] = False
        for function_name in catalog['functions']:
            groups['effective_function_privileges'][role + ':' + function_name] = False
        for p in ('CREATE', 'CONNECT', 'TEMPORARY'):
            groups['effective_database_privileges'][role + ':' + p] = False
    return dict(contract=capture.CONTRACT, catalogue_sha256=census.digest(catalog), groups=groups,
                runtime_entry=None, actual_Native_credit=0, production_go=False, independent_acceptance=False,
                transaction_writes=False, caller_full_catalogue_data_sequence_bracket_required=True,
                caller_outer_restoration_required=True)


class CensusControls(unittest.TestCase):
    def test_empty_catalogue_never_safe(self):
        with self.assertRaisesRegex(ValueError, 'UNKNOWN_EMPTY'):
            run({name: {} for name in census.ALL22})

    def test_missing_group_refused(self):
        c = fixture(); del c['roles']
        with self.assertRaisesRegex(ValueError, 'EXACT_ALL22'):
            run(c)

    def test_duplicate_json_identity_refused(self):
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_JSON'):
            json.loads('{"roles":{},"roles":{}}', object_pairs_hook=census.unique_pairs)

    def test_full_function19_required(self):
        c = fixture(); c['functions']['erp.writer()'].pop()
        with self.assertRaisesRegex(ValueError, 'ROW_ABI:functions'):
            run(c)

    def test_wrong_typed_security_flag_refused(self):
        c = fixture(); c['functions']['erp.writer()'][4] = 'true'
        with self.assertRaisesRegex(ValueError, 'FUNCTION19_TYPES'):
            run(c)

    def test_function_metadata_change_fingerprinted(self):
        a = run(); c = fixture(); c['functions']['erp.writer()'][10] = '101'
        self.assertNotEqual(a['catalogue_sha256'], run(c)['catalogue_sha256'])

    def test_nonempty_expected_contexts_required(self):
        with self.assertRaisesRegex(ValueError, 'NONEMPTY_EXPECTED_CONTEXTS'):
            run(expected_contexts=[])

    def test_missing_actual_context_is_not_safe_empty(self):
        c = fixture(); c['columns']['erp.history:id'] = c['columns'].pop('erp.history:transaction_id')
        c['columns']['erp.history:id'][0] = 'id'
        with self.assertRaisesRegex(ValueError, 'EMPTY_CONTEXT'):
            run(c)

    def test_foreign_schema_transaction_table_detected(self):
        c = fixture(); c['schemas']['unknown'] = ['owner', []]
        c['relations']['unknown.new_context'] = deepcopy(c['relations']['erp.history'])
        c['columns']['unknown.new_context:txid'] = deepcopy(c['columns']['erp.history:transaction_id'])
        c['columns']['unknown.new_context:txid'][0] = 'txid'
        result = run(c)
        self.assertEqual(result['context_membership']['unexpected'], ['unknown.new_context'])
        self.assertIn('EXPECTED_CONTEXT_MEMBERSHIP_CHANGED', result['blockers'])

    def test_wrong_context_type_remains_visible_unknown(self):
        c = fixture(); c['columns']['erp.history:transaction_id'][2] = 'text'
        result = run(c)
        self.assertIn('WRONG_TRANSACTION_TYPE', result['contexts']['erp.history']['issues'])
        self.assertEqual(result['current_context_row_authority'], 'UNKNOWN')

    def test_foreign_partitioned_and_unlogged_contexts_not_silently_omitted(self):
        for kind, persistence, partition in (('f', 'p', False), ('p', 'p', False), ('r', 'u', False), ('r', 'p', True)):
            with self.subTest(kind=kind, persistence=persistence, partition=partition):
                c = fixture(); row = c['relations']['erp.history']; row[1:3] = [kind, persistence]; row[5] = partition
                self.assertIn('NON_ORDINARY_PERSISTENT_TABLE', run(c)['contexts']['erp.history']['issues'])

    def test_column_identity_not_inferred_from_regex(self):
        c = fixture(); c['columns']['erp.history:transaction_id'][0] = 'pretend'
        with self.assertRaisesRegex(ValueError, 'COLUMN_IDENTITY'):
            run(c)

    def test_history_never_marked_ephemeral(self):
        result = run()
        self.assertFalse(result['all_contexts_ephemeral'])
        self.assertFalse(result['contexts']['erp.history']['ephemeral'])

    def test_dynamic_sql_remains_unknown_with_no_static_target(self):
        c = fixture(); c['functions']['erp.writer()'] = function("begin execute format('insert into %I.%I values(1)',s,t); end")
        result = run(c)
        self.assertEqual(result['all_dynamic_sql_candidates'], ['erp.writer()'])
        self.assertIn('DYNAMIC_SQL_REMAINS_UNKNOWN', result['blockers'])
        self.assertFalse(result['writer_or_phantom_lock_closed'])

    def test_no_positive_token_is_not_no_writer_proof(self):
        c = fixture(); c['functions']['erp.writer()'] = function('begin perform mysterious(); end')
        row = run(c)['functions']['erp.writer()']
        self.assertEqual(row['write_candidates'], [])
        self.assertEqual(row['completeness'], 'UNKNOWN_SOURCE_CANDIDATES_ONLY')

    def test_lexer_failure_retains_full19_unknown(self):
        c = fixture(); c['functions']['erp.writer()'] = function("begin execute 'unfinished; end")
        result = run(c)['functions']['erp.writer()']
        self.assertIn('SOURCE_LEXING_UNRESOLVED', result['issues'])
        self.assertEqual(result['full_function19_row'], c['functions']['erp.writer()'])

    def test_comments_and_string_decoys_not_reported_as_writes(self):
        c = fixture(); c['functions']['erp.writer()'] = function("begin /* outer /* insert into erp.lots */ */ perform 'delete from erp.lots'; -- update erp.lots\nend")
        self.assertEqual(run(c)['functions']['erp.writer()']['write_candidates'], [])

    def test_quoted_qualified_static_target_is_a_candidate(self):
        c = fixture(); c['functions']['erp.writer()'] = function('begin insert into "erp"."lots" values(1); end')
        row = run(c)['functions']['erp.writer()']
        self.assertEqual(row['write_candidates'][0]['relation'], 'erp.lots')

    def test_plain_and_escape_strings_do_not_hide_real_target(self):
        c = fixture(); c['functions']['erp.writer()'] = function("begin perform '\\'; perform E'\\\''; insert into erp.lots values(1); end")
        self.assertEqual(run(c)['functions']['erp.writer()']['write_candidates'][0]['relation'], 'erp.lots')

    def test_unqualified_write_target_is_unknown(self):
        c = fixture(); c['functions']['erp.writer()'] = function('begin insert into lots values(1); end')
        self.assertIn('UNRESOLVED_WRITE_TARGET', run(c)['functions']['erp.writer()']['issues'])

    def test_recursive_call_graph_terminates_without_proving_closure(self):
        c = fixture(); c['functions']['erp.writer()'] = function('begin perform erp.other(); end')
        c['functions']['erp.other()'] = function('begin perform erp.writer(); end')
        result = run(c)
        self.assertEqual(result['review_function_candidates'], ['erp.other()', 'erp.writer()'])
        self.assertFalse(result['writer_or_phantom_lock_closed'])

    def test_missing_current_hook_visible(self):
        roots = deepcopy(ROOTS); roots['owning_hook_roots'] = ['erp.missing()']
        result = run(roots=roots)
        self.assertEqual(result['missing_root_functions'], ['erp.missing()'])

    def test_fk_reference_expands_both_directions(self):
        c = fixture(); c['constraints']['erp.history:fk'] = ['f', False, False, True, True, 0, True, None, None, 'erp.history', 'FOREIGN KEY (transaction_id) REFERENCES erp.lots(id)']
        result = run(c)
        self.assertIn('erp.history', result['review_lockset'])
        self.assertFalse(result['fk_candidates']['erp.history:fk']['structural_confrelid_observed'])

    def test_trigger_function_writer_expands_relation_candidates(self):
        c = fixture(); c['functions']['erp.trigger_fn()'] = function('begin insert into erp.history values(1); end')
        c['triggers']['erp.lots:trigger'] = [False, 'O', 5, 0, '', [], False, False, 'erp.trigger_fn()', 'CREATE TRIGGER trigger AFTER INSERT ON erp.lots EXECUTE FUNCTION erp.trigger_fn()', None, None, None, None, None, None]
        result = run(c)
        self.assertIn('erp.history', result['review_lockset'])

    def test_full_role_inherit_graph_and_RLS_retained(self):
        c = fixture(); c['memberships']['owner:reader:owner'] = [False, False, True]
        c['relations']['erp.lots'][3:5] = [True, True]
        c['policies']['erp.lots:no_access'] = ['*', True, ['reader'], 'false', 'false']
        result = run(c)
        self.assertEqual(result['retained_actual_all22']['memberships'], c['memberships'])
        self.assertEqual(result['retained_actual_all22']['policies'], c['policies'])
        self.assertEqual(result['permission_closure'], 'UNKNOWN')

    def test_role_boolean_change_fingerprinted(self):
        c = fixture(); c['roles']['reader'][1] = False
        self.assertNotEqual(run()['inventory_sha256'], run(c)['inventory_sha256'])

    def test_raw_acl_null_and_empty_are_distinct(self):
        c = fixture(); a = run(c, raw_authority=raw_authority(c, None)); b = run(c, raw_authority=raw_authority(c, '{}'))
        self.assertNotEqual(a['raw_context_authority']['captured_sha256'], b['raw_context_authority']['captured_sha256'])
        self.assertIsNone(a['raw_context_authority']['captured']['relations'][0][-1])
        self.assertEqual(b['raw_context_authority']['captured']['relations'][0][-1], '{}')

    def test_missing_effective_permission_cell_refused(self):
        c = fixture(); raw = raw_authority(c); raw['effective_role_table_privileges'].pop()
        with self.assertRaisesRegex(ValueError, 'EFFECTIVE_MATRIX_COVERAGE'):
            run(c, raw_authority=raw)

    def test_unknown_role_permission_cell_refused(self):
        c = fixture(); raw = raw_authority(c); raw['effective_role_table_privileges'][0][0] = 'not_a_role'
        with self.assertRaisesRegex(ValueError, 'EFFECTIVE_MATRIX_COVERAGE'):
            run(c, raw_authority=raw)

    def test_string_permission_bool_refused(self):
        c = fixture(); raw = raw_authority(c); raw['effective_role_table_privileges'][0][3] = 'false'
        with self.assertRaisesRegex(ValueError, 'EFFECTIVE_MATRIX_COVERAGE'):
            run(c, raw_authority=raw)

    def test_duplicate_permission_cell_refused(self):
        c = fixture(); raw = raw_authority(c); raw['effective_role_table_privileges'].append(raw['effective_role_table_privileges'][0])
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_RAW_AUTHORITY'):
            run(c, raw_authority=raw)

    def test_raw_column_null_empty_drift_refused(self):
        c = fixture(); raw = raw_authority(c); raw['columns'][0][3] = '{}'
        with self.assertRaisesRegex(ValueError, 'RAW_COLUMN_NULL_STATE_DRIFT'):
            run(c, raw_authority=raw)

    def test_lock_preview_sorted_exclusive_nowait_not_executed(self):
        value = census.preview_lock_sql(['erp.z', 'aa.a', 'erp.a'])
        self.assertEqual(value, 'LOCK TABLE "aa"."a", "erp"."a", "erp"."z" IN EXCLUSIVE MODE NOWAIT;')
        self.assertFalse(run()['lock_sql_preview_executed'])

    def test_empty_duplicate_ambiguous_lock_identifiers_refused(self):
        for names in ([], ['erp.x', 'erp.x'], ['erp.x;SELECT pg_sleep(1)'], ['a.b.c']):
            with self.subTest(names=names), self.assertRaises(ValueError):
                census.preview_lock_sql(names)

    def test_runtime_is_always_closed_even_after_inventory(self):
        with self.assertRaisesRegex(ValueError, 'RUNTIME_CLOSED'):
            census.require_runtime(run())

    def test_capture_refuses_host_before_any_query(self):
        cursor = SimpleNamespace(connection=SimpleNamespace(info=SimpleNamespace(host='hosted.example', port=54322)))
        with self.assertRaisesRegex(ValueError, 'LOCAL_DISPOSABLE'):
            capture.capture(cursor, fixture())

    def test_capture_refuses_non_readonly_session_after_identity_only(self):
        calls = []
        class Cursor:
            connection = SimpleNamespace(info=SimpleNamespace(host='127.0.0.1', port=54322))
            def execute(self, query):
                calls.append(query); return self
            def fetchone(self):
                return ('cp6_rollback', 'postgres', 'off', '', 'UTC', '170006')
        with self.assertRaisesRegex(ValueError, 'CALLER_READ_ONLY'):
            capture.capture(Cursor(), fixture())
        self.assertEqual(len(calls), 1)

    def test_supplement_does_not_accept_changed_catalogue_hash(self):
        with self.assertRaisesRegex(ValueError, 'CATALOGUE_IDENTITY_CHANGED'):
            capture.validate({'contract': capture.CONTRACT, 'catalogue_sha256': '0' * 64}, fixture())

    def test_supplement_positive_control_remains_metadata_only(self):
        c = fixture(); result = capture.validate(supplemental_fixture(c), c)
        self.assertEqual(result['status'], 'EXACT_SUPPLEMENTAL_METADATA_ONLY')
        self.assertFalse(result['writer_or_phantom_lock_closed'])
        self.assertIsNone(result['runtime_entry'])

    def test_supplement_missing_raw_function_refused(self):
        c = fixture(); supplement = supplemental_fixture(c); supplement['groups']['functions'].clear()
        with self.assertRaisesRegex(ValueError, 'SUPPLEMENT_COVERAGE:functions'):
            capture.validate(supplement, c)

    def test_supplement_unknown_empty_dependency_group_refused(self):
        c = fixture(); supplement = supplemental_fixture(c); supplement['groups']['dependencies'].clear()
        with self.assertRaisesRegex(ValueError, 'EMPTY_DEPENDENCIES'):
            capture.validate(supplement, c)

    def test_supplement_missing_function_execute_cell_refused(self):
        c = fixture(); supplement = supplemental_fixture(c); supplement['groups']['effective_function_privileges'].popitem()
        with self.assertRaisesRegex(ValueError, 'EFFECTIVE_MATRIX:effective_function'):
            capture.validate(supplement, c)

    def test_supplement_MAINTAIN_cell_required(self):
        c = fixture(); supplement = supplemental_fixture(c)
        del supplement['groups']['effective_table_privileges']['owner:erp.lots:MAINTAIN']
        with self.assertRaisesRegex(ValueError, 'EFFECTIVE_MATRIX:effective_table'):
            capture.validate(supplement, c)

    def test_supplement_inherit_option_change_refused(self):
        c = fixture(); c['memberships']['owner:reader:owner'] = [False, False, True]
        supplement = supplemental_fixture(c); supplement['groups']['memberships']['owner:reader:owner'][4] = True
        with self.assertRaisesRegex(ValueError, 'MEMBERSHIP_DRIFT'):
            capture.validate(supplement, c)

    def test_supplement_full_capture_still_cannot_open_runtime(self):
        c = fixture(); result = run(c, supplement=supplemental_fixture(c))
        self.assertIsNone(result['runtime_entry'])
        self.assertFalse(result['writer_or_phantom_lock_closed'])
        self.assertIn('SUPPLEMENT_CALLER_FULL_CATALOGUE_ROWS_SEQUENCES_AND_RESTORE_EVIDENCE_REQUIRED', result['blockers'])

    def test_supplement_credit_requires_exact_integer_zero(self):
        for value in (False, True, 0.0, '0', None, 1, -1):
            with self.subTest(value=value):
                c = fixture(); supplement = supplemental_fixture(c); supplement['actual_Native_credit'] = value
                with self.assertRaisesRegex(ValueError, 'MUST_STAY_CLOSED'):
                    capture.validate(supplement, c)

    def test_supplement_missing_credit_refused(self):
        c = fixture(); supplement = supplemental_fixture(c); del supplement['actual_Native_credit']
        with self.assertRaisesRegex(ValueError, 'MUST_STAY_CLOSED'):
            capture.validate(supplement, c)

    def test_supplement_closed_flags_require_exact_false(self):
        for field in ('production_go', 'independent_acceptance'):
            for value in (True, 0, None, 'false'):
                with self.subTest(field=field, value=value):
                    c = fixture(); supplement = supplemental_fixture(c); supplement[field] = value
                    with self.assertRaisesRegex(ValueError, 'MUST_STAY_CLOSED'):
                        capture.validate(supplement, c)
            c = fixture(); supplement = supplemental_fixture(c); del supplement[field]
            with self.assertRaisesRegex(ValueError, 'MUST_STAY_CLOSED'):
                capture.validate(supplement, c)

    def test_supplement_transaction_writes_requires_exact_false(self):
        for value in (True, 0, None, 'false'):
            with self.subTest(value=value):
                c = fixture(); supplement = supplemental_fixture(c); supplement['transaction_writes'] = value
                with self.assertRaisesRegex(ValueError, 'REQUIRED_CALLER_PROOFS_CHANGED'):
                    capture.validate(supplement, c)
        c = fixture(); supplement = supplemental_fixture(c); del supplement['transaction_writes']
        with self.assertRaisesRegex(ValueError, 'REQUIRED_CALLER_PROOFS_CHANGED'):
            capture.validate(supplement, c)

    def test_supplement_caller_flags_require_exact_true(self):
        for field in ('caller_full_catalogue_data_sequence_bracket_required', 'caller_outer_restoration_required'):
            for value in (False, 1, None, 'true'):
                with self.subTest(field=field, value=value):
                    c = fixture(); supplement = supplemental_fixture(c); supplement[field] = value
                    with self.assertRaisesRegex(ValueError, 'REQUIRED_CALLER_PROOFS_CHANGED'):
                        capture.validate(supplement, c)
            c = fixture(); supplement = supplemental_fixture(c); del supplement[field]
            with self.assertRaisesRegex(ValueError, 'REQUIRED_CALLER_PROOFS_CHANGED'):
                capture.validate(supplement, c)

    def test_supplement_runtime_entry_must_be_present_and_null(self):
        c = fixture(); supplement = supplemental_fixture(c); del supplement['runtime_entry']
        with self.assertRaisesRegex(ValueError, 'MUST_STAY_CLOSED'):
            capture.validate(supplement, c)
        supplement['runtime_entry'] = 'erp.writer()'
        with self.assertRaisesRegex(ValueError, 'MUST_STAY_CLOSED'):
            capture.validate(supplement, c)

    def test_capture_queries_have_no_write_statement(self):
        for name, query in capture.QUERIES.items():
            stream = census.tokens(query)
            self.assertIn(stream[0][1], ('select', 'with'), name)
            # Token-level assertion on a fixed internal query set, not a general
            # SQL security parser; actual capture has an enforced RO session.
            self.assertFalse({'insert', 'delete', 'update', 'truncate', 'call', 'do', 'lock', 'grant'} &
                             {t[1] for t in stream if t[0] == 'word'}, name)


if __name__ == '__main__':
    unittest.main()
