"""Transfer one synthetic fixture from a cloud runner to an isolated Box folder."""
from datetime import date, datetime, timedelta, timezone
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zipfile import ZipFile, ZipInfo

from cryptography.hazmat.primitives.ciphers.aead import AESSIV

import backup_malam as nightly


FOLDER = "GitHub-Gratis"
REMOTE = "boxbackup:Gladi-Sintetis"
RUN_MARKER = ".retiring.json"
ARCHIVE_MAGIC = b"GLADI-BOX-1\0"
MAX_FIXTURE = 4096


def fixture(day, key):
    """Same day and key reproduce the same sealed, synthetic export on a fresh runner."""
    rows = {"scope": "synthetic-transfer-only", "tanggal_wib": day.isoformat(),
            "stok_awal": 12, "terjual": 3, "stok_akhir": 9}
    buf = BytesIO()
    with ZipFile(buf, "w") as archive:
        info = ZipInfo("stok-dummy.json", (day.year, day.month, day.day, 0, 0, 0))
        info.create_system = 3
        info.external_attr = 0o600 << 16
        archive.writestr(info, json.dumps(rows, sort_keys=True).encode())
    blob = ARCHIVE_MAGIC + AESSIV(key).encrypt(buf.getvalue(), [ARCHIVE_MAGIC])
    if len(blob) > MAX_FIXTURE:
        raise ValueError("Arsip gladi melebihi batas.")
    return blob


def read_config(raw, client_secret=None):
    if not raw:
        raise ValueError("Izin mesin Box belum dipasang pada environment erp-box-gladi.")
    cfg = json.loads(raw)
    if not isinstance(cfg, dict):
        raise ValueError("Konfigurasi mesin Box belum lengkap.")
    if client_secret:
        cfg["client_secret"] = client_secret
    for field in ("client_id", "client_secret", "enterprise_id", "folder_id", "fixture_key"):
        if not isinstance(cfg.get(field), str) or not cfg[field].strip():
            raise ValueError("Konfigurasi mesin Box belum lengkap.")
    if not all(re.fullmatch(r"[1-9][0-9]*", cfg[k]) for k in ("folder_id", "enterprise_id")):
        raise ValueError("Identitas Box tidak sah.")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", cfg["fixture_key"]):
        raise ValueError("Kunci gladi tidak sah.")
    return cfg


def box_json(url, *, token=None, form=None):
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    data = urlencode(form).encode() if form else None
    try:
        with urlopen(Request(url, data=data, headers=headers), timeout=25) as response:
            return json.load(response)
    except HTTPError as error:
        raise ValueError(f"Box menolak permintaan (HTTP {error.code}).") from None
    except URLError:
        raise ValueError("Koneksi ke Box gagal.") from None


def connect(cfg):
    result = box_json("https://api.box.com/oauth2/token", form={
        "grant_type": "client_credentials", "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"], "box_subject_type": "enterprise",
        "box_subject_id": cfg["enterprise_id"]})
    token = result.get("access_token")
    if not isinstance(token, str) or not token or int(result.get("expires_in", 0)) < 900:
        raise ValueError("Box tidak memberikan izin yang cukup lama untuk satu siklus.")
    folder = box_json("https://api.box.com/2.0/folders/" + cfg["folder_id"] +
                      "?fields=id,name,permissions,shared_link,trashed_at", token=token)
    if (folder.get("id") != cfg["folder_id"] or folder.get("name") != FOLDER
            or folder.get("shared_link") or folder.get("trashed_at")
            or not folder.get("permissions", {}).get("can_upload")):
        raise ValueError("Folder tujuan gladi tidak cocok atau belum memberi akses unggah.")
    expiry = datetime.now(timezone.utc) + timedelta(seconds=int(result["expires_in"]))
    os.environ.update(
        RCLONE_CONFIG_BOX_TYPE="box", RCLONE_CONFIG_BOX_ROOT_FOLDER_ID=cfg["folder_id"],
        RCLONE_CONFIG_BOX_TOKEN=json.dumps({"access_token": token, "token_type": "Bearer",
                                             "expiry": expiry.isoformat()}),
        RCLONE_CONFIG_BOXBACKUP_REMOTE="box:",
    )


def expected(day, key):
    body = fixture(day, key)
    digest = hashlib.sha256(body).hexdigest()
    return body, f"{day.isoformat()}--{digest}"


def original_receipt(proof, stamp, data, stem):
    # An identical source may be regenerated later that day. Keep its first capture time.
    day = stamp.astimezone(nightly.WIB).date()
    if not isinstance(proof, dict):
        raise ValueError("Bukti gladi tidak sah.")
    wanted = nightly.receipt_for(day, proof.get("captured_at"), len(data), stem.split("--")[1])
    if proof != wanted or datetime.fromisoformat(wanted["captured_at"]) > stamp:
        raise ValueError("Bukti yang tersimpan berbeda dari sumber gladi.")
    return wanted


def file_bytes(name, length):
    if not 0 < length <= MAX_FIXTURE:
        raise ValueError("Ukuran file di folder gladi tidak sah.")
    return nightly.rclone("cat", REMOTE + "/" + name, "--count", str(length + 1))


def retire(day, key):
    """Only delete reproducible test data once 14 newer verified nights still read intact."""
    plan = nightly.retention_plan(REMOTE, day)
    rows = json.loads(nightly.rclone("lsjson", REMOTE, "--files-only", "--no-modtime", "--no-mimetype"))
    sizes = {r["Name"]: r["Size"] for r in rows}
    pending = [n[:-len(RUN_MARKER)] for n in sizes if n.endswith(RUN_MARKER)]
    candidates = sorted(set([name[:-4] for name in plan["eligible"]] + pending))
    if not candidates:
        return plan["verified_nights"], 0
    if len(plan["keep"]) != nightly.KEEP_NIGHTS:
        raise ValueError("Belum ada 14 malam lebih baru untuk membersihkan arsip.")
    for label in plan["keep"]:
        kept_day = date.fromisoformat(label)
        data, stem = expected(kept_day, key)
        marker = stem + ".verified.json"
        if marker not in sizes:
            raise ValueError("Bukti arsip yang akan dipertahankan tidak cocok dengan sumber.")
        proof = nightly.read_marker(REMOTE, marker, sizes[marker])
        reference = nightly.receipt_for(kept_day, proof["captured_at"], len(data), stem.split("--")[1])
        if (reference != proof or sizes.get(stem + ".cp7") != len(data)
                or file_bytes(stem + ".cp7", len(data)) != data):
            raise ValueError("Arsip yang akan dipertahankan gagal verifikasi.")
    for stem in candidates:
        old_day = date.fromisoformat(stem.split("--")[0])
        data, correct = expected(old_day, key)
        if stem != correct or old_day.isoformat() >= min(plan["keep"]):
            raise ValueError("Calon pembersihan berada di luar cakupan gladi.")
        marker, journal, payload = stem + ".verified.json", stem + RUN_MARKER, stem + ".cp7"
        if (journal in sizes) == (marker in sizes):
            raise ValueError("Status pembersihan ganda atau tidak lengkap.")
        evidence = journal if journal in sizes else marker
        proof = nightly.read_marker(REMOTE, evidence, sizes[evidence])
        validated = nightly.receipt_for(old_day, proof["captured_at"], len(data), stem.split("--")[1])
        if validated != proof or (evidence == marker and payload not in sizes):
            raise ValueError("Bukti pembersihan rusak.")
        if payload in sizes and (sizes[payload] != len(data) or file_bytes(payload, len(data)) != data):
            raise ValueError("Isi arsip lama berbeda dari data uji.")
        if evidence == marker:
            nightly.rclone("moveto", REMOTE + "/" + marker, REMOTE + "/" + journal, "--immutable")
        if payload in sizes:
            nightly.rclone("deletefile", REMOTE + "/" + payload)
        nightly.rclone("deletefile", REMOTE + "/" + journal)
    return len(plan["keep"]), len(candidates)


def transfer(stamp, key, work):
    day = stamp.astimezone(nightly.WIB).date()
    data, stem = expected(day, key)
    nightly.rclone("mkdir", REMOTE)
    files = nightly.listing(REMOTE)
    marker = stem + ".verified.json"
    captured = stamp.isoformat()
    if marker in files:
        proof = nightly.read_marker(REMOTE, marker, files[marker])
        captured = original_receipt(proof, stamp, data, stem)["captured_at"]
    archive, ref = work / "input.cp7", work / "reference.json"
    archive.write_bytes(data)
    ref.write_text(json.dumps({"captured_at": captured, "ciphertext_bytes": len(data),
                               "ciphertext_sha256": hashlib.sha256(data).hexdigest()}))
    outcome = nightly.backup(REMOTE, archive, ref, day, work / "lock")
    nights, retired = retire(day, key)
    return {"night_wib": str(day), "bytes": len(data), "sha256": outcome["verified"]["sha256"],
            "new_upload": outcome["uploaded"], "verified_nights": nights, "retired": retired,
            "source": "synthetic", "production_go": False}


def main():
    cfg = read_config(os.environ.pop("BOX_GLADI", ""), os.environ.pop("BOX_GLADI_CLIENT_SECRET", ""))
    with tempfile.TemporaryDirectory() as directory:
        os.environ["RCLONE_LOG_FILE"] = str(Path(directory) / "rclone.log")
        connect(cfg)
        proof = transfer(datetime.now(timezone.utc), bytes.fromhex(cfg["fixture_key"]), Path(directory))
    print(json.dumps(proof, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, TypeError, KeyError, OSError, subprocess.CalledProcessError) as error:
        # Never serialize a response, the Box config, or the process environment.
        if isinstance(error, subprocess.CalledProcessError):
            sys.exit("Transfer rclone gagal. Malam ini belum dapat dinyatakan lulus.")
        sys.exit(f"Gladi berhenti. {error}")
