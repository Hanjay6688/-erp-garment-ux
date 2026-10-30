"""Labelled file/metadata doubles only; no Native execution or synthetic PASS."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest
import accepted_originals as inputs
import midnight_common as common
import midnight_gate as gate
import parent_binding as binding


class AcceptedInputControls(unittest.TestCase):
    def test_root_certificate_and_six_exact_raw_pins(self):
        cfg = common.document((common.HERE / 'CONFIG.json').read_bytes())
        self.assertEqual(inputs.configuration(), binding.original_descriptors())
        self.assertEqual(cfg['accepted_parent14']['head'], binding.HEAD)
        self.assertEqual(len(binding.source()[1]), 475)
        self.assertEqual(inputs.ARCHIVE['expected_members'], 119)

    def test_NULL_remains_first_and_no_original_is_opened(self):
        cfg = deepcopy(common.document((common.HERE / 'CONFIG.json').read_bytes()))
        cfg['accepted_parent14'] = None
        with patch.object(binding, 'root_receipt', side_effect=AssertionError('ORIGINAL_BEFORE_NULL')):
            with self.assertRaisesRegex(ValueError, gate.CLOSED):
                inputs.configuration(cfg=cfg)

    def test_foreign_raw_pin_cannot_bind_even_matching_group_metadata(self):
        cfg = deepcopy(common.document((common.HERE / 'CONFIG.json').read_bytes()))
        cfg['accepted_parent14']['originals']['strict11']['raw']['sha256'] = 'f' * 64
        with self.assertRaisesRegex(ValueError, 'EXACT_ROOT_QUALIFIED14_SIX_RAW'):
            gate.selected(cfg)

    def test_foreign_archive_identity_and_bool_size_refuse(self):
        for field, wrong in (('artifact_id', 12947563875), ('bytes', True), ('sha256', 'f' * 64)):
            cfg = deepcopy(common.document((common.HERE / 'CONFIG.json').read_bytes()))
            cfg['accepted_parent14_archive'][field] = wrong
            with self.assertRaisesRegex(ValueError, 'EXACT_ROOT_QUALIFIED14_ARCHIVE'):
                inputs.configuration(cfg=cfg)

    def test_root_qualified_originals_remain_runtime_inputs_not_source_members(self):
        manifest = common.document((common.HERE / 'SOURCE.json').read_bytes())
        self.assertTrue(all(name not in manifest['files']
            for name in (item['path'] for item in binding.original_descriptors().values())))
        self.assertEqual(manifest['accepted_parent14'],
            common.document((common.HERE / 'CONFIG.json').read_bytes())['accepted_parent14'])

    def test_absent_vs_partial_stage_and_regular_full_stage_on_declared_file_doubles(self):
        raw = b'file-double-not-an-Original\n'
        expected = {str(i): dict(path='stage/' + str(i), raw=common.pin(raw)) for i in range(6)}
        with TemporaryDirectory() as name, patch.object(inputs, 'configuration', return_value=expected):
            root = Path(name)
            self.assertEqual(inputs.present_pins(root), {})
            with self.assertRaisesRegex(ValueError, 'EXACT_ACCEPTED14_SIX_RAW_STAGE_REQUIRED'):
                inputs.present_pins(root, required=True)
            (root / 'stage').mkdir(); (root / 'stage/0').write_bytes(raw)
            with self.assertRaisesRegex(ValueError, 'PARTIAL_ACCEPTED14'):
                inputs.present_pins(root)
            for i in range(1, 6): (root / 'stage' / str(i)).write_bytes(raw)
            self.assertEqual(len(inputs.present_pins(root, required=True)), 6)
            (root / 'stage/0').write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError, 'EXACT_BYTES_REQUIRED'):
                inputs.present_pins(root)

    def test_stage_leaf_and_ancestor_links_fail_on_declared_file_doubles(self):
        raw = b'file-double-not-an-Original\n'
        expected = {str(i): dict(path='stage/' + str(i), raw=common.pin(raw)) for i in range(6)}
        with TemporaryDirectory() as name, patch.object(inputs, 'configuration', return_value=expected):
            root = Path(name); held = root / 'held'; held.mkdir()
            (held / '0').write_bytes(raw)
            (root / 'stage').symlink_to(held, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'SOURCE_SYMLINK:stage/0'):
                inputs.present_pins(root)
            (root / 'stage').unlink(); (root / 'stage').mkdir()
            (root / 'stage/0').symlink_to(held / '0')
            with self.assertRaisesRegex(ValueError, 'SOURCE_SYMLINK:stage/0'):
                inputs.present_pins(root)

    def test_bad_archive_cannot_write_any_accepted_input(self):
        with TemporaryDirectory() as name:
            archive = Path(name) / 'bad.zip'; archive.write_bytes(b'not-qualified-archive')
            with self.assertRaisesRegex(ValueError, 'EXACT_BYTES_REQUIRED'):
                inputs.verify_archive(archive)

    def test_archive_leaf_and_ancestor_links_refuse(self):
        with TemporaryDirectory() as name:
            root = Path(name); (root / 'held').mkdir(); (root / 'held/file').write_bytes(b'bad')
            (root / 'linked').symlink_to(root / 'held', target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'ARCHIVE_SYMLINK'):
                inputs.external_regular(root / 'linked/file')
            (root / 'leaf').symlink_to(root / 'held/file')
            with self.assertRaisesRegex(ValueError, 'ARCHIVE_SYMLINK'):
                inputs.external_regular(root / 'leaf')


if __name__ == '__main__':
    unittest.main()
