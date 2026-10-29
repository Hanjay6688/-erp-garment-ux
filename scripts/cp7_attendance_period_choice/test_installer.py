"""Pure context controls; causal PostgreSQL role behavior is installer.test.ts."""
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace as NS
import sys,unittest
from psycopg.pq import TransactionStatus
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cp7_attendance_period_choice import installer_ddl as ddl


def rows():
    return [dict(schema=name,actor='postgres',session_actor='qualified_outer',role_setting='postgres',
        owner=owner,raw_acl='{'+owner+'=UC/'+owner+',postgres=U/'+owner+'}',usage=True,create=False,
        actor_can_set_owner=False,session_can_set_owner=True,actor_superuser=False,session_superuser=True)
        for name,owner in sorted(ddl.SCHEMAS.items())]


class InstallerContext(unittest.TestCase):
    def test_session_authority_not_current_actor_membership_and_CREATE_only(self):
        plan=ddl.plan_inventory(rows())
        self.assertEqual(plan['temporary_CREATE_schemas'],sorted(ddl.SCHEMAS))
        sql='\n'.join(statement for statement,_ in plan['enter']+plan['leave'])
        self.assertEqual(sql.count('grant create on schema '),2)
        self.assertEqual(sql.count('revoke create on schema '),2)
        for forbidden in('grant usage','grant all','grant cp7_','alter role','default privileges','update pg_'):
            self.assertNotIn(forbidden,sql)
    def test_no_new_set_authority_owner_actor_or_usage_is_invented(self):
        for key,value,expected in(('actor','unexpected','AUTHORITY'),('owner','unexpected','AUTHORITY'),
            ('usage',False,'PREEXISTING_USAGE'),('session_can_set_owner',False,'EXISTING_SET'),
            ('create',0,'BOOLEAN'),('raw_acl',None,'RAW_NULL_GRANT')):
            bad=deepcopy(rows());bad[0][key]=value
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,expected):ddl.plan_inventory(bad)
    def test_preexisting_CREATE_including_raw_NULL_is_never_granted_or_revoked(self):
        model=rows()
        for row in model:row.update(create=True,raw_acl=None)
        plan=ddl.plan_inventory(model);self.assertEqual(plan['enter'],[]);self.assertEqual(plan['leave'],[])
    def context(self,model=None,status=TransactionStatus.INTRANS,after=None):
        before=model or rows();queue=[before,deepcopy(before)if after is None else after];calls=[]
        def execute(statement,args=()):
            calls.append((statement,args))
            if statement==ddl.INVENTORY_SQL:
                values=queue.pop(0)
                return NS(fetchall=lambda:[tuple(row[key]for key in ddl.KEYS)for row in values])
            return NS()
        cur=NS(execute=execute,connection=NS(info=NS(transaction_status=status)))
        return cur,calls
    def test_success_restores_exact_inventory_before_exposing_state(self):
        cur,calls=self.context()
        with ddl.existing_schema_ddl(cur):cur.execute('MODEL_EXISTING_FUNCTION_DDL')
        statements=[sql for sql,_ in calls]
        self.assertLess(statements.index('grant create on schema cp7_hpp_pool to postgres'),statements.index('MODEL_EXISTING_FUNCTION_DDL'))
        self.assertGreater(statements.index('revoke create on schema cp7_payroll from postgres'),statements.index('MODEL_EXISTING_FUNCTION_DDL'))
        self.assertEqual(statements[-1],ddl.INVENTORY_SQL)
    def test_python_error_cleans_usable_transaction_and_preserves_original_error(self):
        cur,calls=self.context()
        with self.assertRaisesRegex(RuntimeError,'MODEL_DDL_FAILURE'):
            with ddl.existing_schema_ddl(cur):raise RuntimeError('MODEL_DDL_FAILURE')
        self.assertEqual(calls[-1][0],ddl.INVENTORY_SQL)
    def test_SQL_aborted_transaction_does_not_issue_cleanup_or_hide_original_error(self):
        cur,calls=self.context()
        with self.assertRaisesRegex(RuntimeError,'MODEL_SQL_ERROR'):
            with ddl.existing_schema_ddl(cur):
                cur.connection.info.transaction_status=TransactionStatus.INERROR
                raise RuntimeError('MODEL_SQL_ERROR')
        self.assertFalse(any(sql.startswith('revoke ')for sql,_ in calls))
        self.assertEqual(sum(sql==ddl.INVENTORY_SQL for sql,_ in calls),1)
    def test_changed_raw_acl_owner_or_existing_privilege_refuses_not_normalizes(self):
        for key,value in(('raw_acl','{normalized-but-different}'),('owner','unexpected'),('create',True)):
            after=deepcopy(rows());after[0][key]=value;cur,_=self.context(after=after)
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'EXACT_RAW_AUTHORITY_NOT_RESTORED'):
                with ddl.existing_schema_ddl(cur):pass


if __name__=='__main__':unittest.main()
