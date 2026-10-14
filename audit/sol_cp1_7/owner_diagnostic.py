"""New diagnostic qualification, preserving all native owner/install guards.
Capture the exception hidden by the installer's public error-code projection.
No SQL, role, fixture, ordering or case assertion is changed.
"""
import hashlib,json,sys,traceback
from pathlib import Path
import psycopg
CANDIDATE=Path(__file__).resolve().parents[3]/'auditor'
sys.path.insert(0,str(CANDIDATE/'scripts'))
OUT=CANDIDATE/'cp6-proof/t3/SOL_OWNER_DIAGNOSTIC.json'
observed=[]
class DiagnosticCursor(psycopg.Cursor):
 def execute(self,query,params=None,**kwargs):
  try:return super().execute(query,params,**kwargs)
  except Exception as error:
   observed.append(dict(sqlstate=getattr(error,'sqlstate',None),message=str(error),
      statement_sha256=hashlib.sha256(str(query).encode()).hexdigest(),
      context=getattr(getattr(error,'diag',None),'context',None)))
   OUT.parent.mkdir(parents=True,exist_ok=True)
   OUT.write_text(json.dumps(dict(original_run=38564307650,original_job=115852968691,
      source_sha='0b7049d9203bac52b47a4c89f3e0d75646067a8f',
      diagnostic_only=True,oracle_change=False,SQL_change=False,errors=observed,production_go=False),indent=2)+'\n')
   raise
original=psycopg.connect
def connect(*args,**kwargs):
 kwargs['cursor_factory']=DiagnosticCursor
 return original(*args,**kwargs)
psycopg.connect=connect
import cp6_readiness_owner_test as probe
probe.main()
