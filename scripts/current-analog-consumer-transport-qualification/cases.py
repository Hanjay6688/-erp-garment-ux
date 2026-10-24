"""Retain exact B transport bodies; adapt two setup hooks for full current ERP."""
from pathlib import Path
from hashlib import sha256
import ast
import importlib.util
import inspect
import cp7_current_analog_consumer_installation as product

SOURCE=Path(__file__).resolve().parents[1]/'cp7_ow11_consumer_transport_cases.py'
spec=importlib.util.spec_from_file_location('qualified_B_consumer_transport',SOURCE)
retained=importlib.util.module_from_spec(spec);spec.loader.exec_module(retained)
IDS=retained.IDS
STATE=None
COPY_SETUP_ADMISSIONS=[]
original_prepare=retained.prepare_fixture


def source_binding():
    raw=SOURCE.read_bytes();text=raw.decode();tree=ast.parse(text)
    declarations={node.name:ast.get_source_segment(text,node).strip()for node in tree.body if isinstance(node,ast.FunctionDef)}
    functions={}
    for name,fn in [('races',retained.races),('http_cases',retained.http_cases),('prepare_fixture',original_prepare)]:
        actual=inspect.getsource(fn).strip()
        assert actual==declarations[name],('RETAINED_TRANSPORT_BODY_CHANGED',name)
        functions[name]=sha256(actual.encode()).hexdigest()
    assert retained.install is install and retained.prepare_fixture is prepare_fixture
    return dict(path='scripts/'+SOURCE.name,sha256=sha256(raw).hexdigest(),functions=functions,
        replaced_setup_hooks=['install','prepare_fixture'],source_oracle_assertions_unchanged=True)


def install(cur):
    assert STATE is not None,'FULL_CURRENT_CONSUMER_INSTALLATION_REQUIRED'
    retained.plan.b.api.admin(cur)
    database=cur.execute('select current_database()').fetchone()[0]
    assert database in('cp6_auditor_race','cp6_auditor_http')
    actual=product.catalog._catalog_rows(cur);expected=STATE['after']
    assert set(actual)==set(expected)and len(actual)==22
    changes={group:sorted(key for key in set(actual[group])|set(expected[group])
        if actual[group].get(key)!=expected[group].get(key))for group in expected if actual[group]!=expected[group]}
    record=dict(database=database,actual_full22_changes=changes,product_state_modified=False,
        product_catalog_projection=False,existing_B_cases_unchanged=True)
    COPY_SETUP_ADMISSIONS.append(record)
    if changes:
        assert database=='cp6_auditor_race'and changes=={'schemas':['erp']},changes
        before,after=expected['schemas']['erp'],actual['schemas']['erp']
        assert before[0]==after[0]
        added=[x for x in after[1]if x not in before[1]]
        removed=[x for x in before[1]if x not in after[1]]
        assert added==[['authenticated',before[0],'USAGE',False]]and not removed,(added,removed)
        record['exact_retained_harness_schema_grant']=added
    assert product.sources()==STATE['sources']
    # Observe the real catalog. Never project it into an older verifier.
    proof=product.provenance.verify(cur,STATE['stages'][-1]['state'])
    record['actual_latest_stage_verification']=proof
    return STATE['before'],None,STATE['stages'][-1]['state']


def prepare_fixture(cur,today,actor):
    retained.plan.b.api.admin(cur)
    acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
    had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
    if not had:cur.execute('grant usage on schema erp to authenticated')
    # The unchanged B fixture needs a setup-only Native schema grant. A failure
    # propagates and the caller rolls back its transaction; no HTTP call runs.
    result=original_prepare(cur,today,actor)
    retained.plan.b.api.admin(cur)
    if not had:cur.execute('revoke usage on schema erp from authenticated')
    assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
    return result


retained.install=install
retained.prepare_fixture=prepare_fixture


def races(tools,today):
    return retained.races(tools,today)


def http_cases(http,today):
    return retained.http_cases(http,today)
