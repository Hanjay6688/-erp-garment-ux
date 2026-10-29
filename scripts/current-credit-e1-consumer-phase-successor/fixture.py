"""Local typed SQL double inputs. No DB, network or product runtime import.

The ERP column declarations come from the same retained actual ERP dump as the
frozen D1 local materialize counter. Defaults/constraints are stripped in the
declared stand-ins; they are not catalog, RLS, Native or financial qualification.
Actual full E profile/history/prepare and consumer command functions are kept.
"""
from pathlib import Path
import ast, hashlib, importlib.util, json, re, sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DUMP_SHA = '2b5eed32d5d2da81c99b57fbd5c27621affe686de427095176f746ccadcb39c7'
CREDIT = ROOT/'scripts/cp7_customer_credit'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def function(text, name):
    starts = list(re.finditer(r'create(?:\s+or\s+replace)?\s+function\s+' + re.escape(name) + r'\s*\(', text, re.I))
    if len(starts) != 1:
        raise ValueError('LOCAL_EXACT_FUNCTION_REQUIRED:' + name + ':' + str(len(starts)))
    start = starts[0].start()
    body = re.search(r'\bas\s+(\$[a-zA-Z_0-9]*\$)', text[start:], re.I)
    if body is None:
        raise ValueError('LOCAL_FUNCTION_BODY_REQUIRED:' + name)
    opening = start + body.end()
    end = text.index(body[1], opening) + len(body[1])
    return text[start:end] + ';'


def once(text, old, new, label):
    if text.count(old) != 1:
        raise ValueError('LOCAL_EXACT_SOURCE_ANCHOR:' + label + ':' + str(text.count(old)))
    return text.replace(old, new, 1)


def build(dump):
    raw = Path(dump).read_bytes()
    if sha(raw) != DUMP_SHA:
        raise ValueError('LOCAL_RETAINED_ERP_DUMP_CHANGED')
    helper_path = ROOT/'scripts/cp7_credit_correction_de/local_compile_fixture.py'
    spec = importlib.util.spec_from_file_location('e_phase_retained_column_parser', helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    tables = helper.tables(raw.decode())
    source_files = [CREDIT/p for p in (
        'ledger/01_immutable_facts.proposal.sql', 'readers/02_materialized_profile.proposal.sql',
        'coordinator/01_coordinator_facts.sql', 'consumer/02_operation_facts.sql',
        'refund/01_initial_refund.proposal.sql')]
    for path in source_files:
        tables.update(helper.tables(path.read_text()))
    be = ROOT/'supabase/release/cp6-t3/20260926050000_erp_v2_6_20be_cp6_conversion_redye_pocket.sql'
    tables.update(helper.tables(be.read_text()))
    # The retained parser is intentionally closed to four schemas. Apply that
    # same parser to exact note DDL using a reversible namespace-only alias.
    note = (ROOT/'scripts/cp7-src/sales/correction.sql').read_text()
    aliased = note.replace('cp7_note.', 'cp7_sales_return_correction.')
    for name, ddl in helper.tables(aliased).items():
        if name.startswith('cp7_sales_return_correction.'):
            real = name.replace('cp7_sales_return_correction.', 'cp7_note.')
            tables[real] = ddl.replace('cp7_sales_return_correction.', 'cp7_note.')
    tables.update(helper.tables((ROOT/'scripts/cp7-src/sales/commands.sql').read_text()))
    required = (
        'erp.sales_headers', 'erp.sales_items', 'erp.sales_payments', 'erp.sales_returns',
        'erp.sales_return_items', 'erp.sale_stock_allocations', 'erp.customers',
        'erp.journal_entries', 'erp.journal_lines', 'erp.chart_accounts', 'erp.cash_accounts',
        'erp.accounting_period_control', 'erp.accounting_account_mappings',
        'erp.fg_stock_movements', 'erp.fg_inventory_balances', 'erp.fg_lots', 'erp.hpp_versions',
        'erp.opening_lot_hpp_gl_state', 'erp.opening_hpp_corrections', 'erp.po_hpp_gl_state',
        'erp.be_conversion_sources_v1',
        'cp7_credit.return_families', 'cp7_credit.return_family_members', 'cp7_credit.cohorts',
        'cp7_credit.recognition_plans', 'cp7_credit.recognition_components',
        'cp7_credit.component_parts', 'cp7_credit.component_journals',
        'cp7_credit.consumption_events', 'cp7_credit.initial_refund_operations',
        'cp7_credit.initial_return_materializations', 'cp7_credit.financial_materializations',
        'cp7_credit.financial_materialization_objects', 'cp7_credit.consumer_requests_v1',
        'cp7_credit.consumer_execution_context', 'cp7_credit.consumer_operations_v1',
        'cp7_credit.consumer_completions_v1', 'cp7_credit.consumer_posting_scope_v1',
        'cp7_note.requests', 'cp7_note.context', 'cp7_note.revisions', 'cp7_note.journal_restatements',
        'cp7_sales.command_context')
    missing = set(required) - set(tables)
    if missing:
        raise ValueError('LOCAL_TYPED_TABLES_MISSING:' + repr(missing))
    ddl = ''.join('create role ' + role + ';' for role in
                  ('anon', 'authenticated', 'service_role', 'cp7_capture', 'cp7_sales_read', 'cp7_sales_write', 'cp7_credit_write'))
    ddl += ''.join('create schema ' + schema + ';' for schema in
                   ('auth', 'erp', 'cp7_credit', 'cp7_note', 'cp7_sales', 'ow04_source_proposal',
                    'ow04_ordinal_wrapper', 'ow04_pure_kernel', 'cp7_guard', 'local_e_phase'))
    ddl += 'create domain cp7_credit.cent_amount as numeric;'
    ddl += ''.join(tables[name] for name in required)
    # Native row-version/touch callbacks, with the other Native ERP triggers
    # explicitly absent in this local model.
    native_callbacks = {name: function(raw.decode(), 'erp.' + name) for name in ('bump_row_version', 'touch_updated_at')}
    ddl += ''.join(native_callbacks.values())
    ddl += ('create trigger trg_sales_row_version before update on erp.sales_headers for each row execute function erp.bump_row_version();'
            'create trigger trg_sales_touch before update on erp.sales_headers for each row execute function erp.touch_updated_at();')
    reader = (CREDIT/'readers/01_current_reader_capability.proposal.sql').read_text()
    facts = (CREDIT/'readers/02_materialized_profile.proposal.sql').read_text()
    own = (CREDIT/'consumer/08_owning_command.sql').read_text()
    data = (CREDIT/'consumer/05_event_data.sql').read_text()
    actual = {name: function(text, name) for text, names in (
        ((CREDIT/'ledger/01_immutable_facts.proposal.sql').read_text(), ('cp7_credit.pg_jsonb_sha256',)),
        ((CREDIT/'ledger/02_uuid_poster.proposal.sql').read_text(), ('cp7_credit.native_cent_lines', 'cp7_credit.native_lines_sha256')),
        ((CREDIT/'source/source.sql').read_text(), ('ow04_source_proposal.canonical_json_v1', 'ow04_source_proposal.sha',
                                                 'ow04_source_proposal.cents', 'ow04_source_proposal.financial_journal_payload')),
        ((CREDIT/'refund/01_initial_refund.proposal.sql').read_text(), ('cp7_credit.refund_physical_text',)),
        (reader, ('cp7_credit.current_leaf_assignment',)),
        (facts, ('cp7_credit.materialized_fact', 'cp7_credit.materialized_journal_payload')),
        (own, ('cp7_credit.consumer_quote_binding_v1', 'cp7_credit.assert_consumer_operation_input_v1',
               'cp7_credit.assert_consumer_operation_bound_v1',
               'cp7_credit.consumer_verify_posted_journal_v1', 'cp7_credit.consumer_actual_manifest_v1',
               'cp7_credit.consumer_document_ar_v1', 'cp7_credit.consumer_invoice_profile_v1',
               'cp7_credit.consumer_execute_v1')),
        (data, ('cp7_credit.consumer_invoice_ar_source_v1', 'cp7_credit.consumer_operation_lines_v1',
                'cp7_credit.consumer_event_data_v1', 'cp7_credit.consumer_incoming_funding_v1')),
        ((CREDIT/'consumer/06_access_and_requests.sql').read_text(), ('cp7_credit.validate_consumer_payload_v1',
            'cp7_credit.consumer_payload_kind_v1', 'cp7_credit.consumer_internal_allowed_v1')),
        ((CREDIT/'consumer/09_deferred_closure.sql').read_text(), ('cp7_credit.consumer_outcome_v1', 'cp7_credit.assert_consumer_closed_v1')),
        ((CREDIT/'consumer/01_dependency_graph.sql').read_text(), ('cp7_credit.consumer_dependency_graph_v1',)),
        ((CREDIT/'consumer/07_locked_projection.sql').read_text(), ('cp7_credit.consumer_joined_graph_v1',
            'cp7_credit.consumer_capture_sources_v1', 'cp7_credit.consumer_native_invariant_v1')))
        for name in names}
    # Existing E derivations, unchanged product source. These are source-level
    # local applications, not pg_get_functiondef/actual catalog qualification.
    actual['cp7_credit.consumer_execute_v1'] = once(actual['cp7_credit.consumer_execute_v1'],
        "jsonb_array_elements_text(o.source_graph->'sale_ids')",
        'jsonb_array_elements_text(cp7_credit_note_carry_de.active_sales_v1(o.source_graph))', 'existing E captured active terminal loop')
    actual['cp7_credit.consumer_event_data_v1'] = once(actual['cp7_credit.consumer_event_data_v1'],
        '(e.cohort_id,e.event_kind,e.amount,e.target_sale_id,e.cash_account_id)\n    is distinct from(old.cohort_id,old.event_kind,-old.amount,old.target_sale_id,old.cash_account_id)',
        '(e.cohort_id,e.event_kind,e.amount,e.cash_account_id)\n    is distinct from(old.cohort_id,old.event_kind,-old.amount,old.cash_account_id)\n   or not cp7_credit_note_carry_de.same_target_v1(old.target_sale_id,e.target_sale_id)', 'existing E exact named target lineage')
    actual['cp7_credit.consumer_invoice_profile_v1'] = once(actual['cp7_credit.consumer_invoice_profile_v1'], 'begin\n',
        'begin\n if cp7_credit_note_carry_de.is_current_v1(p_sale)then return cp7_credit_note_carry_de.invoice_profile_v1(p_sale);end if;\n', 'existing E invoice dispatch')
    actual['cp7_credit.consumer_incoming_funding_v1'] = once(actual['cp7_credit.consumer_incoming_funding_v1'],
        "event_kind='APPLY'and target_sale_id=p_sale", "event_kind='APPLY'and cp7_credit_note_carry_de.effective_target_v1(id)=p_sale", 'existing E immutable incoming assignment')
    body = actual['cp7_credit.consumer_capture_sources_v1']
    for old, new in (
        ("jsonb_array_elements_text(p_graph->'sale_ids')", 'jsonb_array_elements_text(cp7_credit_note_carry_de.active_sales_v1(p_graph))'),
        ('cp7_credit.assert_current_materialized_profile(sale,sale,sale)', 'cp7_credit.assert_current_materialized_profile(sale,cp7_credit_note_carry_de.root_v1(sale),sale)'),
        ('cp7_credit.inspect_current_materialized_profile(sale,sale,sale)', 'cp7_credit.inspect_current_materialized_profile(sale,cp7_credit_note_carry_de.root_v1(sale),sale)')):
        body = once(body, old, new, 'existing E current capture')
    actual['cp7_credit.consumer_capture_sources_v1'] = body
    body = actual['cp7_credit.consumer_native_invariant_v1']
    if body.count('ce.target_sale_id=p_sale') != 2:
        raise ValueError('LOCAL_EXISTING_E_NATIVE_INVARIANT_TWO_ANCHORS_REQUIRED')
    actual['cp7_credit.consumer_native_invariant_v1'] = body.replace('ce.target_sale_id=p_sale', 'cp7_credit_note_carry_de.effective_target_v1(ce.id)=p_sale', 2)
    body = actual['cp7_credit.assert_consumer_closed_v1']
    for old, new in (
        ("is distinct from o.source_graph->'sale_ids'then", 'is distinct from cp7_credit_note_carry_de.active_sales_v1(o.source_graph)then'),
        ("jsonb_array_elements_text(o.source_graph->'sale_ids')", 'jsonb_array_elements_text(cp7_credit_note_carry_de.active_sales_v1(o.source_graph))'),
        ('perform cp7_credit.consumer_invoice_profile_v1(sale::uuid);', 'perform cp7_credit_note_carry_de.validate_current_v1(sale::uuid);')):
        body = once(body, old, new, 'retained E exact closure derivation')
    actual['cp7_credit.assert_consumer_closed_v1'] = body
    paid = function((CREDIT/'coordinator/05_factual_profile.sql').read_text(), 'cp7_credit.current_effective_paid')
    paid = once(paid, 'if paid+adjustment<0 then',
                'if paid+adjustment<0 and not cp7_credit.payment_is_intermediate_v1(p_sale)then', 'existing payment phase predicate')
    core = function(reader, 'erp._cp7_current_credit_adjustment')
    core = once(core, "where e.journal_id=j.id and e.id=j.source_id and e.event_kind='REFUND'))then",
        """where e.journal_id=j.id and e.id=j.source_id and e.event_kind='REFUND'))
  or exists(select 1 from erp.journal_entries j where j.source_type in('CP7_CUSTOMER_CREDIT_APPLY','CP7_CUSTOMER_CREDIT_EVENT_REVERSE')
   and not exists(select 1 from cp7_credit.consumption_events ce join cp7_credit.cohorts c on c.id=ce.cohort_id
    join cp7_credit.return_families f on f.id=c.family_id where ce.journal_id=j.id and ce.id=j.source_id
     and((j.source_type='CP7_CUSTOMER_CREDIT_APPLY'and ce.event_kind='APPLY'and ce.amount>0 and ce.restores_event_id is null)
      or(j.source_type='CP7_CUSTOMER_CREDIT_EVENT_REVERSE'and ce.amount<0 and ce.restores_event_id is not null))))then""", 'retained consumer orphan predicate')
    anchor = ' perform cp7_credit.assert_current_materialized_profile(p_sale,m.root_sale_id,m.current_leaf_id);'
    core = once(core, anchor, ' if cp7_credit.payment_is_intermediate_v1(p_sale)then return cp7_credit.payment_intermediate_adjustment_v1(p_sale);end if;\n' + anchor, 'retained payment own phase')
    old = "e.event_kind='APPLY'and e.target_sale_id=p_sale"
    if core.count(old) != 2:
        raise ValueError('LOCAL_EXISTING_E_CORE_TWO_ANCHORS_REQUIRED')
    core = core.replace(old, "e.event_kind='APPLY'and cp7_credit_note_carry_de.effective_target_v1(e.id)=p_sale", 2)
    core = once(core, ' if not exists(select 1 from cp7_credit.return_families f where f.family_root_sale_id=m.root_sale_id)',
                ' if not cp7_credit_note_carry_de.is_current_v1(p_sale)and not exists(select 1 from cp7_credit.return_families f where f.family_root_sale_id=m.root_sale_id)', 'retained E no silent zero path')
    actual['erp._cp7_current_credit_adjustment'] = core
    actual['cp7_credit.current_effective_paid'] = paid
    paths = source_files + [helper_path, Path(dump), be, ROOT/'scripts/cp7-src/sales/correction.sql',
        ROOT/'scripts/cp7-src/sales/commands.sql', CREDIT/'readers/01_current_reader_capability.proposal.sql',
        CREDIT/'consumer/08_owning_command.sql', CREDIT/'consumer/05_event_data.sql',
        CREDIT/'consumer/06_access_and_requests.sql', CREDIT/'consumer/01_dependency_graph.sql',
        CREDIT/'consumer/09_deferred_closure.sql',
        CREDIT/'consumer/07_locked_projection.sql', CREDIT/'coordinator/05_factual_profile.sql',
        CREDIT/'consumer/composition.py', CREDIT/'payment_correction/transform.py',
        ROOT/'scripts/cp7_credit_correction_de/e_native_delta.py', CREDIT/'ledger/02_uuid_poster.proposal.sql',
        CREDIT/'source/source.sql', CREDIT/'kernel/kernel.sql', CREDIT/'ordinal-wrapper/wrapper.sql']
    return dict(classification='LOCAL_TYPED_SQL_DOUBLES_ONLY_NOT_NATIVE', Native_executions=0,
        ddl=ddl, actual_functions=actual, native_callbacks=native_callbacks, typed_tables=list(required),
        stripped='ERP/credit/note stand-in defaults/constraints only; actual E own DDL loaded separately',
        sources={str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p):
                 dict(bytes=p.stat().st_size, sha256=sha(p.read_bytes())) for p in paths})


if __name__ == '__main__':
    print(json.dumps(build(Path(sys.argv[1]))))
