"""Synthetic byte/provenance controls only; no ERP or external requests."""
from contextlib import chdir
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import copy
import importlib.util
import io
import json
import unittest
import zipfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('current_terminal_collector_control', HERE / 'retain.py')
r = importlib.util.module_from_spec(spec);spec.loader.exec_module(r)


class TerminalRetention(unittest.TestCase):
    def setUp(self):
        r.ARTIFACT = r.SIZE = r.DIGEST = None
        self.run = dict(id=r.RUN, head_sha=r.HEAD, head_branch=r.BRANCH, run_attempt=1,
                        status='completed', conclusion='success')
        self.job = dict(id=r.JOB, run_id=r.RUN, head_sha=r.HEAD, run_attempt=1,
                        status='completed', conclusion='success')
        self.meta = dict(id=123, name=r.ARTIFACT_NAME, size_in_bytes=300, digest='sha256:' + 'a' * 64,
                         workflow_run=dict(id=r.RUN, head_sha=r.HEAD, head_branch=r.BRANCH), expired=False)
        self.items = [self.meta]

    def metadata(self, route, target):
        if '/jobs?' in route:
            return dict(total_count=1, jobs=[copy.deepcopy(self.job)])
        if '/artifacts?' in route:
            page = int(route.split('page=')[-1]);return dict(total_count=len(self.items), artifacts=copy.deepcopy(self.items[(page-1)*100:page*100]))
        if '/actions/artifacts/' in route:
            return copy.deepcopy(self.meta)
        return copy.deepcopy(self.run)

    def test_active_foreign_or_other_attempt_source_refuses_before_any_archive_access(self):
        for change in (dict(status='in_progress'), dict(head_sha='0'*40), dict(run_attempt=2), dict(head_branch='main')):
            self.run.update(change)
            with patch.object(r, 'metadata', side_effect=self.metadata) as getter:
                with self.assertRaisesRegex(ValueError, 'EXACT_TERMINAL_CURRENT_OWNING_RUN'):
                    r.original_context(Path('.'), Path('.'))
                self.assertEqual(getter.call_count, 1)
            self.setUp()

    def test_both_terminal_outcomes_require_complete_pagination_and_exact_owner(self):
        for conclusion in ('success', 'failure'):
            self.run['conclusion'] = self.job['conclusion'] = conclusion
            self.items = [dict(id=i, name='control-nonfinal-' + str(i)) for i in range(200, 300)] + [self.meta]
            with patch.object(r, 'metadata', side_effect=self.metadata):
                r.original_context(Path('.'), Path('.'))
            self.assertEqual((r.ARTIFACT, r.SIZE, r.DIGEST), (123, 300, 'a' * 64))

    def test_duplicate_final_name_and_changed_details_are_refused(self):
        self.items = [self.meta, dict(self.meta, id=124)]
        with patch.object(r, 'metadata', side_effect=self.metadata):
            with self.assertRaisesRegex(ValueError, 'ONE_CANONICAL_FINAL'):
                r.original_context(Path('.'), Path('.'))
        self.items = [dict(self.meta, digest='sha256:' + 'b' * 64)]
        with patch.object(r, 'metadata', side_effect=self.metadata):
            with self.assertRaisesRegex(ValueError, 'EXACT_CANONICAL_SOURCE_ARTIFACT'):
                r.original_context(Path('.'), Path('.'))

    def test_second_phase_cannot_change_first_canonical_identity(self):
        with patch.object(r, 'metadata', side_effect=self.metadata):
            r.original_context(Path('.'), Path('.'))
            self.meta['id'] = 456
            with self.assertRaisesRegex(ValueError, 'FIRST_CANONICAL_SOURCE_IDENTITY'):
                r.original_context(Path('.'), Path('.'))

    def test_dirty_or_unbounded_source_is_refused_before_part_publication(self):
        with TemporaryDirectory() as folder:
            root = Path(folder);source = root / 'source';source.write_bytes(b'actual-control-source')
            for width, source_pin in ((True, r.pin(source)), (1, r.pin(source)), (64, dict(bytes=source.stat().st_size, sha256='0'*64))):
                with self.assertRaises(ValueError):r.split(source, root, width, source_pin)
            self.assertEqual(list(root.glob('part-*')), [])

    def archive_fixture(self, corrupt=False):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w', zipfile.ZIP_STORED) as archive:
            archive.writestr('CP7_AFUI_GOOD_NONPAYABLE_FULL15.json', '{"explicit_control":1}')
            archive.writestr('AFUI_RUNTIME_SUPERVISION.json', '{"fixture_supervisor":1}')
        raw = stream.getvalue()
        if corrupt:raw = raw.replace(b'{"explicit_control":1}', b'{"explicit_control":2}')
        self.meta.update(size_in_bytes=len(raw), digest='sha256:' + sha256(raw).hexdigest())
        return raw

    def test_complete_archive_crc_all_parts_and_zero_credit(self):
        raw = self.archive_fixture()
        with TemporaryDirectory() as folder, chdir(folder), patch.object(r, 'metadata', side_effect=self.metadata), patch.object(r, 'api', return_value=io.BytesIO(raw)), patch.object(r, 'PART_BYTES', 64):
            r.archive();root = Path(r.DIRECTORY)
            manifest = json.loads((root / 'diagnostics/INTAKE_MANIFEST.json').read_bytes())
            joined = b''.join((root / f"part-{p['number']:03d}" / p['name']).read_bytes() for p in manifest['parts'])
            self.assertEqual(joined, raw);self.assertTrue(manifest['full_archive_CRC_verified'])
            self.assertEqual(manifest['financial_acceptance_credit'], 0)
            self.assertEqual(manifest['ERP_commands_executed'], 0)
            for part in manifest['parts']:
                self.assertLessEqual(part['bytes'], 64)
                self.assertEqual(json.loads((root / f"part-{part['number']:03d}/INTAKE_MANIFEST.json").read_bytes()), manifest)

    def test_outer_api_pin_cannot_hide_inner_zip_crc_corruption(self):
        raw = self.archive_fixture(corrupt=True)
        with TemporaryDirectory() as folder, chdir(folder), patch.object(r, 'metadata', side_effect=self.metadata), patch.object(r, 'api', return_value=io.BytesIO(raw)), patch.object(r, 'PART_BYTES', 64):
            with self.assertRaises((ValueError, zipfile.BadZipFile)):r.archive()
            self.assertEqual(list(Path(r.DIRECTORY).glob('part-*')), [])

    def test_prepared_workflow_cannot_trigger_here_or_request_database_authority(self):
        import ast
        import yaml
        root = HERE.parents[1]
        value = yaml.safe_load((root / '.github/workflows/afui215-evidence-intake-20261105.yml').read_bytes())
        self.assertEqual(set(value['on']), {'push'})
        self.assertEqual(value['on']['push']['branches'], ['astra-a/afui215-evidence-intake-20261105'])
        self.assertNotIn('astra-a/afui215-evidence-intake-prepared-20261105', value['on']['push']['branches'])
        self.assertEqual(value['permissions'], dict(contents='read', actions='read'))
        self.assertEqual(set(value['jobs']), {'retain'})
        job = value['jobs']['retain'];self.assertEqual(job['timeout-minutes'], 25)
        self.assertEqual(len(job['steps']), 20)
        for step in job['steps']:
            if 'uses' in step:self.assertIn(step['uses'], ('actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683', 'actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02'))
        tree = ast.parse((HERE / 'retain.py').read_bytes())
        imports = {n.names[0].name for n in ast.walk(tree) if isinstance(n, ast.Import)}
        self.assertFalse(imports & {'psycopg', 'psycopg2', 'subprocess', 'supabase'})


if __name__ == '__main__':
    unittest.main()
