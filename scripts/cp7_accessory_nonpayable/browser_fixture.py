"""Read-only complete browser census on the exact admitted local copy."""
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlparse
import gzip,json,os,re,sys

ROOT=Path(__file__).resolve().parents[2]


def observer_state(prepared, directory, environ):
    from cp7_accessory_nonpayable import complete_original_io

    inputs = prepared.get('observer_catalogue')
    if (type(inputs) is not dict or set(inputs) != {'after', 'original', 'cache'}
            or type(inputs['after']) is not dict or len(inputs['after']) != 22):
        raise ValueError('NONPAYABLE_BROWSER_COMPLETE_OBSERVER_CATALOGUE_REQUIRED')
    for key, name, variable in (
            ('original', 'AFUI_BROWSER_SETTINGS_STATE.json', 'AFUI_BROWSER_STATE_SHA256'),
            ('cache', 'AFUI_BROWSER_SETTINGS_STATE_CACHE.json', 'AFUI_BROWSER_STATE_CACHE_SHA256')):
        expected = inputs[key]
        if (type(expected) is not dict or set(expected) != {'name', 'bytes', 'sha256'}
                or expected['name'] != name or type(expected['bytes']) is not int
                or expected['sha256'] != environ[variable]
                or expected != dict(name=name, **complete_original_io.pin(directory / name))):
            raise ValueError('NONPAYABLE_BROWSER_EXACT_BOUND_STATE_ORIGINAL_REQUIRED:' + key)
    return dict(after=inputs['after'])


def main():
    if sys.argv[1:]!=['observe']:raise ValueError('NONPAYABLE_BROWSER_READ_ONLY_OBSERVATION_REQUIRED')
    args=json.load(sys.stdin)
    sys.path.insert(0,str(ROOT/'scripts'))
    from cp7_accessory_nonpayable import admission
    admission.parent_receipt()  # Before importing psycopg or the domain graph.
    if os.environ.get('AFUI_BROWSER_CONFIRM')!='cp6_auditor_browser':
        raise ValueError('NONPAYABLE_BROWSER_EXPLICIT_DISPOSABLE_COPY_REQUIRED')
    url=os.environ['AUDITOR_BROWSER_DB_URL'];parsed=urlparse(url)
    if parsed.hostname not in('127.0.0.1','localhost')or parsed.port!=54322 or parsed.path!='/cp6_auditor_browser':
        raise ValueError('NONPAYABLE_BROWSER_LOCAL_COPY_ONLY')
    label=args['label']
    if not re.fullmatch(r'AFUI_(DESKTOP|MOBILE390)_[A-Z0-9_]+',label):
        raise ValueError('NONPAYABLE_BROWSER_BOUND_EVIDENCE_LABEL_REQUIRED')
    saved=sys.argv
    try:
        sys.argv=sys.argv[:1]
        import psycopg
        from cp7_accessory_nonpayable import access_cases,native_fixture,complete_original_io
        refusal='NONPAYABLE_BROWSER_EXACT_ORIGINAL_STATE_AND_NATIVE_FIXTURE_REQUIRED'
        directory = ROOT/'cp6-proof/t3'
        prepared=complete_original_io.read_verified_json(directory/'AFUI_BROWSER_NATIVE_PREREQUISITE.json',os.environ['AFUI_BROWSER_FIXTURE_SHA256'],refusal)
        if prepared['status']!='ACTUAL_NATIVE_NONPAYABLE_BROWSER_PREREQUISITE_PREPARED':
            raise ValueError('NONPAYABLE_BROWSER_ACTUAL_NATIVE_PREREQUISITE_REQUIRED')
        state = observer_state(prepared, directory, os.environ)
        with psycopg.connect(url,connect_timeout=5)as conn,conn.cursor()as cur:
            cur.execute("set local statement_timeout='45s';set local lock_timeout='8s'")
            modules=access_cases.browser_observation_context(cur,state);value=access_cases.capture_browser_observed(cur,modules,state)
            actual=native_fixture.observe(cur,modules,prepared['fixture'])
            native_fixture.require_economics(actual,prepared['fixture'],nonpayable=True,hpp='20')
            value['active_good']=actual
            name=label+'_FULL_CURRENT_CENSUS.json.gz';target=ROOT/'cp6-proof/t3'/name
            original=complete_original_io.save_gzip_sorted(target,value)
            complete_original_io.publish(target)
            catalog=modules.product.runtime()[-1]
            reply=dict(catalog_groups=22,catalog_sha256=catalog.digest(value['catalog']),
                data_and_sequences=value['data_and_all_sequences'],date_versions=value['date_versions'],
                date_requests=value['date_requests'],active_good=actual,
                dropped_catalog_fields=[],dropped_data_or_sequence_keys=[],
                original=original)
            conn.rollback();return reply
    finally:sys.argv=saved

if __name__=='__main__':print(json.dumps(main(),default=str))

