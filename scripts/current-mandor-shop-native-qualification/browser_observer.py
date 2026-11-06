"""Source admission and read-only originals for the exact Mandor browser copy."""
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlparse
import gzip,json,os,re,sys
import admission

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def require(value,message):
    if not value:raise ValueError(message)


def originals():
    import qualification
    raw,parent=qualification.actual_parent()
    require(os.environ.get('MANDOR_BROWSER_CONFIRM')=='cp6_auditor_browser','MANDOR_BROWSER_EXACT_DISPOSABLE_CONFIRMATION')
    import access_runtime
    directory=ROOT/'cp6-proof/t3'
    path=directory/'MANDOR_BROWSER_FIXTURE.json'
    require(not path.is_symlink(),'MANDOR_BROWSER_NO_INPUT_SYMLINK')
    data=path.read_bytes()
    require(sha256(data).hexdigest()==os.environ['MANDOR_BROWSER_FIXTURE_SHA256'],'MANDOR_BROWSER_EXACT_OWNING_ORIGINAL')
    fixture=json.loads(data)
    state_io=access_runtime.load('mandor_complete_browser_state',ROOT/'scripts/current-mandor-afui-preparation/state_io.py')
    state=state_io.observer_state(fixture,directory,os.environ['MANDOR_BROWSER_STATE_SHA256'],
        os.environ['MANDOR_BROWSER_STATE_CACHE_SHA256'])
    require(fixture['contract']=='cp7.mandor-shop-access-fixture.v1'
        and fixture['same_GOOD_source_reused_without_policy_mutation']is True,
        'MANDOR_BROWSER_REAL_COMMITTED_GOOD_AND_INVOICE_REQUIRED')
    require(state['contract']=='cp7.mandor-shop-on-accepted-afui.v1','MANDOR_BROWSER_EXACT_COMPOSED_STATE')
    return fixture,state,parent


def main():
    require(sys.argv[1:]in(['--admit'],['observe']),'MANDOR_BROWSER_READ_ONLY_OBSERVER_COMMAND')
    fixture,state,parent=originals()
    if sys.argv[1]=='--admit':
        return dict(status='ACTUAL_AFUI_PARENT_AND_MANDOR_COMMITTED_BROWSER_SOURCE_ADMITTED',
            fixture={k:fixture[k]for k in('payroll_id','sale_id','contractor_id','payroll_number','sale_number')},
            physical_GOOD_day=fixture['physical']['good_day'],parent_head=parent['head'])
    args=json.load(sys.stdin);label=args['label'];actor=args['actor']
    require(re.fullmatch(r'MANDOR_(DESKTOP|MOBILE390)_[A-Z0-9_]+',label)is not None,
        'MANDOR_BROWSER_FIXED_ORIGINAL_LABEL')
    require(re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',actor)is not None,
        'MANDOR_BROWSER_ACTUAL_AUTH_ACTOR_UUID')
    url=os.environ['AUDITOR_BROWSER_DB_URL'];parsed=urlparse(url)
    require(parsed.hostname in('localhost','127.0.0.1')and parsed.port==54322
        and parsed.path=='/cp6_auditor_browser','MANDOR_BROWSER_ONLY_FIXED_LOCAL_COPY')
    import qualification,access_cases
    product=qualification.runtime().product
    product.domain_modules=product.fixture.domain_modules()[0]
    context=access_cases.Context(product,state,dict(fixture,actor=actor),'BROWSER')
    import psycopg
    with psycopg.connect(url,connect_timeout=5)as conn,conn.cursor()as cur:
        cur.execute("set local statement_timeout='45s';set local lock_timeout='8s'")
        # The complete raw catalog equals the pinned owning installation;
        # never use or reconstruct another process's Native control.STATE.
        value=context.snapshot(cur);conn.rollback()
    raw=(json.dumps(value,sort_keys=True,default=str)+'\n').encode();packed=gzip.compress(raw,mtime=0)
    name=label+'_FULL_CENSUS.json.gz';path=ROOT/'cp6-proof/t3'/name
    with path.open('xb')as stream:stream.write(packed)
    catalog=value.pop('actual_all22')
    return dict(value,catalog_groups=22,catalog_sha256=sha256(json.dumps(catalog,sort_keys=True,default=str).encode()).hexdigest(),
        dropped_catalog_fields=[],dropped_data_or_sequence_keys=[],Native_overlay_applied=False,
        original=dict(name=name,bytes=len(raw),sha256=sha256(raw).hexdigest(),gzip_bytes=len(packed),gzip_sha256=sha256(packed).hexdigest()))


if __name__=='__main__':print(json.dumps(main(),default=str))
