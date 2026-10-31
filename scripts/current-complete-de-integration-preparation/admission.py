"""No actual permanent-parent intake yet: no ERP/runtime/DB admission."""
from pathlib import Path
from hashlib import sha256
from contextlib import contextmanager
import importlib,importlib.util,json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PARENT_HEAD=None
PARENT_RECEIPT=None


def parent_receipt():
    if PARENT_HEAD is None or PARENT_RECEIPT is None:
        raise ValueError('COMPLETE_DE_ACTUAL_PERMANENT_PARENT_INTAKE_PENDING')
    raw=(HERE/'PERMANENT_PARENT_ROOT_ACTUAL_INTAKE.json').read_bytes()
    if len(raw)!=PARENT_RECEIPT['bytes']or sha256(raw).hexdigest()!=PARENT_RECEIPT['sha256']:
        raise ValueError('COMPLETE_DE_EXACT_PERMANENT_PARENT_INTAKE_CHANGED')
    value=json.loads(raw)
    required=dict(status='ROOT_VERIFIED_PERMANENT_S05_NATIVE4_BROWSER2_ALL5',head=PARENT_HEAD,
        complete6_qualified=True,actual_Native_cases=4,actual_browser_cases=2,
        retained_join37_fresh_case_credit=0,package_all_five=True,prior_runs_aggregated=False,
        production_go=False,independent_acceptance=False)
    for key,expected in required.items():
        if type(value.get(key))is not type(expected)or value[key]!=expected:
            raise ValueError('COMPLETE_DE_ACTUAL_QUALIFIED_PERMANENT_PARENT_REQUIRED:'+key)
    return value


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


@contextmanager
def import_scope():
    parent_receipt()  # No inherited ERP import is admitted while pending.
    actual=load('complete_DE_exact_permanent_import_scope',
        ROOT/'scripts/current-final-s03-sku-s05-preparation/admission.py')
    with actual.import_scope():yield


def admitted():
    receipt=parent_receipt()
    source=load('complete_DE_own_closed_source',HERE/'source.py').preflight()
    with import_scope():
        product=importlib.import_module('cp7_complete_credit_de.composition')
        complete,d1,e=product.parts()
        financial=complete.parent()
        for module,path in((product,'cp7_complete_credit_de/composition.py'),
            (complete,'cp7_current_s03_sku_s05/composition.py'),
            (d1,'cp7_credit_correction_de/composition.py'),(e,'cp7_credit_correction_de/e_composition.py'),
            (financial,'cp7_s03_sku_composition/composition.py')):
            if Path(module.__file__).resolve()!=ROOT/'scripts'/path:
                raise ValueError('COMPLETE_DE_CURRENT_NATURAL_MODULE_ORIGIN_REQUIRED:'+path)
        graph=product.sources()
        # This is the whole real lower graph returned by the unchanged natural
        # E -> D1 -> complete source calls, not a projected source map.
        qualified_complete=graph['predecessor']['predecessor']['predecessor']
        accepted=product.qualified_parent_sources(receipt,dict(sources=qualified_complete))
        fixture=load('complete_DE_unchanged_Native30_sources',HERE/'native_business.py').source_controls()
    return dict(status='ACTUAL_PERMANENT6_AND_COMPLETE_DE_NATURAL_SOURCE_ADMITTED',
        current_source=source,current_installation=graph,qualified_complete_sources=accepted,
        qualified_permanent6=receipt,Native30_source=fixture,
        actual_complete_parent_graph_preserved=True,product_sources_override=False,
        projected_source_graph=False,actual_new_case_credit=0,production_go=False,independent_acceptance=False)
