"""Freeze the synthetic clean database after the CP6 package and prove a second cluster boots from these files."""
import hashlib
import json
import os
import secrets
import subprocess
import tempfile
import time
from pathlib import Path

import cp6_g01_fingerprint as fingerprint
from close11 import checkpoint, frozen

OUT = Path(os.environ['CP75_OUTPUT'])
OUT.mkdir(parents=True, exist_ok=True)
CONTAINER = frozen.SOURCE
SQL = """select jsonb_build_object('database',current_database(), 'pg',current_setting('server_version_num'),
    'auth_users',(select count(*) from auth.users),'app_users',(select count(*) from erp.app_users),
    'application_migrations',(select count(*) from erp.schema_migrations),
    'ab',(select count(*) from erp.schema_migrations where version='v2.6.20ab'),
    'bf',(select count(*) from erp.schema_migrations where version='v2.6.20bf'),
    'bf_platform',(select count(*) from supabase_migrations.schema_migrations where version='20260928134500'),
    'platform_migrations',(select count(*) from supabase_migrations.schema_migrations),
    'platform_ledger_sha256',(select encode(sha256(convert_to(jsonb_agg(to_jsonb(m) order by version)::text,'UTF8')),'hex')
                               from supabase_migrations.schema_migrations m),
    'recovery',pg_is_in_recovery())"""


def query(container, db, stmt):
    raw = frozen.docker('read clean checkpoint', ['exec','-u','postgres',container,'psql','-U','supabase_admin',
                         '-d',db,'-XAtq','-v','ON_ERROR_STOP=1','-c',stmt],timeout=180)
    return json.loads(raw)


def readback(container):
    result = {db: query(container,db,SQL) for db in ('postgres','cp6_rollback')}
    for db,row in result.items():
        assert row['pg']=='170006' and row['auth_users']==row['app_users']==0 and row['recovery'] is False
        groups = query(container, db, fingerprint.SUMMARY)
        row.update(catalogue_groups=len(groups), catalogue_sha256=hashlib.sha256(
            json.dumps(groups,sort_keys=True, separators=(',',':')).encode()).hexdigest())
    assert result['postgres']['ab']==1 and result['postgres']['bf']==0
    assert result['cp6_rollback']['bf_platform']==result['cp6_rollback']['bf']==1
    return result


def boot(archive, info, image):
    name = 'cp75-clean-bf-review-' + os.environ['GITHUB_RUN_ID']
    data, config = name+'-data',name+'-config'
    resources = []
    try:
        for v in [data,config]:
            frozen.docker('create temporary verification volume',['volume','create',v]);resources.append(v)
        with archive.open('rb') as src:
            frozen.docker('unpack verified BF checkpoint', ['run','--rm','-i','--network','none','--user','0',
                '-v', data+':/restore/data','-v',config+':/restore/config','--entrypoint','sh',image,'-ec',
                'tar -C /restore -xzf -; chmod 700 /restore/data; chown postgres:postgres /restore/data; '+frozen.verify_files(info)],
                input_file=src, timeout=480)
        subprocess.run(['docker','run','-d','--network','none','-e','POSTGRES_PASSWORD','--name',name,'-v',data+':/var/lib/postgresql/data',
                        '-v',config+':/etc/postgresql-custom',image,'postgres','-c','config_file=/etc/postgresql/postgresql.conf',
                        '-c','cron.launch_active_jobs=off'],env={**os.environ,'POSTGRES_PASSWORD':secrets.token_urlsafe(32)},
                       check=True,stdout=subprocess.DEVNULL)
        for _ in range(120):
            try:
                if query(name,'postgres','select to_jsonb(not pg_is_in_recovery())') is True:break
            except ValueError:
                pass
            time.sleep(1)
        else:raise RuntimeError('BF checkpoint did not complete WAL recovery')
        return readback(name)
    finally:
        subprocess.run(['docker','rm','-f',name],capture_output=True)
        for v in resources:subprocess.run(['docker','volume','rm',v],check=True,capture_output=True)


def main():
    folder = Path(os.environ['GITHUB_WORKSPACE'])/'auditor/cp6-proof/t3'
    install = json.loads((folder/'CP75_RELEASE_FILES.json').read_text())
    assert install['status']=='ALL_FILES_INSTALLED' and len(install['files'])==30
    assert all(x['status']=='PASS' for x in install['files'])
    source = readback(CONTAINER)
    image = frozen.docker('read installed test image',['inspect','-f','{{.Image}}',CONTAINER])
    digests = json.loads(frozen.docker('read Registry digest',['image','inspect','-f','{{json .RepoDigests}}',image]))
    assert digests and '@sha256:' in digests[0]
    public_key = Path(os.environ['GITHUB_WORKSPACE'])/'capture/qualification/close11/auditor-public.pem'
    with tempfile.TemporaryDirectory(dir=os.environ['RUNNER_TEMP']) as td:
        raw = Path(td)/'cp75-bf.tar.gz'
        info = frozen.freeze(raw,image)
        verified = boot(raw,info,image)
        assert verified==source
        encrypted = checkpoint.seal(raw,OUT/'clean-bf.cp75',public_key)
        receipt = dict(stage='CP75_CLEAN_THROUGH_V2620BF', clean_foundation_run=44764387328, package_steps=30, foundation_steps=40,
                       candidate='48858590a361343e73a7f16f6646363dc155c04e', parent='486d344e0ce47d2b184e2a7bfccf2a927424d184',
                       run=os.environ['GITHUB_RUN_ID'], runner=os.environ['GITHUB_SHA'], image=digests[0], source=source, restored=verified,
                       copy=info, archive=encrypted, plaintext_sha256=checkpoint.digest(raw), public_key_sha256=checkpoint.digest(public_key),
                       source_and_isolated_boot_equal=True, final_global_comparison=False, production_go=False)
        (OUT/'clean-bf.json').write_text(json.dumps(receipt,indent=2)+'\n')
        print('CP7.5 clean v2.6.20bf on both clusters, 30 release files verified', flush=True)


if __name__=='__main__': main()
