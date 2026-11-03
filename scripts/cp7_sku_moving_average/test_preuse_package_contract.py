"""Actual inverse/caller code with modeled catalog and DDL collaborators.

Reproduce the retained bbdbc missing receipt field, without importing ERP or
rerunning an installation. These controls confer zero Native case credit.
"""
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import ast,subprocess,unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
FAILED='bbdbc9d5874128210d385e0f089105618eab4968'
PATH='scripts/cp7_sku_moving_average/composition.py'


def inverse(source,*,used=False,changed_after_catalog=False,changed_after_rows=False):
    node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)and n.name=='rollback_delta_preuse')
    before={'all22':'original'};preuse={'all_rows_and_sequences':'installed'};old_data={'all_rows_and_sequences':'original'}
    catalog=SimpleNamespace(_lock_tables=Mock(),_data=Mock(side_effect=[{'changed':True}if used else preuse,
        {'changed':True}if changed_after_rows else old_data]),
        _catalog_rows=Mock(return_value={'changed':True}if changed_after_catalog else before))
    locks=Mock();predecessor=SimpleNamespace(atomic=lambda cur:nullcontext(),
        predecessor=SimpleNamespace(predecessor=SimpleNamespace(_locks=locks)))
    parent=SimpleNamespace(verify=Mock(return_value={'exact_original_parent':True}))
    cur=Mock();reader=SimpleNamespace(revoke_schema=lambda c:c.execute('MODEL REVOKE READER SCHEMA'))
    namespace=dict(runtime=lambda:(None,None,None,predecessor,catalog),verify=Mock(),parent=lambda:parent,
        USED_ERROR='SKU_MOVAVG_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE',
        reader_handover=lambda c:nullcontext(),as_owner=lambda c,r:nullcontext(),
        reader_function_ddl=lambda c,s:nullcontext(),reader_access=reader,
        READER_OWNERS={'private.reader()':'existing_owner'},FUNCTIONS=('private.new_function()',),TABLES=('private.new_table',))
    exec(compile(ast.Module(body=[node],type_ignores=[]),'actual_inverse_with_modeled_collaborators','exec'),namespace)
    state=dict(preuse_data_and_sequences=preuse,before_data=old_data,before=before,predecessor={'actual':'parent'},
        originals={'private.reader()':'ORIGINAL READER DDL','erp.existing()':'ORIGINAL NATIVE DDL'})
    return lambda:namespace['rollback_delta_preuse'](cur,state),cur,catalog,parent,locks


def package_assertion(receipt):
    # Execute the existing caller's real assertion, not a looser test oracle.
    raw=(ROOT/'scripts/current-vendor-receivable-qualification/probe.py').read_bytes()
    candidates=[n for n in ast.walk(ast.parse(raw))if isinstance(n,ast.Assert)
        and 'focused_preuse_removal' in ast.unparse(n)]
    assert len(candidates)==1
    exec(compile(ast.Module(body=candidates,type_ignores=[]),'unchanged_owning_package_assertion','exec'),
        {'report':{'focused_preuse_removal':receipt}})


class PreusePackageContract(unittest.TestCase):
    def test_original_failure_is_missing_receipt_after_successful_inverse(self):
        raw=subprocess.check_output(['git','-C',str(ROOT),'show',FAILED+':'+PATH])
        run,cur,_,parent,_=inverse(raw);receipt=run()
        self.assertGreater(cur.execute.call_count,0);parent.verify.assert_called_once()
        with self.assertRaisesRegex(KeyError,'used_guard_before_DDL'):package_assertion(receipt)

    def test_success_receipt_satisfies_the_unchanged_package_consumer(self):
        run,cur,catalog,parent,locks=inverse((HERE/'composition.py').read_bytes());receipt=run()
        package_assertion(receipt)
        self.assertIs(receipt['used_guard_before_DDL'],True)
        self.assertEqual(receipt['parent_verified'],{'exact_original_parent':True})
        self.assertEqual(catalog._data.call_count,2);locks.assert_called_once_with(cur)
        catalog._lock_tables.assert_called_once_with(cur);parent.verify.assert_called_once()

    def test_used_state_refuses_before_any_DDL_and_cannot_emit_success(self):
        run,cur,_,parent,_=inverse((HERE/'composition.py').read_bytes(),used=True)
        with self.assertRaisesRegex(ValueError,'^SKU_MOVAVG_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE$'):run()
        cur.execute.assert_not_called();parent.verify.assert_not_called()

    def test_inexact_catalogue_restoration_cannot_emit_success(self):
        run,_,_,parent,_=inverse((HERE/'composition.py').read_bytes(),changed_after_catalog=True)
        with self.assertRaisesRegex(ValueError,'^SKU_MOVAVG_PREDECESSOR_NOT_RESTORED$'):run()
        parent.verify.assert_not_called()

    def test_inexact_rows_or_sequences_cannot_emit_success(self):
        run,_,_,parent,_=inverse((HERE/'composition.py').read_bytes(),changed_after_rows=True)
        with self.assertRaisesRegex(ValueError,'^SKU_MOVAVG_PREDECESSOR_NOT_RESTORED$'):run()
        parent.verify.assert_not_called()


if __name__=='__main__':unittest.main()
