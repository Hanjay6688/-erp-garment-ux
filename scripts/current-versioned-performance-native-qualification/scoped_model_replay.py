"""The retained scoped-model replay with the current complete used guard.

The versioned-target overlay changes real predecessor functions. A prior
component inverse must not have its old state rewritten to pretend otherwise.
All replay, money, history, stock and time assertions remain exact.
"""
import ast,inspect,uuid
from pathlib import Path
from hashlib import sha256
import cp7_ow11_model_scoped_evaluation_cases as original
import cp7_current_versioned_performance_installation as product
import cp7_p21_current_chain_rehearsal_probe as chain
plan,history,model,parent=original.plan,original.history,original.model,original.parent
capture,read,stored=original.capture,original.read,original.stored
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
            if n.value=='MODEL_SCOPED_EVALUATION_AFTER_USE_REQUIRES_COMPOSED_BACKUP_RESTORE':
                changes['refusal_constants']+=1;return ast.Constant(value='CURRENT_VERSIONED_PERFORMANCE_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE')
            return n
    before=Allowed().visit(before)
    assert changes==dict(rollback_calls=1,refusal_constants=1)
    assert ast.dump(before,include_attributes=False)==ast.dump(after,include_attributes=False),'SCOPED_MODEL_BUSINESS_ASSERTIONS_CHANGED'
    return dict(original_file_sha256=sha256(Path(original.__file__).read_bytes()).hexdigest(),case_id=ID,
        explicit_AST_changes=changes,all_business_assertions_unchanged=True,real_complete_used_guard=True,
        predecessor_catalog_not_rewritten=True,production_go=False)


def cases(cur,today):
    def replay():
        _, current = install(cur)
        actor = model.master.role_actor(cur, 'OWNER')
        _, q, h = parent.prepare(cur, today, actor)
        p = parent.query(h, q)
        physical = plan.monetary_state(cur)
        m, _ = capture(cur, p, actor, h['request_id'])
        frozen = stored(cur, m['run_id'])
        assert m['contract_version'] == 'cp7.scoped-model-run.v3'
        assert m['assessment']['activation']['state'] == 'BASELINE_REQUIRED'
        assert m['assessment']['activation']['reason'] == 'EXPLICIT_ACTIVATION_POLICY_REQUIRED'
        assert frozen['input']['known_as_of'] == h['captured_at']
        assert all(row['known_at'] == h['captured_at'] and row['state'] == 'UNKNOWN' and row['value'] is None for row in frozen['input']['series'])
        history.same_archive(m, capture(cur, p, actor, m['request_id'])[0])
        history.same_archive(m, read(cur, m['run_id'], actor))
        assert plan.refusal(cur, lambda: capture(cur, dict(p, horizon_days='8'), actor, m['request_id']))[0:2] == ('P0001', 'CP7_SCOPED_EVALUATION_REQUEST_CHANGED')
        for command in ('update cp7_model_scoped_evaluation.runs set input=input', 'delete from cp7_model_scoped_evaluation.runs'):
            assert plan.refusal(cur, lambda: cur.execute(command))[0:2] == ('55000', 'CP7_RUN_IMMUTABLE')
        assert stored(cur, m['run_id']) == frozen and plan.monetary_state(cur) == physical
        try: rollback_full(cur, current)
        except ValueError as e: assert str(e) == 'CURRENT_VERSIONED_PERFORMANCE_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'
        else: raise AssertionError('SCOPED_MODEL_AFTER_USE_INVERSE_ALLOWED')
        assert cur.execute('select count(*)from cp7_model_scoped_evaluation.runs').fetchone()[0] == 1
        assert cur.execute('select count(*)from cp7_model_registry_adapter.runs').fetchone()[0] == 0
        return dict(status='PASS', actual_scoped_history_and_retained_model=True, exact_UUID_replay=True,
          same_UUID_separate_method_namespace=True, old_model_table_unchanged=True,
          actual_knowledge_clock_preserved=True, UNKNOWN_not_zero=True, after_use_inverse_refused=True)

    return [(ID,replay)]
