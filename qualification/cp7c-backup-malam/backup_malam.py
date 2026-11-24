"""One nightly transfer of a sealed export, followed by an independent download."""

import argparse
from contextlib import contextmanager
from datetime import date, datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from zoneinfo import ZoneInfo


WIB = ZoneInfo("Asia/Jakarta")
KEEP_NIGHTS = 14
FORMAT = "erp-box-night-v1"
OBJECT = re.compile(r"(\d{4}-\d{2}-\d{2})--([0-9a-f]{64})\.(cp7|verified\.json)")


def rclone(*args):
    return subprocess.run(["rclone", *map(str, args)], check=True, stdout=subprocess.PIPE).stdout


def fingerprint(path):
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(block)
            digest.update(block)
    return size, digest.hexdigest()


def check_bytes(path, receipt):
    if fingerprint(path) != (receipt["bytes"], receipt["sha256"]):
        raise ValueError("Jumlah byte atau SHA-256 berbeda dari tanda terima sumber.")


def receipt_for(night, captured, size, sha):
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha):
        raise ValueError("SHA-256 sumber tidak sah.")
    if type(size) is not int or size < 1 or not isinstance(captured, str):
        raise ValueError("Ukuran atau waktu pengambilan sumber tidak sah.")
    stamp = datetime.fromisoformat(captured.replace("Z", "+00:00"))
    if stamp.utcoffset() is None or stamp.astimezone(WIB).date() != night:
        raise ValueError("Tanggal pengambilan sumber berbeda dari malam backup WIB.")
    key = f"{night.isoformat()}--{sha}"
    return {"format": FORMAT, "night_wib": night.isoformat(),
            "captured_at": stamp.astimezone(timezone.utc).isoformat(),
            "archive": key + ".cp7", "bytes": size, "sha256": sha}


def read_export(path, night):
    data = json.loads(path.read_bytes())
    if not isinstance(data, dict):
        raise ValueError("Tanda terima sumber harus berupa objek JSON.")
    captured = data.get("captured_at")
    # Older synthetic Writer receipts record the original capture rehearsal in UTC.
    if captured is None and data.get("environment") == "synthetic isolated loopback":
        captured = data.get("writer_rehearsal_utc")
    return receipt_for(night, captured, data["ciphertext_bytes"], data["ciphertext_sha256"])


def listing(remote):
    rows = json.loads(rclone("lsjson", remote, "--files-only", "--no-modtime", "--no-mimetype"))
    files = {}
    for row in rows:
        name = row["Name"]
        if OBJECT.fullmatch(name):
            if name in files:
                raise ValueError("Nama objek ganda di tujuan. Periksa folder backup.")
            files[name] = row["Size"]
    return files


def read_marker(remote, name, size):
    if not 0 < size <= 4096:
        raise ValueError("Ukuran bukti verifikasi tidak sah.")
    return json.loads(rclone("cat", remote + "/" + name, "--count", "4097"))


@contextmanager
def single_writer(state):
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (state / "backup.lock").open("a+b") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError("Mesin ini sedang menjalankan siklus backup lain.") from error
        yield


def backup(remote, archive, reference, night, state):
    receipt = read_export(reference, night)
    name = receipt["archive"]
    marker = name[:-4] + ".verified.json"
    with single_writer(state), tempfile.TemporaryDirectory(dir=state) as work:
        work = Path(work)
        # Each upload reads the exact bytes pinned by the producer, even if its input rotates.
        source = work / "source"
        shutil.copyfile(archive, source)
        check_bytes(source, receipt)
        rclone("mkdir", remote)
        files = listing(remote)
        prefix = night.isoformat() + "--"
        if any(p.startswith(prefix) and p not in {name, marker} for p in files):
            raise ValueError("Malam ini sudah memiliki arsip lain. Data yang ada dipertahankan.")
        prior = marker in files
        if prior and (name not in files or read_marker(remote, marker, files[marker]) != receipt):
            raise ValueError("Arsip atau bukti yang sudah terbit tidak cocok.")
        existed = name in files
        if not existed:
            rclone("copyto", source, remote + "/" + name, "--immutable", "--checksum")
        returned = work / "download"
        rclone("copyto", remote + "/" + name, returned)
        check_bytes(returned, receipt)
        if not prior:
            proof = work / "receipt"
            proof.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
            rclone("copyto", proof, remote + "/" + marker, "--immutable", "--checksum")
        final = listing(remote)
        if {p for p in final if p.startswith(prefix)} != {name, marker}:
            raise ValueError("Keadaan malam berubah saat verifikasi.")
        if final[name] != receipt["bytes"] or read_marker(remote, marker, final[marker]) != receipt:
            raise ValueError("Pembacaan ulang bukti atau objek gagal.")
        return {"verified": receipt, "uploaded": not existed, "new_receipt": not prior}


def retention_plan(remote, as_of):
    """Read-only planning. Already verified nights are counted once, with present payloads."""
    files = listing(remote)
    dates = {}
    for name, length in files.items():
        match = OBJECT.fullmatch(name)
        night = date.fromisoformat(match[1])
        if night > as_of:
            raise ValueError("Ada tanggal masa depan. Tahan retensi.")
        if match[3] != "verified.json":
            continue
        marker = read_marker(remote, name, length)
        expected = receipt_for(night, marker["captured_at"], marker["bytes"], match[2])
        if marker != expected or files.get(expected["archive"]) != expected["bytes"]:
            raise ValueError("Arsip atau bukti malam terverifikasi rusak. Tahan retensi.")
        if night in dates:
            raise ValueError("Satu malam mempunyai dua bukti berbeda. Tahan retensi.")
        dates[night] = expected["archive"]
    verified = sorted(dates, reverse=True)
    return {"verified_nights": len(verified),
            "keep": [d.isoformat() for d in verified[:KEEP_NIGHTS]],
            "eligible": [dates[d] for d in verified[KEEP_NIGHTS:]],
            "delete_applied": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["backup", "retention-plan"])
    parser.add_argument("--folder", default="Gladi-Mesin-CP7C", help="Subfolder of boxbackup:")
    parser.add_argument("--night", type=date.fromisoformat, default=datetime.now(WIB).date())
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--state", type=Path, help="Private persistent directory shared by runs on this worker")
    args = parser.parse_args()
    if not all(re.fullmatch(r"[\w .-]+", p) and p.strip() == p and p not in {".", ".."}
               for p in args.folder.split("/")):
        parser.error("Nama folder remote tidak sah.")
    remote = "boxbackup:" + args.folder
    if args.mode == "backup" and not all((args.archive, args.reference, args.state)):
        parser.error("backup memerlukan --archive, --reference dan --state.")
    try:
        if args.mode == "backup":
            result = backup(remote, args.archive, args.reference, args.night, args.state)
        else:
            result = retention_plan(remote, args.night)
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        sys.exit(f"Siklus berhenti. {error}")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
