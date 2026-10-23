"""Run the real B installer/catalog APIs against a caller's local SQL engine.

The JSON cursor is a test transport, never a database connection or Native proof.
"""
from pathlib import Path
import importlib
import json
import re
import sys
from types import SimpleNamespace
from psycopg.pq import TransactionStatus

sys.path.insert(0,str(Path(__file__).resolve().parent))
import cp7_ow04_restore_bundle as catalog


def emit(value):
    print(json.dumps(value),flush=True)


class Cursor:
    def __init__(self):
        self.connection=SimpleNamespace(info=SimpleNamespace(transaction_status=TransactionStatus.INTRANS))
        self.rows=[]
        self.ddl=[]

    def execute(self,statement,params=None,**kwargs):
        if not isinstance(statement,str):
            raise ValueError('LOCAL_CURSOR_REQUIRES_TEXT_SQL')
        if re.match(r'\s*(create|alter|drop|grant|revoke)\b',statement,re.I):
            self.ddl.append(statement)
        emit(dict(kind='query',sql=statement,params=params))
        response=json.loads(sys.stdin.readline())
        if not response['ok']:
            raise RuntimeError('LOCAL_SQL_ENGINE: '+response['error'])
        self.rows=response['rows']
        return self

    def fetchone(self):
        return self.rows.pop(0)if self.rows else None

    def fetchall(self):
        rows=self.rows;self.rows=[]
        return rows


def main():
    name=sys.argv[1]
    if name not in('cp7_target_policy_stage','cp7_analysis_finance_bridge','cp7_initial_analysis_stage','cp7_reorder_supply'):
        raise ValueError('LOCAL_STAGE_NOT_ALLOWLISTED')
    module=importlib.import_module(name)
    cur=Cursor();cur.execute('begin')
    before=catalog._catalog_rows(cur)
    state=module.install_delta(cur)
    module.admit_catalog(before,catalog._catalog_rows(cur),state)
    module.rollback_preuse(cur,state)
    if catalog._catalog_rows(cur)!=before:
        raise ValueError('LOCAL_PREUSE_22_GROUPS_NOT_EXACTLY_RESTORED')
    state=module.install_delta(cur)
    module.admit_catalog(before,catalog._catalog_rows(cur),state)
    result=dict(classification='LOCAL_REAL_INSTALLER_AND_PG_CATALOG_VIA_CONTROLLED_TRANSPORT_NOT_NATIVE',
                stage=name,status='PASS',catalog_groups=len(before),
                apply_rollback_reapply_exact=True,admission_passed=True,full_A_chain_qualified=False,production_go=False)
    if name=='cp7_initial_analysis_stage':
        from cp7_ow13a_initial_probe import verify_initial_delta
        state['predecessor_catalog']=before
        installed=catalog._catalog_rows(cur)
        calls=[]
        admitted_current=object()
        admitted_predecessor=object()
        function_oracle=SimpleNamespace(INSTALLED_FUNCTIONS=admitted_current,functions=lambda cursor:admitted_predecessor)
        def predecessor_check(cursor):
            if catalog._catalog_rows(cursor)!=before:
                raise ValueError('LOCAL_LEGACY_ORACLE_NOT_EXACT_PREDECESSOR')
            if function_oracle.INSTALLED_FUNCTIONS is not admitted_predecessor:
                raise ValueError('LOCAL_LEGACY_FUNCTION_ORACLE_NOT_BOUND_TO_PREDECESSOR')
            calls.append(True)
        verify_initial_delta(cur,predecessor_check,state,function_oracle)
        if calls!=[True]or catalog._catalog_rows(cur)!=installed or function_oracle.INSTALLED_FUNCTIONS is not admitted_current:
            raise ValueError('LOCAL_LEGACY_ORACLE_NOT_RESTORED')
        def rejected_predecessor(cursor):
            predecessor_check(cursor)
            raise ValueError('LOCAL_LEGACY_ORACLE_SENTINEL')
        try:
            verify_initial_delta(cur,rejected_predecessor,state,function_oracle)
        except ValueError as error:
            if str(error)!='LOCAL_LEGACY_ORACLE_SENTINEL':raise
        else:
            raise ValueError('LOCAL_LEGACY_ORACLE_FAILURE_SWALLOWED')
        if catalog._catalog_rows(cur)!=installed or function_oracle.INSTALLED_FUNCTIONS is not admitted_current:
            raise ValueError('LOCAL_REJECTED_LEGACY_ORACLE_NOT_RESTORED')
        result.update(legacy_oracle_exact_predecessor=True,
                      legacy_oracle_refusal_propagated=True,legacy_oracle_restored_22_on_pass_and_fail=True,
                      function_oracle_bound_only_after_exact_22_predecessor_and_restored=True)
    cur.execute('commit');emit(dict(kind='ready',result=result))
    if json.loads(sys.stdin.readline())!={'kind':'after_use'}:
        raise ValueError('LOCAL_AFTER_USE_PHASE_REQUIRED')
    cur.execute('begin');cur.ddl=[]
    try:
        module.rollback_preuse(cur,state)
    except ValueError as error:
        if 'AFTER_USE_REQUIRES_BACKUP_RESTORE'not in str(error):
            raise
        result['after_use_refusal']=str(error)
    else:
        raise ValueError('LOCAL_ROLLBACK_FAILED_TO_REFUSE_AFTER_USE')
    if cur.ddl:
        raise ValueError('LOCAL_AFTER_USE_DDL_BEFORE_REFUSAL')
    cur.execute('rollback');cur.execute('begin');module.verify(cur,state);cur.execute('rollback')
    result['after_use_refused_before_first_DDL']=True
    emit(dict(kind='done',result=result))


if __name__=='__main__':main()
