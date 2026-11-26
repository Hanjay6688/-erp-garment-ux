#!/usr/bin/env python3
"""Resume the reviewed CP6 recovery packages in Enteng Uji over PostgreSQL.

Use Python 3 and psql on a private runner with network access to the project.
Mount the reviewed Box package contents using the original base/ and early/
directories and supply ENTENG_UJI_DATABASE_URL through the runner's secret
store. Pass a trusted Supabase CA bundle with --ca-file when necessary.

  python3 restore.py /private/box-packages --files-only
  python3 restore.py /private/box-packages
  python3 restore.py /private/box-packages --apply

Without --apply the script only checks the files and reads the database.
The default ends at CP6 AN. AO-BF use the separate reviewed maintenance
package, which requires an independent connection controlling admission.

Read the private Box packages through from_box.py.
Synthetic PostgreSQL test: https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/45736930963
"""

import argparse
import csv
import hashlib
import io
import json
import os
from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import parse_qs, unquote, urlsplit


PROJECT_REF_SHA256 = "e63c0f8d394a305540d50e575b192986c3f2ce8846f90087660a7944bee1c3c9"
POSTGRES_VERSION = 170012
DATABASE_URL_VARIABLE = "ENTENG_UJI_DATABASE_URL"
CERTIFICATES = Path("/etc/ssl/certs/ca-certificates.crt")
BOX_HISTORY_DIGEST = "2c01127132c860f2ed58a34aab1536e30ec7b51bd464795861f68e014fd964c1"
LAST_BOX_HISTORY_VERSION = "20260904232442"

PINNED_FILES = {
    "base/source-manifest.json": "82d51d147e3e082140a044be288eae8d4532aaaa5f8febcaf4698ba252262270",
    "base/verify-platform-history.sql": "8421e39bb7d1be9836f0092df0fb8e1090c5b5b48f6913115190b506169d6e46",
    "base/verify-rows.sql": "a0b5a2074cdb2512e5eea048d0409873389912b48173663a27911fe328e141df",
    "base/verify-sequences.sql": "78fd2719617b3321977b18c74482963a7cef28477d4dfa6a0d0b171e020e3af3",
    "base/verify-catalog.sql": "bfc337fd11bffc00b2f300dff6ac40d04e950ada0823f68a83f14bde5eb271ff",
    "base/expected-rows.json": "7f0847fa7eec576e35dace2e44000d3c2db5f9e89cf33d1d11c771b4bcb601de",
    "base/expected-sequences.json": "fabfc30615dc45c36235606b81a2cf903807e666eef887e814c4fc270e9a8416",
    "base/expected-groups.json": "d5c5e91b3062dbcfae9b96989a633caad4d92df2d55cc86dcf579e2d632708a7",
    "early/MANIFEST.json": "bb35baee1af65862a8e1f9d0373e17b9b255d24b5c6ba71a45890250697bbe39",
}

LEDGER = "supabase_migrations.schema_migrations"
LEDGER_DIGEST = """
SELECT encode(sha256(convert_to(
  coalesce(jsonb_agg(to_jsonb(m) ORDER BY version COLLATE "C")::text,'[]'),
  'UTF8'
)), 'hex') FROM supabase_migrations.schema_migrations AS m
"""


class RestoreError(RuntimeError):
    pass


@dataclass(frozen=True)
class Step:
    name: str
    digest: str
    sql: str


def verified_file(root, path, digest, size=None):
    try:
        data = (root / path).read_bytes()
    except OSError:
        raise RestoreError(f"Berkas paket tidak bisa dibaca: {path}") from None
    if (size is not None and len(data) != size) or hashlib.sha256(data).hexdigest() != digest:
        raise RestoreError(f"Ukuran atau checksum berubah: {path}")
    return data.decode("utf-8")


def load_packages(root, through):
    files = {
        path: verified_file(root, path, digest)
        for path, digest in PINNED_FILES.items()
        if not (through == "baseline" and path.startswith("early/"))
    }
    manifest = json.loads(files["base/source-manifest.json"])
    steps = [
        Step(
            f"enteng_uji_restore_cp6_{part:02}",
            item["sha256"],
            verified_file(root, "base/" + item["file"], item["sha256"], item["bytes"]),
        )
        for part, item in enumerate(manifest, start=1)
    ]
    if through == "an":
        steps.extend(
            Step(
                item["name"],
                item["sha256"],
                verified_file(root, "early/" + item["file"], item["sha256"], item["bytes"]),
            )
            for item in json.loads(files["early/MANIFEST.json"])
        )
    if len(steps) != (6 if through == "baseline" else 50):
        raise RestoreError("Jumlah langkah tidak cocok dengan paket yang diuji")
    if any(not re.fullmatch(r"[a-z0-9_]+", step.name) for step in steps):
        raise RestoreError("Nama langkah pemasangan tidak sah")
    source_header = files["base/verify-platform-history.sql"].splitlines()[0]
    source_versions = re.findall(r"\('(\d{14})'\)", source_header)
    if len(set(source_versions)) != 70:
        raise RestoreError("Daftar riwayat Enteng di Box tidak lengkap")
    return files, steps, source_versions


def connect_environment(raw, ca_file):
    if not raw:
        raise RestoreError(f"Pasang {DATABASE_URL_VARIABLE} di penyimpanan rahasia runner")
    try:
        url = urlsplit(raw)
        username = unquote(url.username or "")
        password = unquote(url.password or "")
        host = url.hostname or ""
        port = url.port or 5432
        query = parse_qs(url.query, keep_blank_values=True, strict_parsing=True)
    except ValueError:
        raise RestoreError("Alamat PostgreSQL Enteng Uji tidak valid") from None

    direct = re.fullmatch(r"db\.([a-z]{20})\.supabase\.co", host)
    pooler = re.fullmatch(r"aws-[0-9]+-ap-southeast-1\.pooler\.supabase\.com", host)
    pooler_user = re.fullmatch(r"postgres\.([a-z]{20})", username)
    project = None
    if direct and username == "postgres":
        project = direct[1]
    elif pooler and pooler_user:
        project = pooler_user[1]
    if (
        url.scheme not in {"postgres", "postgresql"}
        or project is None
        or hashlib.sha256(project.encode()).hexdigest() != PROJECT_REF_SHA256
        or port != 5432
        or url.path != "/postgres"
        or not password
        or url.fragment
        or query not in ({}, {"sslmode": ["require"]}, {"sslmode": ["verify-full"]})
    ):
        raise RestoreError("Runner hanya menerima Enteng Uji lewat PostgreSQL atau Session pooler")
    if not ca_file.is_file():
        raise RestoreError("Berkas CA TLS tidak tersedia untuk memverifikasi host Supabase")
    env = {
        key: val for key, val in os.environ.items()
        if not key.startswith("PG") and key != DATABASE_URL_VARIABLE
    }
    env.update(
        PGHOST=host,
        PGPORT="5432",
        PGUSER=username,
        PGDATABASE="postgres",
        PGPASSWORD=password,
        PGSSLMODE="verify-full",
        PGSSLROOTCERT=str(ca_file.resolve()),
        PGCONNECT_TIMEOUT="12",
        PGOPTIONS="-c TimeZone=UTC",
        PGCLIENTENCODING="UTF8",
        PGAPPNAME="enteng-uji-cp6-restore",
    )
    return env


def psql(env, sql, *, as_csv=False):
    binary = shutil.which("psql")
    if binary is None:
        raise RestoreError("Klien psql diperlukan di runner")
    output_option = "--csv" if as_csv else "--no-align"
    command = [
        binary, "-X", "-w", "-q", "-t", output_option,
        "--set=ON_ERROR_STOP=1", "--set=VERBOSITY=sqlstate", "-f", "-",
    ]
    try:
        result = subprocess.run(
            command, env=env, input=sql, encoding="utf-8",
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=420, check=False,
        )
    except subprocess.TimeoutExpired:
        raise RestoreError("Sesi PostgreSQL melebihi waktu. Periksa riwayat sebelum mengulang") from None
    if result.returncode != 0:
        sqlstate = re.search(r"ERROR:\s+([A-Z0-9]{5})\b", result.stderr)
        if sqlstate:
            raise RestoreError(f"PostgreSQL menolak perintah. SQLSTATE {sqlstate[1]}")
        if "password authentication failed" in result.stderr:
            raise RestoreError("Autentikasi PostgreSQL Enteng Uji gagal")
        if "certificate" in result.stderr:
            raise RestoreError("Verifikasi sertifikat PostgreSQL Enteng Uji gagal")
        raise RestoreError(f"Koneksi atau perintah psql gagal (kode {result.returncode})")
    return result.stdout


def quote(value):
    return "'" + value.replace("'", "''") + "'"


def read_state(env, source_versions):
    versions = ",".join(map(quote, source_versions))
    return json.loads(psql(env, f"""
SELECT jsonb_build_object(
  'database', current_database(),
  'server', current_setting('server_version_num')::int,
  'standby', pg_is_in_recovery(),
  'fingerprint', ({LEDGER_DIGEST}),
  'box_digest', (SELECT encode(sha256(convert_to(
    coalesce(jsonb_agg(to_jsonb(m) ORDER BY to_jsonb(m)::text COLLATE "C")::text,'[]'),
    'UTF8'
  )), 'hex') FROM {LEDGER} AS m WHERE version IN ({versions})),
  'entries', (SELECT coalesce(jsonb_agg(
    jsonb_build_object(
      'version', version,
      'name', name,
      'size', cardinality(statements),
      'body', CASE WHEN cardinality(statements)=1
        THEN encode(sha256(convert_to(statements[1],'UTF8')),'hex') END
    ) ORDER BY version COLLATE "C"),'[]')
    FROM {LEDGER})
);
"""))


def next_step(state, steps, archive_versions):
    if state["database"] != "postgres" or state["standby"] or state["server"] != POSTGRES_VERSION:
        raise RestoreError("Database atau versi PostgreSQL berbeda dari Enteng Uji yang diuji")
    if not re.fullmatch(r"[a-f0-9]{64}", state["fingerprint"]):
        raise RestoreError("Sidik jari riwayat tidak valid")

    entries = state["entries"]
    archive = [row for row in entries if row["version"] in archive_versions]
    restored = [row for row in entries if row["version"] not in archive_versions]
    expected = steps[:len(restored)]
    if (
        not restored
        or len(restored) > len(steps)
        or any(
            row["name"] != step.name
            or row["size"] != 1
            or row["body"] != step.digest
            or not re.fullmatch(r"\d{14}", row["version"])
            or row["version"] <= LAST_BOX_HISTORY_VERSION
            for row, step in zip(restored, expected)
        )
    ):
        raise RestoreError("Riwayat Enteng Uji menyimpang dari urutan dan checksum paket")

    completed = len(restored)
    if (completed <= 6 and archive) or (
        completed >= 10 and (len(archive) != 70 or state["box_digest"] != BOX_HISTORY_DIGEST)
    ):
        raise RestoreError("Riwayat asli dari Box tidak cocok dengan tahap pemulihan")
    return completed


def apply_step(env, step, state):
    marker = f"$sql_{step.digest[:20]}$"
    if marker in step.sql:
        raise RestoreError("Pemisah tanda terima bertabrakan dengan isi SQL")
    psql(env, f"""
BEGIN;
SET LOCAL lock_timeout = '10s';
LOCK TABLE {LEDGER} IN SHARE ROW EXCLUSIVE MODE;
DO $guard$
BEGIN
  IF ({LEDGER_DIGEST}) IS DISTINCT FROM '{state["fingerprint"]}' THEN
    RAISE EXCEPTION 'Riwayat berubah sejak pemeriksaan awal';
  END IF;
END
$guard$;
{step.sql}
INSERT INTO {LEDGER} (version, name, statements)
SELECT to_char(greatest(
  clock_timestamp() AT TIME ZONE 'UTC',
  coalesce((SELECT to_timestamp(max(version),'YYYYMMDDHH24MISS')
                      AT TIME ZONE current_setting('TimeZone') FROM {LEDGER}),
           '2000-01-01'::timestamp) + interval '1 second'
), 'YYYYMMDDHH24MISS'), {quote(step.name)}, ARRAY[{marker}{step.sql}{marker}];
COMMIT;
""")


def verify_baseline(env, files):
    def rows(name):
        sql = files[f"base/verify-{name}.sql"]
        return list(csv.reader(io.StringIO(psql(env, f"BEGIN READ ONLY;\n{sql}\nCOMMIT;\n", as_csv=True))))

    expected_rows = json.loads(files["base/expected-rows.json"])
    by_relation = {r["relation"]: (str(r["rows"]), r["sha256"]) for r in expected_rows}
    actual = {relation: (count, digest) for relation, count, digest in rows("rows")}
    if actual != by_relation:
        raise RestoreError("Isi tabel CP6 berbeda dari backup Box")
    expected_seq = {
        r["relation"]: (r["last_value"], "t" if r["is_called"] else "f")
        for r in json.loads(files["base/expected-sequences.json"])
    }
    if {relation: (last, called) for relation, last, called in rows("sequences")} != expected_seq:
        raise RestoreError("Nomor urut CP6 berbeda dari backup Box")
    expected_groups = json.loads(files["base/expected-groups.json"])
    if {kind: {"n": int(count), "digest": digest} for kind, count, digest in rows("catalog")} != expected_groups:
        raise RestoreError("Struktur atau izin CP6 berbeda dari backup Box")
    print(json.dumps({"baseline_checked": True, "tables": len(actual), "rows": sum(r["rows"] for r in expected_rows),
                      "sequences": len(expected_seq), "catalog_groups": len(expected_groups)}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packages", type=Path)
    parser.add_argument("--through", choices=("baseline", "an"), default="an")
    parser.add_argument("--ca-file", type=Path, default=CERTIFICATES)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--files-only", action="store_true")
    action.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        files, steps, archive_versions = load_packages(args.packages, args.through)
        print(json.dumps({"verified_files": len(steps), "through": args.through}), flush=True)
        if args.files_only:
            return 0
        env = connect_environment(os.environ.get(DATABASE_URL_VARIABLE), args.ca_file)
        state = read_state(env, archive_versions)
        completed = next_step(state, steps, archive_versions)
        print(json.dumps({"completed": completed, "next": steps[completed].name if completed < len(steps) else None}), flush=True)
        if completed == 6:
            verify_baseline(env, files)
        if args.apply:
            for step in steps[completed:]:
                apply_step(env, step, state)
                state = read_state(env, archive_versions)
                completed += 1
                if next_step(state, steps, archive_versions) != completed:
                    raise RestoreError("Pembacaan ulang belum menemukan satu tanda terima baru")
                print(json.dumps({"applied": step.name, "completed": completed}), flush=True)
                if completed == 6:
                    verify_baseline(env, files)
        return 0
    except (RestoreError, OSError, UnicodeError, ValueError, KeyError) as error:
        print(f"Pemasangan berhenti: {error if isinstance(error, RestoreError) else type(error).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
