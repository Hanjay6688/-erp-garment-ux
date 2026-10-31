"""Admit canonical joined37 and the complete natural permanent composition."""
from pathlib import Path
from contextlib import contextmanager
from hashlib import sha256
import importlib,importlib.util,json,os,sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
COMMON=ROOT/'scripts/current-s03-sku-s05-composite-qualification'
MAIN='CP7_CURRENT_S03_SKU_S05_NATIVE31_BROWSER6.json'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def joined37():
    required=load('permanent_requires_terminal_join37_before_ERP',HERE/'persistent_financial.py')
    if required.PARENT_RECEIPT is None:
        raise ValueError('PERMANENT_S05_EXACT_TERMINAL_JOIN37_INTAKE_PENDING')
    raw=Path(os.environ['PERMANENT_JOIN37_ROOT_INTAKE']).read_bytes()
    receipt=required.qualified_receipt(raw)
    # The canonical-byte root intake binds the ENTIRE source graph,
    # plus canonical archive/main hashes and all original gates. Compare that
    # complete canonical graph here rather than reparse its large evidence on
    # every case. The fetcher separately retains the exact original archive.
    return receipt


@contextmanager
def import_scope():
    before_path=list(sys.path);before_argv=sys.argv
    try:
        backend=load('permanent_exact_physical_SKU',HERE/'frozen_parent.py').admitted()
        sys.argv=sys.argv[:1]
        load('permanent_natural_owning_harness_and_parent_modules',HERE/'parent_import.py').parent_modules(Path(backend['path']))
        sys.path.insert(0,str(ROOT/'scripts'));yield
    finally:sys.path[:]=before_path;sys.argv=before_argv


def admitted():
    source=load('permanent_closed_whole_source_before_ERP',HERE/'persistent_source.py').preflight()
    receipt=joined37()
    backend=load('permanent_physical_SKU_before_current_composition',HERE/'frozen_parent.py').admitted()
    with import_scope():
        vendor=importlib.import_module('cp7_vendor_receivable.composition')
        sku=importlib.import_module('cp7_sku_pair_conversion.composition')
        financial=importlib.import_module('cp7_s03_sku_composition.composition')
        complete=importlib.import_module('cp7_current_s03_sku_s05.composition')
        for module,path,root in((vendor,'cp7_vendor_receivable',Path(backend['path'])),
            (sku,'cp7_sku_pair_conversion',Path(backend['path'])),
            (financial,'cp7_s03_sku_composition',ROOT),(complete,'cp7_current_s03_sku_s05',ROOT)):
            if Path(module.__file__).resolve()!=root/'scripts'/path/'composition.py':
                raise ValueError('PERMANENT_S05_NATURAL_ACTUAL_MODULE_ORIGIN_REQUIRED:'+path)
        if complete.parent()is not financial or financial.parent()is not sku or sku.parent()is not vendor:
            raise ValueError('PERMANENT_S05_COMPLETE_NATURAL_PARENT_CHAIN_CHANGED')
        current_financial=financial.sources();actual_sku=sku.sources()
        raw=json.dumps(current_financial,sort_keys=True,separators=(',',':')).encode()
        expected=receipt['qualified_financial_sources']
        if(current_financial['predecessor']!=actual_sku or len(raw)!=expected['bytes']
           or sha256(raw).hexdigest()!=expected['sha256']):
            raise ValueError('PERMANENT_S05_WHOLE_FINANCIAL_SOURCE_MUST_EQUAL_ACTUAL_JOIN37')
        actual_complete=complete.sources()
        if(actual_complete['financial_parent']!=current_financial
           or actual_complete['reader']['parent']!=current_financial):
            raise ValueError('PERMANENT_S05_COMPLETE_READER_PARENT_SOURCE_CHANGED')
    return dict(status='ACTUAL_JOIN37_AND_COMPLETE_PERMANENT_S05_SOURCE_ADMITTED',
        current_source=source,current_installation=actual_complete,qualified_financial_installation=current_financial,
        qualified_join37=receipt,retained_parent_chain_bound_by_entire_actual_join37_source=True,
        physical_qualified_SKU_backend=backend,qualified_SKU_current_installation=actual_sku,
        product_sources_override=False,projected_source_graph=False,used_inverse_guard_before_DDL=True,
        actual_new_case_credit=0,production_go=False,independent_acceptance=False)
