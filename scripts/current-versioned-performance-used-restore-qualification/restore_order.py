"""Exact fixture order correction; all target freshness assertions stay unchanged."""
import ast

OLD_ORDER = """            held_target=target_fixture.prepare(cur,comparison['row']['query'],comparison['target'],report)
            held_history=history_fixture.prepare(cur,today,comparison['target'],f['products'][0],report)
            held_scoped_model=scoped_model_fixture.prepare(cur,held_history,report)"""
NEW_ORDER = """            held_history=history_fixture.prepare(cur,today,comparison['target'],f['products'][0],report)
            held_scoped_model=scoped_model_fixture.prepare(cur,held_history,report)
            held_target=target_fixture.prepare(cur,comparison['row']['query'],comparison['target'],report)
            target_before_backup={}
            target_fixture.assert_restored(cur,held_target,target_before_backup,'BEFORE_USED_BACKUP',source_changed=False)
            report['dated_target_prebackup_check']=target_before_backup['dated_target_full_restore_checks'][0]"""


def correct(text):
    assert text.count(OLD_ORDER) == 1, 'RESTORE_PREPARATION_ORDER_ANCHOR_CHANGED'
    return text.replace(OLD_ORDER, NEW_ORDER)


def verify(before, after):
    assert ast.dump(ast.parse(correct(before)), include_attributes=False) == ast.dump(ast.parse(after), include_attributes=False), 'RESTORE_ORDER_UNDECLARED_RUNNER_CHANGE'
    return dict(target_capture_after_all_scoped_evaluations=True,
                exact_existing_target_prebackup_assertions=True,
                freshness_oracle_unchanged=True,
                remaining_runner_AST_unchanged=True)
