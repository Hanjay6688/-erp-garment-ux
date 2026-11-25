"""Read-only CP7.5 parent check for the November 2026 Enteng CP6 BF test restore.

The report records the actual catalogue and the historical fixture separately.
It does not supply a synthetic factory receipt or authorize a production install.
Run against the disposable PostgreSQL clone using CP75_TEST_DSN. The Box ZIP
digest must come from the independently verified backup download.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import zipfile

import psycopg

import cp6_g01_fingerprint as fingerprint


REPO = Path(__file__).resolve().parents[1]
EARLY = "1bdca3766f7c9800d68295ff5122798060b8a05d"
RELEASE = "48858590a361343e73a7f16f6646363dc155c04e"
BF = "b036261ee8902fc3be5307d54cf2b021dd2e2b419e24100655a7a338b70bad0a"
PAIR_ARCHIVE = "5aa536700c5ccf40dc12ea19baf432eb032dd12733eba8d9f2618d351a67e7c2"
G01_DETAIL = "docs/evidence/cp6-g01/baseline_objects_run35901222287.json.gz"
G01_HOSTED = "docs/evidence/cp6-g01/hosted_summary.json"
WORKFLOW = ".github/workflows/cp6-full-schema-validation.yml"
DIRECTORY = "supabase/release/cp6-t3"
BOUNDARY = ("cp6_rollback", "170006", 128, 113, 0, 0, 1)
EARLY_NAME = re.compile(r"_erp_v2_6_20(?:[a-z]|aa|ab)_")
TRIM_LINE = re.compile(r"Path\('(supabase/migrations/[^']+\.sql)'\).*?base64\.b64encode\(p\[:-1\]\)")


class Mismatch(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Mismatch(message)


def git(*args):
    return subprocess.check_output(["git", "-C", REPO, *args])


def blob(commit, relative_path):
    return git("show", f"{commit}:{relative_path}")


def verify_file(path, expected):
    with path.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    require(actual == expected, f"Checksum mismatch for {path.name}")


def archive_rows(box_zip, box_digest):
    verify_file(box_zip, box_digest)
    with zipfile.ZipFile(box_zip) as archive:
        source = json.loads(archive.read("data/records.json"))
    rows = []
    for part in source:
        if part["relation"] == "supabase_migrations.schema_migrations":
            rows.extend(json.loads(part["payload"]))
    require(len(rows) == 70, "Unexpected number of source migrations in the Box restore")
    return sorted(rows, key=lambda row: row["version"])


def reference(pair_zip):
    verify_file(pair_zip, PAIR_ARCHIVE)
    with zipfile.ZipFile(pair_zip) as archive:
        data = json.loads(archive.read("cp75-original-observations/bf-reader-comparison.json"))
    require(data["native_seal"] == BF and seal(data["native_groups"]) == BF, "BF reference differs")
    return data


def seal(groups):
    return hashlib.sha256(json.dumps(groups, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def group(entries):
    text = "\n".join(f"{key}={value}" for key, value in sorted(entries))
    return {"n": len(entries), "md5": hashlib.md5(text.encode()).hexdigest()}


def ledger_entry(number, version, name, statements):
    # Mirrors cp6_g01_fingerprint.detail('platform_ledger') for PostgreSQL text[].
    text = f"{len(statements)}|" + "\n".join(s for s in statements if s is not None)
    return f"{number:03d} {version} {name or ''}", hashlib.md5(text.encode()).hexdigest()


def release_inputs():
    pins = [
        (RELEASE, G01_DETAIL, "cea8ebaf1f20a42c875c1d7063e33ad2216f99b2"),
        (EARLY, WORKFLOW, "65340533b6307a6d2e0af8947547392aed4ab75b"),
        (RELEASE, DIRECTORY, "557896a51f0661f73b74bdf9babaf9d08e7314a9"),
    ]
    for commit, path, expected in pins:
        require(git("rev-parse", f"{commit}:{path}").decode().strip() == expected, f"Wrong source for {path}")
    reader_pin = git("hash-object", str(Path(fingerprint.__file__).resolve())).decode().strip()
    require(reader_pin == "b30172a78ce3927026275933e77d105207d9014b", "Wrong catalogue reader")
    detail = json.loads(gzip.decompress(blob(RELEASE, G01_DETAIL)))
    historical = [(key, value) for kind, key, value in detail if kind == "platform_ledger"]
    require(len(historical) == 70, "Historical G-01 row count differs")
    workflow = blob(EARLY, WORKFLOW).decode()
    trimmed = set(TRIM_LINE.findall(workflow))
    early_paths = git("ls-tree", "-r", "--name-only", EARLY, "supabase/migrations").decode().splitlines()
    early = sorted(p for p in early_paths if EARLY_NAME.search(p) and p.endswith(".sql"))
    late = [f["file"] for f in json.loads(blob(RELEASE, DIRECTORY + "/MANIFEST.json"))["files"]]
    require(len(early) == 28 and len(late) == 30 and trimmed.intersection(early) == set(early[:6]),
            "Release paths or six historical line-ending conversions differ")
    updates = []
    for commit, names in ((EARLY, early), (RELEASE, late)):
        for path in names:
            version, name = Path(path).stem.split("_", 1)
            source = blob(commit, path).decode("utf-8")
            keep_last_lf = path not in trimmed
            require(keep_last_lf or source.endswith("\n"), "Historical conversion requires a final LF")
            updates.append((version, name, source, keep_last_lf))
    hosted_ledger = json.loads(blob(RELEASE, G01_HOSTED))["summary"]["platform_ledger"]
    return historical, updates, hosted_ledger


def compare_ledger(actual, source, historical, updates, hosted_ledger, archived_ledger):
    require(len(actual) == len(source) + len(updates) == 128, "Number of migrations differs")
    require(actual[:len(source)] == source, "Archived Enteng migration rows differ, including metadata")
    current = [ledger_entry(n, row["version"], row["name"], row["statements"] or [])
               for n, row in enumerate(actual, 1)]
    require(group(current[:len(source)]) == hosted_ledger, "Old rows do not match the independent G-01 source")
    expected = list(historical)
    shortened = []
    for n, (version, name, body, keep_lf) in enumerate(updates, len(source)+1):
        row = actual[n-1]
        require((row["version"], row["name"], row["statements"]) == (version, name, [body]),
                f"Installed migration differs from its release file at row {n}")
        fixture_body = body if keep_lf else body[:-1]
        expected.append(ledger_entry(n, version, name, [fixture_body]))
        if not keep_lf:
            shortened.append(version)
    require(group(expected) == archived_ledger, "Reconstructed history differs from the signed BF reference")
    old_diffs = []
    for n, ((left, left_hash), (right, right_hash)) in enumerate(zip(current[:len(source)], historical), 1):
        if left != right or left_hash != right_hash:
            old_diffs.append({"row":n, "live_recorded_identity_differs_from_fixture":left!=right,
                              "live_statement_digest_differs_from_fixture":left_hash!=right_hash})
    return {"raw":group(current), "historical":group(expected), "source_rows_verified":len(source),
            "release_files_byte_exact":len(updates), "old_fixture_differences":old_diffs,
            "historical_final_lf_removed":shortened}


def check(dsn, source, expected, inputs):
    with psycopg.connect(dsn) as conn:
        conn.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
        conn.read_only = True
        with conn.cursor() as cur:
            boundary = cur.execute("""
                select current_database(),current_setting('server_version_num'),
                    (select count(*) from supabase_migrations.schema_migrations),
                    (select count(*) from erp.schema_migrations),(select count(*) from auth.users),
                    (select count(*) from erp.app_users),
                    (select count(*) from erp.schema_migrations where version='v2.6.20bf')
            """).fetchone()
            require(boundary == BOUNDARY, "Unexpected local Enteng BF boundary")
            require(cur.execute("select inet_server_addr() = '127.0.0.1'::inet, "
                                "current_setting('cron.launch_active_jobs'),current_setting('transaction_read_only')")
                    .fetchone() == (True, "off", "on"), "Expected read-only verification on the local inactive scheduler")
            cur.execute("select set_config('search_path',%s,true),set_config('TimeZone','UTC',true)",
                        (expected["source_session_path"],))
            actual_groups = cur.execute(fingerprint.SUMMARY).fetchone()[0]
            groups = expected["native_groups"]
            require(actual_groups.keys() == groups.keys(), "Catalogue group names differ")
            others = [k for k in groups if k != "platform_ledger" and groups[k] != actual_groups[k]]
            require(not others, "Other catalogue differences: " + ", ".join(sorted(others)))
            live = [row for (row,) in cur.execute("select to_jsonb(m) from supabase_migrations.schema_migrations m order by version")]
            ledger = compare_ledger(live, source, *inputs, groups["platform_ledger"])
            require(actual_groups["platform_ledger"] == ledger["raw"], "Row reconstruction and native PostgreSQL disagree")
            direct = sorted(k for k in groups if groups[k] == actual_groups[k])
            return {"status":"BF_SOURCE_VERIFIED", "raw_group_matches":direct, "raw_catalogue":seal(actual_groups),
                    "historical_catalogue":BF, "raw_catalogue_equal":actual_groups==groups,
                    "ledger":ledger, "boundary":list(boundary), "production_go":False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--box", type=Path, required=True)
    parser.add_argument("--box-sha256", required=True)
    parser.add_argument("--pair", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    data = check(os.environ["CP75_TEST_DSN"], archive_rows(args.box, args.box_sha256),
                 reference(args.pair), release_inputs())
    args.out.write_text(json.dumps(data, indent=2) + "\n")
    print(data["status"], len(data["raw_group_matches"]), "exact groups, 128 ledger rows verified")


if __name__ == "__main__":
    main()

