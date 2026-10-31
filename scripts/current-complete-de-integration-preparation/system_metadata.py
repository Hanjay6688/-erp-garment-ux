"""Reuse the exact readonly system collector on this owning D1/E candidate.

The actual permanent6 parent gate precedes source loading, URI handling and
any client import. Separate candidate/primary snapshots never prove closure.
"""
from pathlib import Path
import importlib.util

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
INHERITED=ROOT/'scripts/current-final-s03-sku-s05-preparation/system_metadata.py'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def source():
    original=load('complete_DE_exact_inherited_readonly_metadata_wrapper',INHERITED)
    collector,binding=original.source()
    if binding['query_count']!=27:
        raise ValueError('COMPLETE_DE_ALL_ORIGINAL_TWENTY_SEVEN_METADATA_QUERIES_REQUIRED')
    return original,collector,binding


def capture_pair(url):
    receipt=load('complete_DE_actual_parent_before_metadata',HERE/'admission.py').parent_receipt()
    load('complete_DE_closed_source_before_metadata',HERE/'source.py').preflight()
    original,collector,binding=source()
    urls=original.local_urls(url)
    import psycopg
    result=dict(classification='READONLY_CURRENT_DE_SYSTEM_AND_PRIMARY_SCHEDULER_METADATA_NOT_CLOSURE',
        permanent_parent_head=receipt['head'],source=binding,snapshots={},
        separate_snapshots_not_atomic=True,qualification_actors_and_overlays_may_be_observed=True,
        actual_Native_case_credit=0,writer_closure=False,permission_closure=False,
        lockset_approved=False,production_go=False,independent_acceptance=False)
    for kind,target in urls:
        try:
            def observe(cursor):
                base=(collector.capture if kind=='candidate'else collector.capture_scheduler)(cursor)
                identities=load('complete_DE_additive_execution_oid_metadata',HERE/'execution_oids.py')
                base['execution_oid_supplement']=identities.capture(cursor,base)
                dispatch=load('complete_DE_additive_dispatch_oid_metadata',HERE/'dispatch_oids.py')
                base['dispatch_oid_supplement']=dispatch.capture(cursor,base)
                return base
            result['snapshots'][kind]=original.one(psycopg,target,observe)
        except psycopg.Error as error:
            result['snapshots'][kind]=dict(status='READONLY_METADATA_UNAVAILABLE',
                error_type=type(error).__name__,sqlstate=error.sqlstate,
                error_text_or_connection_details_retained=False,writer_closure=False)
    result['all_metadata_captured']=all(value.get('classification')==
        'ACTUAL_READ_ONLY_ALL_NAMESPACE_SYSTEM_CRON_METADATA_NOT_WRITER_CLOSURE'
        for value in result['snapshots'].values())
    return result
