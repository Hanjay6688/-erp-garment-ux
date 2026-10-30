"""Execute the full extracted used block on faithful API doubles: Native0/DB0."""
from contextlib import contextmanager
from datetime import date
from types import SimpleNamespace, ModuleType
from unittest import TestCase
import midnight_derive as derive


class Cursor:
    def __init__(self, log):
        self.log=log
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def execute(self,sql,args=()):
        self.log.append(sql)
        self.answer=(1,) if 'count(*) from erp.app_users' in sql else (date(2026,10,30),)
        return self
    def fetchone(self):return self.answer


class Connection:
    def __init__(self,log):self.log=log
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def cursor(self):return Cursor(self.log)
    def commit(self):self.log.append('COMMIT_REAL_WRITER_API_DOUBLE')
    def rollback(self):self.log.append('ROLLBACK_API_DOUBLE')


def doubles(changed_sequence=False, refuse=True):
    log=[]
    @contextmanager
    def catalog_context(cursor):
        log.append('PHYSICAL_PRODUCT_CATALOG_DOUBLE')
        yield
    n={'data':0}
    def data(cursor):
        n['data']+=1
        # One strict-case sequence allocation, then actual used allocation.
        value=2 if n['data']==1 else 3
        if changed_sequence and n['data']>=3:value=4
        return {'table:LOCAL':{'immutable':'rows'},'sequence:LOCAL':value}
    catalog=SimpleNamespace(_data=data,_catalog_rows=lambda cur:{str(i):{} for i in range(22)})
    product=SimpleNamespace(USED_ERROR='LOCAL_PRODUCT_AFTER_USE_REQUIRES_FULL_RESTORE',
        runtime=lambda:(None,None,None,None,catalog),verify=lambda *a:log.append('ACTUAL_VERIFY_API_DOUBLE'))
    def inverse(cur,state):
        log.append('INVERSE_CALLED_BEFORE_ANY_DDL')
        if refuse:raise ValueError(product.USED_ERROR)
    product.rollback_delta_preuse=inverse
    fixture={'day':date(2026,10,24)}
    business=SimpleNamespace(
        f=SimpleNamespace(admin=lambda cur:None,assert_pool=lambda *a:{'LOCAL_NATIVE_POOL_ORACLE_DOUBLE':True}),
        pair=lambda *a:(fixture,date(2026,10,25),{'LOCAL_PHYSICAL_DOUBLE':True}),
        original_accrual=lambda *a:{'LOCAL_IMMUTABLE_ACCRUAL_DOUBLE':True},
        source_hash=lambda *a:'LOCAL_IMMUTABLE_SOURCE_BINDING_DOUBLE',
        allocate=lambda *a:log.append('ACTUAL_ALLOCATE_WRITER_API_DOUBLE') or {'event_id':'LOCAL_DOUBLE'},
        cases=lambda *a,**k:(_ for _ in ()).throw(AssertionError('FRESH11_FACTORY_MUST_NOT_RUN')))
    truth=SimpleNamespace(all_truth=lambda cur:{'LOCAL_FINANCIAL_TRUTH_DOUBLE':True},truth_quiet=lambda a,b:a==b)
    state={'preuse_data_and_sequences':{'table:LOCAL':{'immutable':'rows'},'sequence:LOCAL':1}}
    return log,product,business,truth,state,catalog_context


class UsedWitnessControls(TestCase):
    def run_block(self,**kwargs):
        module=ModuleType('local_exact_used_block_double')
        code,proof=derive.witness((derive.OLD/'native_runner.py').read_bytes())
        exec(compile(code,'local-exact-used-block-double','exec'),module.__dict__)
        log,product,business,truth,state,physical=doubles(**kwargs)
        report={}
        module.committed_used_witness(None,SimpleNamespace(product_catalog=physical),state,report,'LOCAL_URL_DOUBLE',
            business,product,truth,SimpleNamespace(connect=lambda url:Connection(log)),
            lambda *a:log.append('LOCAL_DATABASE_IDENTITY_API_DOUBLE'),module.sequence_prefix)
        return log,report

    def test_actual_writer_commit_and_exact_all22_rows_sequences_refusal_block(self):
        log,report=self.run_block()
        self.assertLess(log.index('ACTUAL_ALLOCATE_WRITER_API_DOUBLE'),log.index('COMMIT_REAL_WRITER_API_DOUBLE'))
        self.assertLess(log.index('COMMIT_REAL_WRITER_API_DOUBLE'),log.index('INVERSE_CALLED_BEFORE_ANY_DDL'))
        self.assertEqual(report['actual_Native_cases'],1)
        self.assertTrue(report['original_accrual_and_source_binding_unchanged'])
        self.assertEqual(report['used_inverse_refusal_before'],report['used_inverse_refusal_after'])
        self.assertEqual(len(report['used_inverse_refusal_before']['actual_all22']),22)
        self.assertFalse(report['strict_group_scope']['complete_sequence_restore_proved'])

    def test_changed_sequence_during_used_refusal_is_not_projected_away(self):
        with self.assertRaisesRegex(ValueError,'USED_REFUSAL_CHANGED_ALL22_ROWS_SEQUENCES'):
            self.run_block(changed_sequence=True)

    def test_missing_real_used_refusal_fails(self):
        with self.assertRaisesRegex(AssertionError,'USED_INVERSE_NOT_REFUSED'):
            self.run_block(refuse=False)
