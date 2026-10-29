"""Emit local structural DDL only. No connection or product runtime import.

Retained helper supplies exact column types; original defaults/constraints are
stripped for ERP/credit stand-ins. Actual D1 facts.sql is loaded separately.
"""
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
import ast,importlib.util,json,sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
TABLES=(
 'erp.sales_returns','erp.sales_return_items','erp.journal_entries','erp.journal_lines',
 'cp7_credit.return_families','cp7_credit.return_family_members','cp7_credit.cohorts',
 'cp7_credit.recognition_plans','cp7_credit.recognition_components','cp7_credit.component_parts',
 'cp7_credit.component_journals','cp7_credit.plan_support_events',
 'cp7_credit.financial_materializations','cp7_credit.financial_materialization_objects',
 'cp7_sales_return_correction.links','cp7_sales_return_correction.requests','cp7_sales.command_context')


def build(dump):
    path=ROOT/'scripts/cp7_credit_correction_de/local_compile_fixture.py'
    spec=importlib.util.spec_from_file_location('d1_materialize_retained_structural_helper',path)
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    source=helper.build(dump);tables=helper.tables(source)
    missing=set(TABLES)-set(tables)
    if missing:raise ValueError('LOCAL_STRUCTURAL_TYPE_MISSING:'+repr(missing))
    ddl='create role anon;create role authenticated;create role service_role;'
    for schema in ('auth','erp','cp7_credit','cp7_sales','cp7_sales_return_correction',
                   'cp7_credit_correction_de','ow04_source_proposal','ow04_ordinal_wrapper','local_materialize_fixture'):
        ddl+='create schema '+schema+';'
    ddl+=''.join(tables[name]for name in TABLES)
    # Retained helper parses CREATE TABLE only; this later installed source
    # declares the two exact columns used by materialize_v1. Defaults/checks
    # remain absent in these explicitly structural credit stand-ins.
    no_journal=ROOT/'scripts/cp7_customer_credit/source/NO_JOURNAL_SCHEMA_DIFF.proposal.sql'
    no_journal_text=no_journal.read_text()
    for anchor in ("add column financial_state text not null default 'JOURNAL'",'add column financial_source_proof jsonb'):
        if no_journal_text.count(anchor)!=1:raise ValueError('LOCAL_RETAINED_COLUMN_DECLARATION_CHANGED')
    ddl+='alter table cp7_credit.return_family_members add column financial_state text,add column financial_source_proof jsonb;'

    ddl+="create function auth.uid()returns uuid language sql stable as $$select null::uuid$$;"
    # Reuse all22 actual source comparator queries without importing runtime.
    capture=ROOT/'scripts/cp7_ow04_restore_bundle.py'
    tree=ast.parse(capture.read_text());values={}
    names={'NAMESPACE','QUERIES'}
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='_acl'
           or isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id in names for t in n.targets)]
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(capture),'exec'),values)
    case_tree=ast.parse((ROOT/'scripts/cp7_credit_correction_de/cases.py').read_text())
    hook=[n.value for n in ast.walk(case_tree)if isinstance(n,ast.Constant)and isinstance(n.value,str)
          and 'create function cp7_credit_correction_de.test_part_failure()'in n.value]
    if len(hook)!=1:raise ValueError('EXACT_RETAINED_FAILURE_HOOK_REQUIRED')
    return dict(classification='LOCAL_TYPED_STRUCTURAL_STANDINS_NOT_NATIVE',ddl=ddl,
        catalog_queries=values['QUERIES'],failure_hook=hook[0],
        type_tables=list(TABLES),constraints_defaults='STRIPPED_IN_ERP_AND_CREDIT_STANDINS_ONLY',
        actual_D1_facts_DDL=True,Native_execution=False,
        sources={str(p.relative_to(ROOT))if p.is_relative_to(ROOT)else str(p):sha256(p.read_bytes()).hexdigest()
                 for p in (Path(dump),path,capture,ROOT/'scripts/cp7_credit_correction_de/cases.py',no_journal)})


if __name__=='__main__':print(json.dumps(build(Path(sys.argv[1]))))
