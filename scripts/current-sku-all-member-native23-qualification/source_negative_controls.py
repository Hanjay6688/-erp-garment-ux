"""Local complete source-gate negatives; no runtime, database or network imports.

Run only after the candidate is committed and the real main72 output exists.
Every temporary mutation is an untracked qualification input or output; source
files are never edited. The original client report is restored byte exactly.
"""
from hashlib import sha256
from pathlib import Path
import importlib.util
import json
import os
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def run():
    spec = importlib.util.spec_from_file_location('sku23_complete_source_negative', HERE / 'closure.py')
    closure = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(closure)
    before = closure.source_only()
    results = {}
    controls = (
        ('unknown_source', HERE / 'UNDECLARED_SOURCE_NEGATIVE.py', b'raise RuntimeError("NEVER EXECUTED")\n'),
        ('unknown_output_JSON', ROOT / 'cp6-proof/t3/UNDECLARED_OUTPUT_NEGATIVE.json', b'{"status":"PASS"}\n'),
    )
    for label, path, raw in controls:
        assert not path.exists() and not path.is_symlink(), 'SKU23_NEGATIVE_CONTROL_PATH_ALREADY_PRESENT'
        try:
            path.write_bytes(raw)
            try:
                closure.source_only()
            except AssertionError as error:
                assert str(error) == 'SKU23_UNDECLARED_UNTRACKED_SOURCE', str(error)
                results[label] = str(error)
            else:
                raise AssertionError('SKU23_UNDECLARED_SOURCE_WAS_ADMITTED')
        finally:
            path.unlink()
    report = ROOT / 'cp6-proof/t3/SKU_TARGETED_CLIENT.json'
    assert report.is_file() and not report.is_symlink()
    original = report.read_bytes()
    with tempfile.TemporaryDirectory() as temp:
        target = Path(temp) / 'client-report.json'
        target.write_bytes(original)
        try:
            report.unlink()
            report.symlink_to(target)
            assert report.is_symlink() and os.readlink(report) == str(target), 'SKU23_SYMLINK_CONTROL_NOT_INSTALLED'
            try:
                closure.source_only()
            except AssertionError as error:
                assert str(error).startswith('GENERATED_OUTPUT_SYMLINK:'), str(error)
                results['known_output_symlink'] = str(error)
            else:
                assert report.is_symlink(), 'SKU23_SYMLINK_CONTROL_REPLACED_DURING_SOURCE_CHECK'
                raise AssertionError('SKU23_GENERATED_SYMLINK_WAS_ADMITTED')
        finally:
            restored = report.with_name('SKU_TARGETED_CLIENT.restore.tmp')
            assert not restored.exists() and not restored.is_symlink()
            restored.write_bytes(original)
            os.replace(restored, report)
    retained = ROOT / 'cp6-proof/t3/RETAINED_SKU21C'
    assert retained.is_dir() and not retained.is_symlink()
    originals = {p.name: p.read_bytes() for p in retained.iterdir()}
    assert len(originals) == 4
    with tempfile.TemporaryDirectory() as temp:
        saved = Path(temp) / 'exact-retained21-output-directory'
        retained.rename(saved)
        try:
            retained.symlink_to(saved, target_is_directory=True)
            assert retained.is_symlink() and os.readlink(retained) == str(saved)
            try:
                closure.source_only()
            except AssertionError as error:
                # Git may report the directory link itself instead of following
                # it to the four known leaves. Either complete caller refusal
                # must precede any runtime or Original admission.
                assert str(error) == 'SKU23_UNDECLARED_UNTRACKED_SOURCE' or str(error).startswith('GENERATED_OUTPUT_SYMLINK:'), str(error)
                results['known_output_symlink_ancestor'] = str(error)
            else:
                assert retained.is_symlink(), 'SKU23_SYMLINK_ANCESTOR_CONTROL_REPLACED_DURING_CHECK'
                raise AssertionError('SKU23_GENERATED_SYMLINK_ANCESTOR_WAS_ADMITTED')
        finally:
            retained.unlink()
            saved.rename(retained)
    assert {p.name: p.read_bytes() for p in retained.iterdir()} == originals
    after = closure.source_only()
    assert before == after and report.read_bytes() == original
    return dict(status='PASS', complete_real_source_gate_controls=results,
                source_and_output_restored_byte_exact=True,
                source_status=after['status'],
                client_report_sha256=sha256(original).hexdigest(),
                actual_Native_credit=0, actual_DB_calls=0, actual_network_calls=0)


if __name__ == '__main__':
    print(json.dumps(run(), sort_keys=True))
