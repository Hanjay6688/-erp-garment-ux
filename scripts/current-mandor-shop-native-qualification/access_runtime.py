"""Own four actual race copies without changing their retained authority rules."""
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from types import ModuleType,SimpleNamespace
import importlib.util,json,os,subprocess
import admission,access_cases

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ORIGINAL='scripts/ow04-payment-current-qualification/copy_authority.py'
ORIGIN='0da4d79a4f7201ef053d6de1eb155d990b4bfa4d'
PIN=(3895,'cfdc3b899e335dd13a9456242ed5158b718ac5c56d9b1ebf06c4571eda2cc7a2')
BEFORE="assert name in('cp6_auditor_browser','cp6_auditor_http')"
AFTER="assert name in('cp6_auditor_browser','cp6_auditor_http','cp6_auditor_race')"


def require(value,message):
    if not value:raise ValueError(message)


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module);return module


def derive(raw):
    require((len(raw),sha256(raw).hexdigest())==PIN,'MANDOR_COPY_EXACT_ORIGINAL_BYTES')
    require(raw==subprocess.check_output(['git','-C',str(ROOT),'show',ORIGIN+':'+ORIGINAL]),
        'MANDOR_COPY_EXACT_ORIGINAL_PUBLIC_BLOB')
    text=raw.decode();require(text.count(BEFORE)==1 and AFTER not in text,'MANDOR_COPY_ONE_FIXED_NAME_EXTENSION')
    result=text.replace(BEFORE,AFTER,1)
    require(result.replace(AFTER,BEFORE,1).encode()==raw,'MANDOR_COPY_COMPLETE_ORIGINAL_RECOVERED')
    compile(result,'mandor_exact_original_copy_authority','exec')
    return result,dict(original_bytes=PIN[0],original_sha256=PIN[1],derived_sha256=sha256(result.encode()).hexdigest(),
        exact_copy_name_extension_count=1,original_bytes_recovered=True,all_raw22_authority_checks_unchanged=True,
        product_or_schema_or_RPC_grants_added=False,actual_case_credit=0)


@contextmanager
def copy_scope(modes,product,state):
    admission.parent(product.parent_raw)
    from assembly import FROZEN
    text,proof=derive((FROZEN/ORIGINAL).read_bytes())
    adapter=ModuleType('mandor_exact_copy_authority');adapter.__file__=str(FROZEN/ORIGINAL)
    exec(compile(text,adapter.__file__,'exec'),adapter.__dict__)
    previous=modes.copy_db;adapter.ORIGINAL_COPY_DATABASE=previous
    adapter.STATE=dict(installed_catalog=state['after'])
    def verify(cur,actual):
        require(actual is adapter.STATE,'MANDOR_COPY_EXACT_ADAPTER_STATE')
        return product.verify(cur,state)
    adapter.PRODUCT=SimpleNamespace(catalog=product.runtime()[-1],verify=verify)
    modes.copy_db=adapter.copy_database
    try:yield dict(source=proof,actual_copy_admissions=adapter.COPY_ADMISSIONS)
    finally:modes.copy_db=previous


def save(value,name='MANDOR_SESSION4_ORIGINAL.json'):
    require(name in('MANDOR_SESSION4_ORIGINAL.json','MANDOR_HTTP2_ORIGINAL.json','MANDOR_BROWSER_FIXTURE.json',
        'MANDOR_BROWSER_STATE.json','MANDOR_BROWSER2_ORIGINAL.json'),'MANDOR_FIXED_ACCESS_ORIGINAL_NAME')
    output=load('mandor_current_complete_access_output',ROOT/'scripts/current-mandor-afui-preparation/output_binding.py')
    return output.save_access(value,name)


def run(product,state,fixture,verify,report):
    admission.parent(product.parent_raw)
    from assembly import FROZEN
    modes=load('mandor_exact_original_real_copy_modes',FROZEN/'scripts/current-s03-sku-s05-composite-qualification/modes.py')
    gate=load('mandor_qualified_typed_copy_gate',FROZEN/'scripts/cp7_accessory_nonpayable/qualification_gate.py')
    adapter=SimpleNamespace(races=lambda tools,today:access_cases.races(tools,today,
        product=product,state=state,fixture=fixture))
    output=load('mandor_current_complete_access_output',ROOT/'scripts/current-mandor-afui-preparation/output_binding.py')
    with output.case_scope(modes,'copies',retention=access_cases),copy_scope(modes,product,state)as copies:
        report['access_copy_authority']=copies
        actual=modes.run_races(adapter,verify,'mandor_current_session4')
        report['session4_original']=save(actual)
        report['session4_gate']=gate.copies(actual,access_cases.RACE_IDS,mode='RACE')
    require(len(copies['actual_copy_admissions'])==4 and all(
        row.get('all22_groups_equal_original_install')is True
        and row.get('product_state_modified')is False
        and row.get('Native_or_schema_or_RPC_permissions_changed')is False
        for row in copies['actual_copy_admissions']),'MANDOR_FOUR_FRESH_AUTHORITY_PRESERVED_COPIES')
    report.update(actual_two_session_races=4,actual_business_cases=13,
        actual_Mandor_browser_acceptance_pending=True)


def run_http(product,state,fixture,verify,report):
    admission.parent(product.parent_raw)
    from assembly import FROZEN
    import http_cases
    modes=load('mandor_exact_original_real_HTTP_modes',FROZEN/'scripts/current-s03-sku-s05-composite-qualification/modes.py')
    typed=load('mandor_qualified_HTTP_copy_gate',FROZEN/'scripts/cp7_accessory_nonpayable/qualification_gate.py')
    adapter=SimpleNamespace(http_cases=lambda http,today:http_cases.http_cases(http,today,
        product=product,state=state,fixture=fixture))
    output=load('mandor_current_complete_access_output',ROOT/'scripts/current-mandor-afui-preparation/output_binding.py')
    with output.case_scope(modes,'copies',retention=access_cases),copy_scope(modes,product,state)as copies:
        report['http_copy_authority']=copies
        actual=modes.run_http(adapter,verify,'mandor_current_HTTP2')
        report['HTTP2_original']=save(actual,'MANDOR_HTTP2_ORIGINAL.json')
        report['HTTP2_gate']=typed.copies(actual,http_cases.HTTP_IDS,mode='HTTP')
    require(len(copies['actual_copy_admissions'])==1 and all(
        row.get('all22_groups_equal_original_install')is True
        and row.get('product_state_modified')is False
        and row.get('Native_or_schema_or_RPC_permissions_changed')is False
        for row in copies['actual_copy_admissions']),'MANDOR_ONE_REAL_AUTH_COPY_WITH_ORIGINAL_AUTHORITY')
    report.update(actual_Auth_HTTP_cases=2,actual_business_cases=15,
        actual_Mandor_browser_acceptance_pending=True)


@contextmanager
def browser_environment(report):
    changes=dict(MANDOR_BROWSER_CONFIRM='cp6_auditor_browser',
        MANDOR_BROWSER_FIXTURE_SHA256=report['browser_fixture_original']['sha256'],
        MANDOR_BROWSER_STATE_SHA256=report['browser_state_original']['sha256'],
        AUDITOR_BROWSER_CASE_TIMEOUT_MS='600000')
    old={name:os.environ.get(name)for name in changes};os.environ.update(changes)
    try:yield
    finally:
        for name,value in old.items():
            if value is None:os.environ.pop(name,None)
            else:os.environ[name]=value


def run_browser(product,state,fixture,verify,report):
    admission.parent(product.parent_raw)
    from assembly import FROZEN
    import browser_preflight
    modes=load('mandor_exact_original_browser_copy_modes',FROZEN/'scripts/current-s03-sku-s05-composite-qualification/modes.py')
    typed=load('mandor_qualified_browser_copy_gate',FROZEN/'scripts/cp7_accessory_nonpayable/qualification_gate.py')
    # The original host must build THIS candidate's exact normal App. Its
    # source stays byte-exact; only the pre-existing candidate-root slot moves.
    require(modes.AUDITOR==FROZEN,'MANDOR_BROWSER_EXACT_ORIGINAL_HOST_ROOT')
    modes.AUDITOR=ROOT
    host='scripts/current-s03-sku-s05-composite-qualification/host.mjs'
    require((ROOT/host).read_bytes()==(FROZEN/host).read_bytes(),'MANDOR_BROWSER_ORIGINAL_HOST_UNCHANGED')
    report['browser_fixture_original']=save(fixture,'MANDOR_BROWSER_FIXTURE.json')
    report['browser_state_original']=save(state,'MANDOR_BROWSER_STATE.json')
    output=load('mandor_current_complete_access_output',ROOT/'scripts/current-mandor-afui-preparation/output_binding.py')
    with output.case_scope(modes,'copies',retention=access_cases),copy_scope(modes,product,state)as copies:
        report['browser_copy_authority']=copies
        with browser_environment(report):actual=modes.run_browser(HERE/'browser.mjs',verify,'mandor_current_browser2')
        report['browser2_original']=save(actual,'MANDOR_BROWSER2_ORIGINAL.json')
        report['browser2_gate']=typed.copies(actual,browser_preflight.IDS,mode='BROWSER')
    require(len(copies['actual_copy_admissions'])==1 and all(
        row.get('all22_groups_equal_original_install')is True
        and row.get('product_state_modified')is False
        and row.get('Native_or_schema_or_RPC_permissions_changed')is False
        for row in copies['actual_copy_admissions']),'MANDOR_ONE_ACTUAL_BROWSER_COPY_WITH_PRODUCT_AUTHORITY')
    report.update(actual_browser_cases=2,actual_business_cases=17,
        actual_Mandor_browser_acceptance_pending=False,real_Auth_browser_claim=True)
