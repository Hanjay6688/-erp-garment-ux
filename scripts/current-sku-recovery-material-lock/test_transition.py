from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
import transition as t
import runtime_source


class MaterialLockTransition(unittest.TestCase):
    def test_one_exact_hunk_and_round_trip(self):
        before=t.original(t.ROOT,t.SQL);after=(t.ROOT/t.SQL).read_bytes()
        t.exact_transition(before,after)
        self.assertEqual(after.replace(t.INSERT.encode(),b'',1),before)
        self.assertEqual(after.count(t.INSERT.encode()),1)

    def test_missing_row_lock_blanket_and_wrong_lot_refuse(self):
        before=t.original(t.ROOT,t.SQL);good=t.patched(before)
        for bad in [before,good.replace(b'where material.id=(select lot.material_id from erp.bc_return_lots_v1 lot where lot.id=p_lot)',b'where true'),
                    good.replace(b'lot.id=p_lot',b'lot.material_id=p_lot'),good.replace(b'order by material.id for update nowait;',b'order by material.id for update;')]:
            with self.subTest(bad=bad[-40:]):
                with self.assertRaisesRegex(ValueError,'ONLY_ONE_EXACT_SQL_HUNK'):
                    t.exact_transition(before,bad)

    def test_before_effects_and_fresh_authority_unchanged(self):
        current=(t.ROOT/t.SQL).read_text();pos=current.index(t.INSERT)
        self.assertLess(current.index("'FG_HPP_SALES_V2620C'"),pos)
        self.assertLess(current.index('in share row exclusive mode nowait;'),pos)
        self.assertLess(pos,current.index("perform cp7_sku_conversion.recovery_auth_v1",pos))
        self.assertLess(pos,current.index('perform erp.resolve_accounting_transaction_date',pos))
        self.assertNotIn('MOVING_AVERAGE',t.INSERT.split('perform 1',1)[1])
        raw=t.original(t.ROOT,'scripts/cp7_sku_pair_conversion/recovery_before/erp.bc_value_custody_v1.sql').decode()
        self.assertLess(raw.index('erp.bc_lock_lot_v1'),raw.index("if v_policy->>'unit_value_cap'='MOVING_AVERAGE' then"))
        self.assertLess(raw.index('for update;'),raw.index('erp.bc_new_document_v1'))
        self.assertEqual((t.ROOT/'scripts/cp7_sku_pair_conversion/recovery_before/erp.bc_value_custody_v1.sql').read_text(),raw)
        policy=t.original(t.ROOT,'scripts/cp6_bc_objects_policy.sql').decode()
        self.assertIn("not in('MOVING_AVERAGE','NONE')",policy)

    def test_unexpected_own_source_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);own=root/t.PREFIX;own.mkdir(parents=True)
            p=own/'known.py';p.write_text('known\n');(own/'SOURCE.json').write_text('{}')
            m={'files':{t.PREFIX+'known.py':t.pin(p.read_bytes())}}
            t.own_files(root,m)
            (own/'rogue.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'UNDECLARED_OWN_SOURCE'):
                t.own_files(root,m)

    def test_tamper_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);own=root/t.PREFIX;own.mkdir(parents=True)
            p=own/'known.py';p.write_text('known\n');(own/'SOURCE.json').write_text('{}')
            m={'files':{t.PREFIX+'known.py':t.pin(p.read_bytes())}}
            p.write_text('tampered\n')
            with self.assertRaisesRegex(ValueError,'OWN_SOURCE_CHANGED'):t.own_files(root,m)
            target=root/'target';target.write_text('known\n');p.unlink();p.symlink_to(target)
            with self.assertRaisesRegex(ValueError,'REGULAR_SOURCE_REQUIRED'):t.own_files(root,m)

    def test_public_parent_all43_and_old_callbacks(self):
        proof=t.admitted()
        self.assertEqual(proof['public_parent'],t.BASE)
        self.assertEqual(proof['old_source_pins'],43)
        self.assertEqual(proof['old23_callbacks_changed'],0)
        self.assertEqual(proof['Native_financial'],0)
        self.assertFalse(proof['complete_untracked_qualification'])

    def test_actual_policy_catalog_permits_none_without_new_capture(self):
        proof=json.loads((t.HERE/'evidence/POLICY_CATALOG_AUTHORITY.json').read_bytes())
        row=proof['full_captured_catalog_row'];raw=row[0].encode()
        self.assertEqual(len(raw),7657)
        self.assertEqual(sha256(raw).hexdigest(),'834f2b9cd80d9527dc45397c848d6ea6c1389c130f7539172fea71746f95c6c9')
        self.assertIn("not in('MOVING_AVERAGE','NONE')",row[0])
        self.assertEqual(row[1],'postgres')
        self.assertEqual(row[-1],[['postgres','postgres','EXECUTE',False]])
        self.assertTrue(proof['source']['exact_before_after'])
        source=json.loads((t.HERE/'SOURCE.json').read_bytes())
        self.assertEqual(source['unchanged_captures'],8)

    def test_local_controls_and_actual_current_sources_are_honest(self):
        local=json.loads((t.HERE/'evidence/LOCAL_MATERIAL_POLICY.json').read_bytes())
        self.assertEqual(local['status'],'PASS')
        self.assertEqual(local['count'],49)
        self.assertEqual(local['retained_controls'],45)
        self.assertEqual(local['additional_NONE_controls'],4)
        self.assertEqual(local['sources']['recovery'],sha256((t.ROOT/t.SQL).read_bytes()).hexdigest())
        self.assertEqual(local['actual_Native_financial'],0)
        self.assertFalse(local['real_NOWAIT_contention_proven'])
        none=[c for c in local['cases'] if c['id'].startswith('NONE_')]
        self.assertEqual(len(none),4)
        for c in none:
            self.assertEqual(c['status'],'PASS')
            if 'before_sha256' in c:self.assertEqual(c['before_sha256'],c['after_sha256'])
        runtime=json.loads((t.HERE/'evidence/UNPROJECTED_CURRENT_RUNTIME.json').read_bytes())
        self.assertEqual(runtime['status'],'PASS')
        self.assertEqual(runtime['forbidden_DB_network_attempts'],[])
        self.assertFalse(runtime['projected_sources'])
        self.assertFalse(runtime['ROOT_reassigned'])
        self.assertEqual(len(runtime['sku_business_leaves']),10)
        self.assertEqual(runtime['sku_business_leaves'][t.SQL],sha256((t.ROOT/t.SQL).read_bytes()).hexdigest())
        self.assertEqual([c.get('api') for c in runtime['DB_entrypoint_self_controls'][:3]],
                         ['psycopg.connect','psycopg.Connection.connect','psycopg.AsyncConnection.connect'])
        self.assertEqual(runtime['DB_entrypoint_self_controls'][-1],{'original_connect_descriptors_restored':True})

    def test_database_guard_refuses_and_restores_after_error(self):
        import psycopg
        targets=[psycopg,psycopg.Connection,psycopg.AsyncConnection]
        originals=[vars(target)['connect'] for target in targets];attempts=[];controls=[]
        with self.assertRaisesRegex(ValueError,'DECLARED_LATE_SOURCE_CONTROL'):
            with runtime_source.database_guard(attempts,controls):
                for target in targets:
                    with self.assertRaisesRegex(RuntimeError,'DATABASE_FORBIDDEN'):
                        target.connect()
                raise ValueError('DECLARED_LATE_SOURCE_CONTROL')
        self.assertEqual(attempts,['psycopg.connect','psycopg.Connection.connect','psycopg.AsyncConnection.connect'])
        for target,original in zip(targets,originals):self.assertIs(vars(target)['connect'],original)
        self.assertEqual(controls[-1],{'original_connect_descriptors_restored':True})


if __name__=='__main__':unittest.main()
