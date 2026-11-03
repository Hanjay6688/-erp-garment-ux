"""Own four actual race copies without changing their retained authority rules."""
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from types import ModuleType,SimpleNamespace
import importlib.util,json,subprocess
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


def save(value):
    path=ROOT/'cp6-proof/t3/MANDOR_SESSION4_ORIGINAL.json'
    raw=(json.dumps(value,sort_keys=True,default=str)+'\n').encode()
    require(not path.exists(),'MANDOR_FIRST_SESSION_ORIGINAL_OVERWRITE_REFUSED')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb')as stream:stream.write(raw)
    return dict(name=path.name,bytes=len(raw),sha256=sha256(raw).hexdigest())


def run(product,state,fixture,verify,report):
    admission.parent(product.parent_raw)
    from assembly import FROZEN
    modes=load('mandor_exact_original_real_copy_modes',FROZEN/'scripts/current-s03-sku-s05-composite-qualification/modes.py')
    gate=load('mandor_qualified_typed_copy_gate',FROZEN/'scripts/cp7_accessory_nonpayable/qualification_gate.py')
    adapter=SimpleNamespace(races=lambda tools,today:access_cases.races(tools,today,
        product=product,state=state,fixture=fixture))
    with copy_scope(modes,product,state)as copies:
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
        actual_Mandor_Auth_browser_acceptance_pending=True)
