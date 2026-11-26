"""Smoke tests for the public runner boundary, using only synthetic inputs."""

import base64
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import from_box
import restore


class RunnerTest(unittest.TestCase):
    def test_supabase_tls_and_target(self):
        project = "syntheticentengtestx"
        with patch.object(restore, "PROJECT_REF_SHA256", sha256(project.encode()).hexdigest()):
            url = f"postgresql://postgres.{project}:dummy%25only@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres"
            env = restore.connect_environment(url, restore.CERTIFICATES)
            self.assertEqual(env["PGPASSWORD"], "dummy%only")
            self.assertEqual(env["PGSSLMODE"], "verify-full")
            with self.assertRaises(restore.RestoreError):
                restore.connect_environment(url.replace(project, "anotherentengtestxx"), restore.CERTIFICATES)
            with self.assertRaises(restore.RestoreError):
                restore.connect_environment(url.replace(":5432", ":6543"), restore.CERTIFICATES)

    def test_only_box_can_supply_downloads(self):
        from_box.check_url("https://public.boxcloud.com/file/dummy")
        for url in ("https://other.example/file", "http://public.boxcloud.com/file",
                    "https://public.boxcloud.com@other.example/file"):
            with self.assertRaises(from_box.PackageError):
                from_box.check_url(url)

    def test_verified_package_stays_in_the_runner_directory(self):
        def wrapper(name):
            buffer = BytesIO()
            with ZipFile(buffer, "w") as archive:
                archive.writestr(name, "SELECT 1;")
            data = buffer.getvalue()
            digest = sha256(data).hexdigest()
            return json.dumps({"data": base64.b64encode(data).decode(), "sha256": digest, "bytes": len(data)}), (digest, len(data))

        with TemporaryDirectory() as folder:
            root = Path(folder)
            valid, pin = wrapper("synthetic.sql")
            with patch.dict(from_box.PACKAGES, {"base": pin}):
                from_box.open_package("base", valid, root)
                self.assertEqual((root / "base/synthetic.sql").read_text(), "SELECT 1;")
                damaged = json.loads(valid)
                damaged["sha256"] = "0" * 64
                with self.assertRaises(from_box.PackageError):
                    from_box.open_package("base", json.dumps(damaged), root)
            traversal, traversal_pin = wrapper("../unsafe.sql")
            with patch.dict(from_box.PACKAGES, {"base": traversal_pin}), self.assertRaises(from_box.PackageError):
                from_box.open_package("base", traversal, root)
            self.assertFalse((root / "unsafe.sql").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
