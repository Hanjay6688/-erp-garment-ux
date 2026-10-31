"""Private unchanged S05 callbacks reading an already installed full assembly.

No imported product module, method, ROOT or source map is changed. The private
case module receives its own reader dependency. The original reader remains
installed around every actual Native fixture transition and read.
"""
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
import importlib.util

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def permanent_stage(complete,reader,state,control):
    private=ModuleType('private_persistent_S05_reader_dependency')
    private.__file__=str(HERE/'business_reader.py')
    private.parent=lambda:complete
    private.verify=reader.verify
    for name in('ROLE','SCHEMA','FUNCTIONS','PUBLIC'):
        setattr(private,name,getattr(reader,name))
    private.observations=[]
    @contextmanager
    def kept(cursor,actual_state):
        if actual_state!=state:raise ValueError('PERMANENT_S05_EXACT_FULL_STATE_REQUIRED')
        _,_,_,_,catalog=complete.runtime()
        row=dict(status='INCOMPLETE',reader_remains_installed=True,DDL_executed=False)
        private.observations.append(row)
        with control.product_catalog(cursor):
            complete.verify(cursor,state)
            before_catalog,before_data=catalog._catalog_rows(cursor),catalog._data(cursor)
            yield state['reader']
            complete.verify(cursor,state)
            after_catalog,after_data=catalog._catalog_rows(cursor),catalog._data(cursor)
            if before_catalog!=after_catalog or before_data!=after_data:
                raise ValueError('PERMANENT_S05_READER_CHANGED_ALL22_ROWS_OR_ANY_SEQUENCE')
            row.update(status='PASS',before=dict(actual_all22=before_catalog,full_data_and_sequences=before_data),
                after=dict(actual_all22=after_catalog,full_data_and_sequences=after_data))
    private.reader_only=kept
    return private


def business(retained,state):
    admission=load('persistent_browser_requires_actual_join37',HERE/'persistent_financial.py')
    if admission.PARENT_RECEIPT is None:
        raise ValueError('PERMANENT_S05_EXACT_TERMINAL_JOIN37_INTAKE_PENDING')
    from cp7_current_s03_sku_s05 import composition as complete
    from cp7_s05_s03_sku_composition import stage as reader
    from cp7_p21_current_chain_rehearsal_probe import helper
    if state['sources']!=complete.sources():raise ValueError('PERMANENT_S05_COMPLETE_SOURCE_REQUIRED')
    original_stage=retained.stage
    factory=load('persistent_browser_retains_complete_lawful_S05_factory',
        ROOT/'scripts/current-s05-wib-owner-fixture-successor-qualification/factory.py')
    private=factory.business(retained,state)
    if private is retained or private.stage is not original_stage or retained.stage is not original_stage:
        raise ValueError('PERMANENT_S05_PRIVATE_UNCHANGED_CASE_MODULE_REQUIRED')
    if private.IDS!=retained.IDS or len(private.IDS)!=10:
        raise ValueError('PERMANENT_S05_ALL_TEN_ORIGINAL_CALLBACK_IDS_REQUIRED')
    private.stage=permanent_stage(complete,reader,state,helper.control)
    private.sku_parent_binding=dict(original_imported_case_module_unchanged=True,
        original_Native10_callback_bytes_unchanged=True,permanent_reader_dependency=True,
        actual_complete_parent_verified=True,private_constructor_only_routing=True,actual_new_Native_credit=0)
    return private
