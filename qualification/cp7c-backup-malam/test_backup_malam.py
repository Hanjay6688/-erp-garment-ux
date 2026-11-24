"""Nightly backup worker tests. All archives and remote objects are local fixtures."""

from datetime import date, timedelta
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import backup_malam as worker


HERE = Path(__file__).resolve().parent
PROFILE = HERE.parent / "cp7c-backup-sintetis" / "box-250mb.conf"
DAY = date(2026, 11, 24)
FOLDER = "Gladi-Mesin-CP7C"
REMOTE = "boxbackup:" + FOLDER


class NightlyTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        base = Path(self.work.name)
        self.state = base / "state"
        self.archive = base / "sample.cp7"
        self.ref = base / "source.json"
        self.store = base / "physical"
        self.folder = self.store / "ERP-Backup" / FOLDER
        self.folder.mkdir(parents=True)
        env = patch.dict(os.environ, RCLONE_CONFIG=str(PROFILE),
                         RCLONE_CONFIG_BOX_TYPE="alias", RCLONE_CONFIG_BOX_REMOTE=str(self.store))
        env.start()
        self.addCleanup(env.stop)
        self.archive.write_bytes(b"new synthetic export\n")
        self.reference(DAY)

    def reference(self, night):
        size, digest = worker.fingerprint(self.archive)
        self.ref.write_text(json.dumps({"captured_at": f"{night}T00:58:15+07:00",
                                        "ciphertext_bytes": size, "ciphertext_sha256": digest}))

    def backup(self, night=DAY):
        return worker.backup(REMOTE, self.archive, self.ref, night, self.state)

    def test_new_large_export_through_cli(self):
        with self.archive.open("wb") as src:
            src.write(b"synthetic export begin")
            src.seek(250_000_000)
            src.write(b"synthetic last part")
        self.reference(DAY)
        result = subprocess.run([sys.executable, str(HERE / "backup_malam.py"), "backup",
                                 "--archive", str(self.archive), "--reference", str(self.ref),
                                 "--state", str(self.state), "--night", str(DAY)],
                                capture_output=True, check=True)
        proof = json.loads(result.stdout)
        self.assertTrue(proof["uploaded"] and proof["new_receipt"])
        self.assertEqual(proof["verified"]["sha256"], worker.fingerprint(self.archive)[1])
        parts = sorted(p.stat().st_size for p in self.folder.glob("*.rclone_chunk.*"))
        self.assertEqual(parts, [19, 250_000_000])

    def test_retry_does_not_write_a_second_object_or_receipt(self):
        self.backup()
        before = {p.name: p.stat().st_mtime_ns for p in self.folder.iterdir()}
        proof = self.backup()
        self.assertFalse(proof["uploaded"] or proof["new_receipt"])
        self.assertEqual(before, {p.name: p.stat().st_mtime_ns for p in self.folder.iterdir()})

    def test_second_export_for_same_night_does_not_overwrite(self):
        self.backup()
        before = {p.name: p.read_bytes() for p in self.folder.iterdir()}
        self.archive.write_bytes(b"different export")
        self.reference(DAY)
        with self.assertRaisesRegex(ValueError, "arsip lain"):
            self.backup()
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.folder.iterdir()})

    def test_bad_source_stops_before_remote_write(self):
        self.archive.write_bytes(b"incorrect bytes")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            self.backup()
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_capture_date_uses_jakarta_and_rejects_stale_archive(self):
        data = json.loads(self.ref.read_text())
        data["captured_at"] = "2026-11-24T17:00:01Z"
        self.ref.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "Tanggal"):
            self.backup(DAY)
        proof = self.backup(DAY + timedelta(days=1))
        self.assertEqual(proof["verified"]["night_wib"], "2026-11-25")
        with self.assertRaisesRegex(ValueError, "Tanggal"):
            self.backup(DAY + timedelta(days=2))

    def test_interrupted_download_then_reverify_existing_upload(self):
        run = worker.rclone

        def interrupted(*args):
            if args[:1] == ("copyto",) and str(args[1]).startswith(REMOTE):
                raise subprocess.CalledProcessError(1, ["rclone", "copyto"])
            return run(*args)

        with patch.object(worker, "rclone", side_effect=interrupted):
            with self.assertRaises(subprocess.CalledProcessError):
                self.backup()
        self.assertEqual(len(list(self.folder.glob("*.cp7"))), 1)
        self.assertEqual(list(self.folder.glob("*.verified.json")), [])
        resumed = self.backup()
        self.assertFalse(resumed["uploaded"])
        self.assertTrue(resumed["new_receipt"])

    def test_same_length_corruption_fails_fresh_readback(self):
        proof = self.backup()["verified"]
        (self.folder / proof["archive"]).write_bytes(b"X" * proof["bytes"])
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            self.backup()

    def test_missing_previously_verified_payload_stops(self):
        proof = self.backup()["verified"]
        (self.folder / proof["archive"]).unlink()
        with self.assertRaisesRegex(ValueError, "sudah terbit"):
            self.backup()
        with self.assertRaisesRegex(ValueError, "Tahan retensi"):
            worker.retention_plan(REMOTE, DAY)

    def test_overlapping_process_is_refused(self):
        with worker.single_writer(self.state):
            result = subprocess.run([sys.executable, str(HERE / "backup_malam.py"), "backup",
                                     "--archive", str(self.archive), "--reference", str(self.ref),
                                     "--state", str(self.state), "--night", str(DAY)],
                                    capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"siklus backup lain", result.stderr)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_retention_counts_verified_nights_only(self):
        days = [DAY - timedelta(days=i) for i in range(19) if i not in (2, 5, 9)]
        for night in days:
            self.archive.write_bytes(f"synthetic at {night}".encode())
            self.reference(night)
            self.backup(night)
        orphan = self.folder / f"{DAY - timedelta(days=2)}--{hashlib.sha256(b'orphan').hexdigest()}.cp7"
        orphan.write_bytes(b"orphan")
        unrelated = self.folder / "operator-note.txt"
        unrelated.write_text("keep")
        before = sorted(x.name for x in self.folder.iterdir())
        actual = worker.retention_plan(REMOTE, DAY)
        self.assertEqual(actual["verified_nights"], 16)
        self.assertEqual(actual["keep"], [str(d) for d in days[:14]])
        self.assertEqual([p[:10] for p in actual["eligible"]], [str(d) for d in days[14:]])
        self.assertFalse(actual["delete_applied"])
        self.assertEqual(before, sorted(x.name for x in self.folder.iterdir()))

    def test_marker_changed_after_publish_blocks_retention(self):
        self.backup()
        marker = next(self.folder.glob("*.verified.json"))
        data = json.loads(marker.read_bytes())
        data["bytes"] += 1
        marker.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "Tahan retensi"):
            worker.retention_plan(REMOTE, DAY)


if __name__ == "__main__":
    unittest.main()
