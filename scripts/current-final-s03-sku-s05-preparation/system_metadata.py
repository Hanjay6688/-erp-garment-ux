"""Readonly metadata on the owning candidate; zero business/closure credit."""
from pathlib import Path
from hashlib import sha256
from urllib.parse import urlsplit
import importlib.util
import json

HERE=Path(__file__).resolve().parent
SOURCE_COMMIT='a83f87d76abbd3d94b5e75a50391d1d202b837c9'
SOURCE_PREFIX='scripts/current-global-system-cron-profile-preparation/'
MANIFEST_BYTES=1726
MANIFEST_SHA256='7a1d1b6d930abc96918df8fb35f96ac2a4dd3905c7e230d848c5d4f528b80c47'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def source():
    directory=HERE/'metadata';manifest=directory/'SOURCE.json';raw=manifest.read_bytes()
    if(manifest.is_symlink()or directory.is_symlink()or len(raw)!=MANIFEST_BYTES
       or sha256(raw).hexdigest()!=MANIFEST_SHA256):
        raise ValueError('PERMANENT_SYSTEM_METADATA_EXACT_SOURCE_MANIFEST_REQUIRED')
    declaration=json.loads(raw)
    for name,pin in declaration['files'].items():
        path=directory/name;value=path.read_bytes()
        if(path.is_symlink()or len(value)!=pin['bytes']or sha256(value).hexdigest()!=pin['sha256']):
            raise ValueError('PERMANENT_SYSTEM_METADATA_ORIGINAL_FILE_CHANGED:'+name)
    collector=load('permanent_unchanged_all_namespace_metadata_collector',directory/'collector.py')
    return collector,dict(commit=SOURCE_COMMIT,prefix=SOURCE_PREFIX,
        manifest=dict(bytes=MANIFEST_BYTES,sha256=MANIFEST_SHA256),
        byte_exact_original_files=len(declaration['files'])+1,query_count=len(collector.queries()))


def local_urls(url):
    parsed=urlsplit(url)
    if(parsed.scheme not in('postgres','postgresql')or parsed.hostname not in('127.0.0.1','localhost')
       or parsed.port!=54322 or parsed.path!='/cp6_rollback'or parsed.fragment):
        raise ValueError('PERMANENT_SYSTEM_METADATA_EXACT_LOCAL_CANDIDATE_URI_REQUIRED')
    return [('candidate',url),('primary_scheduler',parsed._replace(path='/postgres').geturl())]


def one(psycopg,url,capture):
    connection=psycopg.connect(url)
    failed=False
    try:
        connection.read_only=True
        connection.isolation_level=psycopg.IsolationLevel.REPEATABLE_READ
        with connection.cursor()as cursor:
            cursor.execute('set local search_path=pg_catalog')
            return capture(cursor)
    except BaseException:
        failed=True
        raise
    finally:
        try:
            try:connection.rollback()
            except psycopg.Error:
                if not failed:raise
        finally:connection.close()


def capture_pair(url,raw_parent_receipt):
    # Do not import a client or open even a metadata connection while parent
    # qualification remains pending. No candidate/state source is projected.
    required=load('permanent_system_metadata_actual_parent_gate',HERE/'persistent_financial.py')
    receipt=required.qualified_receipt(raw_parent_receipt)
    urls=local_urls(url)
    collector,binding=source()
    import psycopg
    result=dict(classification='READONLY_SYSTEM_AND_PRIMARY_SCHEDULER_METADATA_NOT_CLOSURE',
        parent_head=receipt['head'],source=binding,snapshots={},
        separate_snapshots_not_atomic=True,qualification_actors_and_overlays_may_be_observed=True,
        actual_Native_case_credit=0,writer_closure=False,permission_closure=False,
        lockset_approved=False,production_go=False,independent_acceptance=False)
    for kind,target in urls:
        try:
            result['snapshots'][kind]=one(psycopg,target,
                collector.capture if kind=='candidate'else collector.capture_scheduler)
        except psycopg.Error as error:
            # Metadata availability is recorded explicitly. This grants no
            # global acceptance and never masks any financial test failure.
            result['snapshots'][kind]=dict(status='READONLY_METADATA_UNAVAILABLE',
                error_type=type(error).__name__,sqlstate=error.sqlstate,
                error_text_or_connection_details_retained=False,writer_closure=False)
    result['all_metadata_captured']=all(value.get('classification')==
        'ACTUAL_READ_ONLY_ALL_NAMESPACE_SYSTEM_CRON_METADATA_NOT_WRITER_CLOSURE'
        for value in result['snapshots'].values())
    return result
