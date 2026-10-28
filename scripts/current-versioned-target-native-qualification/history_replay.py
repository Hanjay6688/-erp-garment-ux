"""The retained immutable-history replay with the current complete used guard.

The new scoped-model parent FK triggers are real catalog additions. A prior
component inverse must not have its old state rewritten to pretend otherwise.
All replay, money, history, stock and time assertions remain exact.
"""
import ast,inspect,uuid
from pathlib import Path
from hashlib import sha256
import cp7_ow11_model_history_runtime_cases as original
import cp7_current_versioned_target_installation as product
import cp7_p21_current_chain_rehearsal_probe as chain
plan,history,source=original.plan,original.history,original.source
query,capture,read,stored,count,same_archive=original.query,original.capture,original.read,original.stored,original.count,original.same_archive
ID=original.IDS['native'][1]
STATE=CHECKER=None


def install(cur):
    assert STATE is not None and callable(CHECKER)
    plan.b.api.admin(cur);CHECKER(cur)
    return None,STATE


def rollback_full(cur,state):
    assert state is STATE
    with chain.helper.control.product_catalog(cur):return product.rollback_preuse(cur,state)


def source_binding():
    before=ast.parse(inspect.getsource(original.cases)).body[0]
    before=next(n for n in before.body if isinstance(n,ast.FunctionDef)and n.name=='replay')
    after=ast.parse(inspect.getsource(cases)).body[0].body[0]
    changes={'rollback_calls':0,'refusal_constants':0}
    class Allowed(ast.NodeTransformer):
        def visit_Call(self,n):
            n=self.generic_visit(n)
            if isinstance(n.func,ast.Attribute)and isinstance(n.func.value,ast.Name)and n.func.value.id=='stage'and n.func.attr=='rollback_preuse':
                n.func=ast.Name(id='rollback_full',ctx=ast.Load());changes['rollback_calls']+=1
            return n
        def visit_Constant(self,n):
            if n.value=='MODEL_HISTORY_RUNTIME_AFTER_USE_REQUIRES_COMPOSED_BACKUP_RESTORE':
                changes['refusal_constants']+=1;return ast.Constant(value='CURRENT_VERSIONED_TARGET_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE')
            return n
    before=Allowed().visit(before)
    assert changes==dict(rollback_calls=1,refusal_constants=1)
    assert ast.dump(before,include_attributes=False)==ast.dump(after,include_attributes=False),'IMMUTABLE_HISTORY_BUSINESS_ASSERTIONS_CHANGED'
    return dict(original_file_sha256=sha256(Path(original.__file__).read_bytes()).hexdigest(),case_id=ID,
        explicit_AST_changes=changes,all_business_assertions_unchanged=True,real_complete_used_guard=True,
        predecessor_catalog_not_rewritten=True,production_go=False)


def cases(cur,today):
    def replay():
        parents,current=install(cur);f=history.fixture(cur,today);q=query(cur,f,today);request=uuid.uuid4()
        physical=plan.monetary_state(cur);one=capture(cur,q,request);frozen=stored(cur,one['run_id'])
        assert one['current_guard']['source_state']=='UNCHANGED'and one['history']['scope']=='SINGLE_CURRENT_PHYSICAL_ROOT'
        assert one['history']['history']['rows'][0]['gross_observed_pcs']=='0'
        assert one['history']['current_stock'][0]['native_available_pcs']=='76'
        assert one['history']['training_known_at']==one['captured_at']
        actual,_=source.capture(cur,q['target_key'],{k:v for k,v in q.items()if k!='target_key'})
        assert one['history']['history']['rows']==actual['result']['history']['rows']
        same_archive(one,capture(cur,q,request));same_archive(one,read(cur,one['run_id']))
        refused=plan.refusal(cur,lambda:capture(cur,dict(q,group_mode='RESTATED'),request))
        assert refused[0:2]==('P0001','CP7_MODEL_HISTORY_REQUEST_CHANGED')
        for sql in('update cp7_model_history_runtime.runs set query=query','delete from cp7_model_history_runtime.runs'):
            assert plan.refusal(cur,lambda:cur.execute(sql))[0:2]==('55000','CP7_RUN_IMMUTABLE')
        assert stored(cur,one['run_id'])==frozen and count(cur)==1 and plan.monetary_state(cur)==physical
        try:rollback_full(cur,current)
        except ValueError as e:assert str(e)=='CURRENT_VERSIONED_TARGET_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'
        else:raise AssertionError('SCOPED_HISTORY_USED_INVERSE_ALLOWED')
        return dict(status='PASS',actual_public_capture_and_replay=True,one_UUID_one_immutable_row=True,
          actual_Native_draft_available76=True,exact_private_source_history_parity=True,
          no_backfilled_training_knowledge=True,after_use_inverse_refused_before_DDL=True,no_stock_money_HPP_change=True)

    return [(ID,replay)]
