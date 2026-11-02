"""Three reversible routes in the previously qualified whole-package engine.

Only the parent, installation connection and declared coverage change. The
unused inverse/reinstall, used refusal, complete dump/restore, role cleanup,
all22/all rows/all sequences, public state and advisor machinery remain exact.
This module provides source data and cannot dispatch a package on import.
"""
from pathlib import Path
from hashlib import sha256
import subprocess

ROOT=Path(__file__).resolve().parents[2]
ORIGINAL='scripts/current-vendor-receivable-qualification/probe.py'
ORIGIN='0da4d79a4f7201ef053d6de1eb155d990b4bfa4d'
PIN=(12667,'c420d894f8d5f16bddefeae73addb621507170f372a28e7d6e33d88c7eeb0be9')
INSTALL_BEFORE="prior=measured(timings,'SINGLE_FULL_READONLY_PARENT_INSTALL',readonly.install,cur)\n                prior=measured(timings,'EXACT_BACKEND3194_PARENT_INSTALL',product.parent().install_delta,cur,prior)"
INSTALL_AFTER="prior=measured(timings,'ACTUAL_QUALIFIED_AFUI15_PARENT_INSTALL',product.parent().install,cur)"
CONNECTION_BEFORE="with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:\n            try:\n                report['install_boundary_lock']"
CONNECTION_AFTER="with trusted_installer_connection()as conn,conn.cursor()as cur:\n            try:\n                report['install_boundary_lock']"
COUNTS_BEFORE="""report['actual_two_session_races']=3
            report['actual_Native_cases']=7
            report['actual_Auth_HTTP_cases']=1
            report['actual_browser_cases']=0
            report['actual_business_cases']=11
            report['real_Auth_HTTP_qualified']=True"""
COUNTS_AFTER="""report['actual_two_session_races']=0
            report['actual_Native_cases']=6
            report['actual_Auth_HTTP_cases']=0
            report['actual_browser_cases']=0
            report['actual_business_cases']=6
            report['real_Auth_HTTP_qualified']=False
            report['actual_Mandor_Auth_browser_race_and_return_correction_acceptance_pending']=True"""


def derive(raw):
    if(len(raw),sha256(raw).hexdigest())!=PIN:raise ValueError('MANDOR_ENGINE_EXACT_ORIGINAL_BYTES')
    if raw!=subprocess.check_output(['git','-C',str(ROOT),'show',ORIGIN+':'+ORIGINAL]):
        raise ValueError('MANDOR_ENGINE_EXACT_ORIGINAL_PUBLIC_BLOB')
    text=raw.decode();routes=[]
    for before,after in[(INSTALL_BEFORE,INSTALL_AFTER),(CONNECTION_BEFORE,CONNECTION_AFTER),(COUNTS_BEFORE,COUNTS_AFTER)]:
        if text.count(before)!=1 or after in text:raise ValueError('MANDOR_ENGINE_ONE_REVIEWED_ROUTE_REQUIRED')
        text=text.replace(before,after,1);routes.append(dict(before=before,after=after,count=1))
    restored=text
    for route in reversed(routes):
        if restored.count(route['after'])!=1:raise ValueError('MANDOR_ENGINE_ONE_INVERSE_SITE_REQUIRED')
        restored=restored.replace(route['after'],route['before'],1)
    if restored.encode()!=raw:raise ValueError('MANDOR_ENGINE_COMPLETE_ORIGINAL_NOT_RECOVERED')
    compile(text,'mandor_exact_whole_package_engine','exec')
    return text,dict(original=dict(bytes=PIN[0],sha256=PIN[1]),derived_sha256=sha256(text.encode()).hexdigest(),routes=routes,
        original_engine_fully_recovered=True,normal_business_connection_unchanged=True,
        only_install_transaction_uses_fixed_local_trusted_maintenance=True,
        full_restore_role_cleanup_all22_rows_sequences_public_and_advisors_unchanged=True,
        actual_SQL_executed=0,actual_Native_cases=0,actual_Auth_HTTP_cases=0,production_go=False,independent_acceptance=False)
