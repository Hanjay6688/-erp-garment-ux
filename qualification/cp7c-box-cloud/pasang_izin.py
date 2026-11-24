"""Install the synthetic Box worker's secret using an existing GitHub CLI login."""
import argparse
import getpass
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys


REPO = "Hanjay6688/-erp-garment-ux"
ENVIRONMENT = "erp-box-gladi"


def install(folder):
    opts = ["--repo", REPO, "--env", ENVIRONMENT]
    listed = subprocess.run(["gh", "secret", "list", *opts, "--json", "name"],
                            capture_output=True, check=True)
    installed = any(s["name"] == "BOX_GLADI" for s in json.loads(listed.stdout))
    private = Path.home() / ".erp-box-gladi"
    private.mkdir(mode=0o700, exist_ok=True)
    key_path = private / (folder + ".key")
    if not key_path.exists():
        if installed:
            sys.exit("Secret sudah ada. Gunakan kembali kunci gladi asli dari komputer pemasang.")
        with os.fdopen(os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as out:
            out.write(secrets.token_hex(32) + "\n")
            out.flush()
            os.fsync(out.fileno())
    key = key_path.read_text().strip()
    if not re.fullmatch(r"[0-9a-f]{64}", key):
        sys.exit("Kunci gladi lokal tidak sah.")
    client = input("Box Client ID: ").strip()
    enterprise = input("Box Enterprise ID: ").strip()
    secret = getpass.getpass("Box Client Secret (tersembunyi): ").strip()
    if not client or not re.fullmatch(r"[1-9][0-9]*", enterprise) or not secret:
        sys.exit("Identitas aplikasi Box belum lengkap.")
    data = {"client_id": client, "enterprise_id": enterprise, "folder_id": folder,
            "client_secret": secret, "fixture_key": key}
    subprocess.run(["gh", "secret", "set", "BOX_GLADI", *opts],
                   input=json.dumps(data).encode(), check=True)
    print("Izin tersimpan pada environment erp-box-gladi. Jalankan gladi unggah–unduh.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", help="ID folder privat GitHub-Gratis")
    args = parser.parse_args()
    if not re.fullmatch(r"[1-9][0-9]*", args.folder):
        parser.error("Gunakan ID folder Box khusus gladi.")
    try:
        install(args.folder)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        sys.exit("Pemasangan berhenti. Periksa login GitHub, akses environment, dan kunci gladi.")
