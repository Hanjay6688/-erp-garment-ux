import json
import os
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from unittest.mock import patch
from zipfile import ZipFile

from cryptography.hazmat.primitives.ciphers.aead import AESSIV
import gladi as job


STAMP = datetime(2026, 11, 24, 18, 1, tzinfo=timezone.utc)
DAY = STAMP.astimezone(job.nightly.WIB).date()
KEY = bytes(range(32))  # test vector
CFG = {"client_id": "mock", "client_secret": "mock-only", "enterprise_id": "2",
       "folder_id": "3", "fixture_key": KEY.hex()}


class CloudTransfer(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.physical = self.base / "store" / "Gladi-Sintetis"
        self.physical.mkdir(parents=True)
        settings = patch.dict(os.environ, RCLONE_CONFIG_BOX_TYPE="alias",
                              RCLONE_CONFIG_BOX_REMOTE=str(self.physical.parent),
                              RCLONE_CONFIG_BOXBACKUP_REMOTE="box:")
        settings.start()
        self.addCleanup(settings.stop)

    def seed(self, n):
        for i in range(n):
            day = DAY - timedelta(days=i)
            data, stem = job.expected(day, KEY)
            record = job.nightly.receipt_for(day, f"{day}T01:00:00+07:00", len(data), stem.split("--")[1])
            (self.physical / (stem + ".cp7")).write_bytes(data)
            (self.physical / (stem + ".verified.json")).write_text(json.dumps(record))

    def test_fixture_opens_and_changes_each_day(self):
        data, _ = job.expected(DAY, KEY)
        plain = AESSIV(KEY).decrypt(data[len(job.ARCHIVE_MAGIC):], [job.ARCHIVE_MAGIC])
        with ZipFile(BytesIO(plain)) as z:
            rows = json.loads(z.read("stok-dummy.json"))
        self.assertEqual(rows["scope"], "synthetic-transfer-only")
        self.assertEqual(rows["stok_awal"] - rows["terjual"], rows["stok_akhir"])
        self.assertNotEqual(data, job.fixture(DAY - timedelta(days=1), KEY))

    def test_upload_then_repeat_on_fresh_runner(self):
        first = job.transfer(STAMP, KEY, self.base)
        before = {p.name: p.stat().st_mtime_ns for p in self.physical.iterdir()}
        other = self.base / "new-runner"
        other.mkdir()
        retry = job.transfer(STAMP + timedelta(minutes=10), KEY, other)
        self.assertTrue(first["new_upload"])
        self.assertFalse(retry["new_upload"])
        self.assertEqual(first["sha256"], retry["sha256"])
        self.assertEqual(retry["night_wib"], str(DAY))
        self.assertEqual(before, {p.name: p.stat().st_mtime_ns for p in self.physical.iterdir()})

    def test_missing_config_stops_before_network_access(self):
        with patch.dict(os.environ, BOX_GLADI=""), patch.object(job, "box_json") as http:
            with self.assertRaisesRegex(ValueError, "Izin mesin"):
                job.main()
            http.assert_not_called()
        with self.assertRaises(ValueError):
            job.read_config(json.dumps(dict(CFG, folder_id="0")))

    def test_machine_grant_is_scoped_to_private_pilot_folder(self):
        token = {"access_token": "simulated", "expires_in": 3600}
        folder = {"id": "3", "name": "GitHub-Gratis", "permissions": {"can_upload": True}}
        with patch.object(job, "box_json", side_effect=[token, folder]) as http:
            job.connect(CFG)
            self.assertEqual(http.call_args_list[0].kwargs["form"]["grant_type"], "client_credentials")
            self.assertEqual(os.environ["RCLONE_CONFIG_BOX_ROOT_FOLDER_ID"], "3")
        for wrong in (dict(folder, shared_link={"url": "example"}), dict(folder, name="ERP-Backup"),
                      dict(folder, permissions={"can_upload": False})):
            with patch.object(job, "box_json", side_effect=[token, wrong]):
                with self.assertRaisesRegex(ValueError, "Folder tujuan"):
                    job.connect(CFG)

    def test_separate_secret_works_with_private_web_setup(self):
        config = dict(CFG)
        secret = config.pop("client_secret")
        with self.assertRaisesRegex(ValueError, "belum lengkap"):
            job.read_config(json.dumps(config))
        self.assertEqual(job.read_config(json.dumps(config), secret), CFG)
        self.assertEqual(job.read_config(json.dumps(CFG)), CFG)

    def test_retire_only_older_verified_samples(self):
        self.seed(16)
        note = self.physical / "catatan.txt"
        note.write_text("private")
        self.assertEqual(job.retire(DAY, KEY), (14, 2))
        self.assertEqual(len(list(self.physical.glob("*.cp7"))), 14)
        self.assertEqual(len(list(self.physical.glob("*.verified.json"))), 14)
        self.assertEqual(note.read_text(), "private")
        self.assertEqual(job.retire(DAY, KEY), (14, 0))

    def test_corrupt_kept_sample_prevents_any_cleanup(self):
        self.seed(15)
        data, stem = job.expected(DAY, KEY)
        (self.physical / (stem + ".cp7")).write_bytes(b"x" * len(data))
        with self.assertRaisesRegex(ValueError, "dipertahankan"):
            job.retire(DAY, KEY)
        self.assertEqual(len(list(self.physical.glob("*.cp7"))), 15)

    def test_cleanup_resumes_from_either_intermediate_state(self):
        self.seed(16)
        for i in (14, 15):
            _, stem = job.expected(DAY - timedelta(days=i), KEY)
            (self.physical / (stem + ".verified.json")).rename(self.physical / (stem + job.RUN_MARKER))
            if i == 15:
                (self.physical / (stem + ".cp7")).unlink()
        self.assertEqual(job.retire(DAY, KEY), (14, 2))
        self.assertFalse(any(self.physical.glob("*" + job.RUN_MARKER)))

    def test_unverified_good_payload_cannot_substitute_for_another_receipt(self):
        self.seed(15)
        data, stem = job.expected(DAY, KEY)
        marker = self.physical / (stem + ".verified.json")
        captured = json.loads(marker.read_bytes())["captured_at"]
        marker.unlink()
        alternate_data, alternate = job.expected(DAY, bytes(reversed(KEY)))
        self.assertEqual(len(data), len(alternate_data))
        (self.physical / (alternate + ".cp7")).write_bytes(alternate_data)
        proof = job.nightly.receipt_for(DAY, captured, len(alternate_data), alternate.split("--")[1])
        (self.physical / (alternate + ".verified.json")).write_text(json.dumps(proof))
        with self.assertRaisesRegex(ValueError, "dipertahankan"):
            job.retire(DAY, KEY)
        self.assertEqual(len(list(self.physical.glob("*.cp7"))), 16)

    def test_future_capture_is_rejected_on_retry(self):
        self.seed(1)
        _, stem = job.expected(DAY, KEY)
        name = self.physical / (stem + ".verified.json")
        proof = json.loads(name.read_bytes())
        proof["captured_at"] = (STAMP + timedelta(hours=1)).isoformat()
        name.write_text(json.dumps(proof))
        with self.assertRaisesRegex(ValueError, "berbeda"):
            job.transfer(STAMP, KEY, self.base)


if __name__ == "__main__":
    main()
