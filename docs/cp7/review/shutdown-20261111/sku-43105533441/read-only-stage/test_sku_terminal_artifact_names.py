"""Verify the read-only SKU reader's terminal archive names and case credit."""
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import json
import re
import sys
import unittest

import yaml


STAGE = Path(sys.argv.pop(1)).resolve()
SKU_REPO = Path(sys.argv.pop(1)).resolve()
sys.path.insert(0, str(STAGE / 'scripts/afui-evidence-intake-20261105/sku-intake/global/reviewed-sku-shutdown-successor'))
import reviewed_sku_source as source
import verify_sku_read_only as transport
import verify_terminal_sku as terminal


class TerminalArtifactNames(unittest.TestCase):
    def fixture(self, conclusion='failure'):
        run = dict(id=914, head_sha=source.CANDIDATE, head_branch=terminal.BRANCH, path=terminal.WORKFLOW,
                   run_attempt=1, status='completed', conclusion=conclusion, event='push')
        job = dict(id=213, run_id=run['id'], head_sha=source.CANDIDATE, run_attempt=1, status='completed',
                   conclusion=conclusion, name=transport.JOB_NAME,
                   steps=[dict(name='Remove disposable database', conclusion='success')])
        reviewed = dict(run_id=run['id'], job_id=job['id'], head=source.CANDIDATE)
        artifact = dict(id=522, name=terminal.terminal_archive_name(run), expired=False,
                        digest='sha256:'+'a'*64, size_in_bytes=10,
                        workflow_run=dict(id=run['id'], head_sha=source.CANDIDATE, head_branch=terminal.BRANCH))
        return run, job, reviewed, artifact

    def test_reader_names_match_the_actual_pinned_workflow(self):
        path = SKU_REPO / terminal.WORKFLOW
        workflow = yaml.safe_load(path.read_bytes())
        value = workflow['jobs']['p21']['steps'][-1]['with']['name']
        success, failure = re.findall(r"format\('([^']+)',", value)
        for outcome, template in [('success', success), ('failure', failure)]:
            run, *_ = self.fixture(outcome)
            name = template.format(1) if outcome == 'success' else template.format(run['id'], 1)
            self.assertEqual(terminal.terminal_archive_name(run), name)

    def test_same_run_failure_zip_retains_first_error_and_no_case_credit(self):
        run, job, reviewed, artifact = self.fixture()
        with TemporaryDirectory() as temp:
            file = Path(temp) / 'example-only.zip'
            fixture = dict(qualification_commit=source.CANDIDATE, error='SYNTHETIC_FAILURE_FOR_READER_CONTROL')
            with ZipFile(file, 'x') as z:
                z.writestr(terminal.MAIN, json.dumps(fixture))
            raw = file.read_bytes()
            artifact.update(digest='sha256:'+sha256(raw).hexdigest(), size_in_bytes=len(raw))
            binding = transport.bind(run, job, dict(artifacts=[artifact]), reviewed)
            self.assertEqual(binding['conclusion'], 'failure')
            receipt, root, catalogue = terminal.verify(file, artifact, run, job, Path(temp), b'', reviewed)
            self.assertTrue(receipt['all_member_crc_verified'])
            self.assertEqual(receipt['first_reported_error'], fixture['error'])
            self.assertEqual(receipt['actual_case_credit'], 0)
            self.assertIsNone(root)
            self.assertIsNone(catalogue)
            promoted = dict(run, conclusion='success')
            with self.assertRaisesRegex(ValueError, 'UNIQUE_TERMINAL_ORIGINAL'):
                transport.bind(promoted, dict(job, conclusion='success'), dict(artifacts=[artifact]), reviewed)
            with self.assertRaisesRegex(ValueError, 'NATIVE25_BROWSER2_ALL_FIVE_AND_CATALOGUE_REQUIRED'):
                terminal.verify(file, dict(artifact, name=terminal.CANONICAL), promoted,
                                dict(job, conclusion='success'), Path(temp), b'', reviewed)

    def test_mismatched_attempt_or_another_run_archive_is_refused(self):
        run, job, reviewed, artifact = self.fixture()
        for altered in (dict(run, status='in_progress'), dict(run, run_attempt=2)):
            with self.assertRaisesRegex(ValueError, 'TERMINAL_ARCHIVE_IDENTITY_REQUIRED'):
                transport.bind(altered, job, dict(artifacts=[artifact]), reviewed)
        with self.assertRaisesRegex(ValueError, 'EXACT_TERMINAL_ORIGINAL'):
            binding = transport.bind(run, job, dict(artifacts=[artifact]), reviewed)
            transport.check_metadata(binding, reviewed, run, job, dict(artifact, name='cp7-sku-failure-913-1'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
