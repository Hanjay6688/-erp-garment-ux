"""Actual current D1/E Native30 receipt is required before ERP imports."""
from pathlib import Path
from hashlib import sha256
from contextlib import contextmanager
import importlib,importlib.util,json,math

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PARENT_HEAD=None
PARENT_RECEIPT=None


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def strict(raw):
    def pairs(items):
        value={}
        for key,item in items:
            if key in value:raise ValueError('FREE_DATE_DE_DUPLICATE_RECEIPT_KEY')
            value[key]=item
        return value
    def finite(item):
        if type(item)is float and not math.isfinite(item):raise ValueError('FREE_DATE_DE_NONFINITE_RECEIPT')
        if type(item)is dict:
            for value in item.values():finite(value)
        elif type(item)is list:
            for value in item:finite(value)
    value=json.loads(raw,object_pairs_hook=pairs,
        parse_constant=lambda x:(_ for _ in()).throw(ValueError('FREE_DATE_DE_NONFINITE_RECEIPT')))
    finite(value);return value


def parent_receipt():
    if PARENT_HEAD is None or PARENT_RECEIPT is None:
        raise ValueError('FREE_DATE_DE_ACTUAL_NATIVE30_PARENT_INTAKE_PENDING')
    raw=(HERE/'DE30_PARENT_ROOT_ACTUAL_INTAKE.json').read_bytes()
    if len(raw)!=PARENT_RECEIPT['bytes']or sha256(raw).hexdigest()!=PARENT_RECEIPT['sha256']:
        raise ValueError('FREE_DATE_DE_EXACT_PARENT_RECEIPT_BYTES_CHANGED')
    value=strict(raw)
    expected=dict(status='ROOT_VERIFIED_CURRENT_COMPLETE_D1_E_NATIVE30_ALL5',head=PARENT_HEAD,
        actual_Native_cases=30,actual_D1_cases=13,actual_E_cases=17,actual_browser_cases=0,
        actual_Auth_HTTP_cases=0,actual_two_session_races=0,package_all_five=True,
        prior_runs_aggregated=False,retained_permanent6_fresh_case_credit=0,
        D_complete=False,E_complete=False,global_writer_or_permission_or_lock_closure=False,
        production_go=False,independent_acceptance=False)
    for key,item in expected.items():
        if type(value.get(key))is not type(item)or value[key]!=item:
            raise ValueError('FREE_DATE_DE_EXACT_ACTUAL_QUALIFIED_PARENT_REQUIRED:'+key)
    return value


@contextmanager
def import_scope():
    parent_receipt()
    original=load('free_date_actual_DE_import_scope',
        ROOT/'scripts/current-complete-de-integration-preparation/admission.py')
    with original.import_scope():yield


def admitted():
    receipt=parent_receipt()
    source=load('free_date_DE_own_closed_source',HERE/'source.py').preflight()
    with import_scope():
        product=importlib.import_module('cp7_current_de_free_date.composition')
        parent=product.parent();stage=product.stage()
        for module,path in((product,'cp7_current_de_free_date/composition.py'),
            (parent,'cp7_complete_credit_de/composition.py'),(stage,'cp7_special_free_date_on_de/composition.py')):
            if Path(module.__file__).resolve()!=ROOT/'scripts'/path:
                raise ValueError('FREE_DATE_DE_EXACT_NATURAL_MODULE_ORIGIN_REQUIRED:'+path)
        graph=product.sources();accepted=product.qualified_parent_sources(receipt,graph['parent'])
    return dict(status='ACTUAL_COMPLETE_DE_AND_ADDITIVE_FREE_DATE_SOURCE_ADMITTED',
        current_source=source,current_installation=graph,qualified_parent_sources=accepted,
        qualified_DE30=receipt,whole_parent_graph_compared=True,projected_source_graph=False,
        actual_Native_cases=0,production_go=False,independent_acceptance=False)
