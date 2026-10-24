"""Generate public TypeScript from the actual installed disposable database.

Retain generator output byte for byte. This never selects a linked/hosted
project and never substitutes a hand-written type definition.
"""
from hashlib import sha256
from pathlib import Path
import subprocess
from psycopg.conninfo import conninfo_to_dict

CLI_VERSION='2.116.0'
REQUIRED=('erp_cp7_get_staged_production_schedule_v1',
    'erp_cp7_save_staged_production_schedule_v1',
    'erp_cp7_request_bounded_staged_analysis_v1')


def generate(url,out):
    info=conninfo_to_dict(url)
    if info.get('host')not in('127.0.0.1','localhost') or info.get('dbname')!='cp6_rollback' \
            or info.get('user')!='postgres' or info.get('port')!='54322':
        raise ValueError('GENERATED_TYPES_DISPOSABLE_DATABASE_REQUIRED')
    version=subprocess.run(['supabase','--version'],capture_output=True,check=True).stdout.decode().strip()
    if version!=CLI_VERSION:raise ValueError('GENERATED_TYPES_PINNED_CLI_REQUIRED')
    help_run=subprocess.run(['supabase','gen','types','--help'],capture_output=True,check=True)
    for flag in (b'--db-url',b'--schema',b'--lang'):
        if flag not in help_run.stdout:raise ValueError('GENERATED_TYPES_CLI_CONTRACT_CHANGED')
    run=subprocess.run(['supabase','gen','types','--db-url',url,'--schema','public','--lang','typescript'],
        capture_output=True,timeout=180)
    if run.returncode:
        raise ValueError('GENERATED_TYPES_CLI_FAILED: exit='+str(run.returncode)+
            '; stderr_sha256='+sha256(run.stderr).hexdigest())
    raw=run.stdout
    if b'export type Database'not in raw or any((name+':').encode()not in raw for name in REQUIRED):
        raise ValueError('GENERATED_TYPES_CURRENT_PUBLIC_FACADES_MISSING')
    target=Path(out);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    return dict(status='PASS',generator='supabase gen types',cli_version=version,
        schema='public',database='cp6_rollback',hosted=False,raw_name=target.name,
        raw_bytes=len(raw),raw_sha256=sha256(raw).hexdigest(),required_facades=list(REQUIRED),
        generator_help_sha256=sha256(help_run.stdout).hexdigest(),
        client_contract_replaced=False,production_go=False)
