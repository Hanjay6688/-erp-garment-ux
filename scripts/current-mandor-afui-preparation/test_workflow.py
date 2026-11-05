"""Current workflow/retention controls; no accepted Root or financial run."""
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import importlib.util
import json
import os
import subprocess
import unittest

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location('current_mandor82_control_' + name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


class CurrentWorkflow(unittest.TestCase):
    def test_real_shell_runs_Afui_static_check_inside_frozen_parent_only(self):
        import yaml
        text, _ = load('workflow').derive()
        steps = yaml.safe_load(text)['jobs']['p21']['steps']
        step = next(row for row in steps if row.get('name') ==
                    'Verify complete current Mandor source, transport and owning workflow before database')
        with TemporaryDirectory() as directory:
            root = Path(directory)
            auditor, frozen, binaries = root / 'auditor', root / 'qualified-afui-parent', root / 'bin'
            for path in (auditor, frozen, binaries):
                path.mkdir()
            log = root / 'command-context.tsv'
            stub = '#!/bin/sh\nprintf \'%s\\t%s\\n\' "$PWD" "$*" >> "$CP7_PREFLIGHT_CWD_LOG"\n'
            for command in ('python', 'node'):
                executable = binaries / command
                executable.write_text(stub)
                executable.chmod(0o700)
            env = dict(os.environ, PATH=str(binaries) + os.pathsep + os.environ['PATH'],
                       CP7_PREFLIGHT_CWD_LOG=str(log))
            result = subprocess.run(['bash', '-c', step['run']], cwd=auditor,
                                    env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            commands = [line.split('\t', 1) for line in log.read_text().splitlines()]
            afui = [row for row in commands if 'qualification.py --check-static' in row[1]]
            self.assertEqual(len(afui), 1)
            self.assertEqual(afui[0][0], str(frozen))
            self.assertEqual(len(commands), 5)
            self.assertTrue(all(cwd == str(auditor) for cwd, args in commands
                                if 'qualification.py --check-static' not in args))

    def test_current80_chain_has69_unchanged_steps_and84_complete_current_steps(self):
        workflow = load('workflow');text, proof = workflow.derive()
        self.assertEqual((proof['original_steps'], proof['unchanged_steps'], proof['owning_routes'], proof['total_steps']), (80, 69, 11, 84))
        self.assertEqual(text.encode(), workflow.TEMPLATE.read_bytes())
        self.assertEqual(workflow.check(), proof)
        self.assertIn('current-mandor-afui-preparation/', text)
        self.assertIn('MANDOR_NATIVE_JOB_START_MONOTONIC', text)
        self.assertNotIn('AFUI_JOB_START_MONOTONIC', text)
        self.assertFalse(workflow.ACTIVE.exists())

    def test_both_complete_original_sources_refuse_mutation_and_transport_is_exact(self):
        workflow, transport = load('workflow'), load('transport')
        for subject in (workflow, transport):
            with self.subTest(subject=subject.__name__), self.assertRaisesRegex(ValueError, 'EXACT_'):
                subject.derive(subject.ORIGINAL.read_bytes() + b'\n')
        text, proof = transport.derive()
        self.assertTrue(proof['entire_original_recovered'])
        self.assertEqual(proof['reversible_routes'], 16)
        self.assertEqual(text.encode(), (HERE / 'durable_action.mjs').read_bytes())

    def test_returned_native_group_publishes_complete_bytes_and_preserves_first_conflict(self):
        output = load('output_binding');complete = output.frozen_source('complete_original_io.py')
        with TemporaryDirectory() as directory:
            root = Path(directory);source = root / 'writer_original.json'
            raw = (b'{"explicit_protocol_model":true,"whole":"' + b'x' * 300000 + b'"}\n');source.write_bytes(raw)
            target = root / 'cp6-proof/t3/CP7_FG_MANDOR_NATIVE9_STRICT.json';target.parent.mkdir(parents=True)
            with patch.object(output, 'ROOT', root), patch.object(output, 'frozen_source', return_value=complete):
                receipt = output.copy_exact(source, target)
                published = target.parent / 'MANDOR_CASE_STDOUT' / target.name
                self.assertEqual(published.read_bytes(), raw)
                self.assertEqual(receipt['sha256'], sha256(raw).hexdigest())
                source.write_bytes(b'changed Original must not replace the first')
                with self.assertRaisesRegex(ValueError, 'FIRST_STRICT_ORIGINAL_CHANGED'):
                    output.copy_exact(source, target)
                self.assertEqual(published.read_bytes(), raw)

    def test_complete_receipts_stream_originals_and_refuse_changes_or_symlink(self):
        subject = load('receipts')
        with TemporaryDirectory() as directory:
            proof = Path(directory);raw = b'whole Original including binary\0' * 20000
            first = proof / 'MANDOR_HTTP2_ORIGINAL.json';first.write_bytes(raw)
            original_read = Path.read_bytes
            def bounded(path):
                if path == first:raise AssertionError('Complete Original was read as one byte buffer')
                return original_read(path)
            with patch.object(Path, 'read_bytes', bounded):
                value = subject.receipts(proof)
            self.assertEqual(value['originals'][first.name], dict(bytes=len(raw), sha256=sha256(raw).hexdigest()))
            self.assertEqual(value['actual_case_credit'], 0)
            before = (proof / 'MANDOR_CURRENT_COMPLETE_ORIGINAL_RECEIPTS.json').read_bytes()
            first.write_bytes(b'changed original')
            with self.assertRaisesRegex(ValueError, 'FIRST_ORIGINAL_RECEIPT_CHANGED'):
                subject.receipts(proof)
            self.assertEqual((proof / 'MANDOR_CURRENT_COMPLETE_ORIGINAL_RECEIPTS.json').read_bytes(), before)
            other = proof / 'MANDOR_BROWSER2_ORIGINAL.json';other.symlink_to(first)
            with self.assertRaisesRegex(ValueError, 'REGULAR_ORIGINAL'):
                subject.receipts(proof)


if __name__ == '__main__':unittest.main()
