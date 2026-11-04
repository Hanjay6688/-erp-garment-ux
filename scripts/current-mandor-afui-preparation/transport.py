"""Whole current Afui transport with explicit Mandor location and filenames.

No financial worker, supervisor, recovery budget, source or authority is
replaced. Only the one existing watcher observes two fixed proof directories.
"""
from hashlib import sha256
from pathlib import Path
import argparse
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ORIGINAL = ROOT / 'scripts/cp7_accessory_nonpayable/durable_action.mjs'
PIN = dict(bytes=13814, sha256='4cdb05df0247e860edb76f2f62ce8e28b44e9f6d99e89d622a69b7a4a6b1a8ce')
NAMES = ('CP7_FG_MANDOR_NATIVE9_STRICT.json', 'CP7_FG_MANDOR_NATIVE9_STRICT_BUSINESS_DAY_FIRST_ATTEMPT.json',
         'CP7_FG_MANDOR_NATIVE9.json', 'MANDOR_SESSION4_ORIGINAL.json', 'MANDOR_HTTP2_ORIGINAL.json',
         'MANDOR_BROWSER_FIXTURE.json', 'MANDOR_BROWSER_STATE.json', 'MANDOR_BROWSER2_ORIGINAL.json')


def require(value, message):
    if not value:
        raise ValueError(message)


def derive(raw=None):
    if raw is None:
        raw = ORIGINAL.read_bytes()
    require(dict(bytes=len(raw), sha256=sha256(raw).hexdigest()) == PIN, 'MANDOR_TRANSPORT_EXACT_WHOLE_CURRENT_AFUI_SOURCE')
    text = raw.decode()
    routes = (
        ("  'AFUI_BROWSER_NATIVE_PREREQUISITE.json', 'AFUI_BROWSER_SETTINGS_STATE.json',\n",
         "  'AFUI_BROWSER_NATIVE_PREREQUISITE.json', 'AFUI_BROWSER_SETTINGS_STATE.json',\n  " + ', '.join(repr(n) for n in NAMES) + ',\n'),
        ("  if (NAMED_ORIGINALS.has(name) || /^AFUI_ACCESS_", "  if (NAMED_ORIGINALS.has(name) || /^MANDOR_ACCESS_[A-Z0-9_]+_[a-f0-9]{32}\\.json\\.gz$/.test(name) || /^AFUI_ACCESS_"),
        ("  const scan = async () => {\n    let entries;", "  const scan = async () => {\n    for (const observedDirectory of [caseDirectory, path.dirname(caseDirectory)]) {\n    let entries;"),
        ("await regular(caseDirectory, true); entries = await fs.readdir(caseDirectory)",
         "await regular(observedDirectory, true); entries = await fs.readdir(observedDirectory)"),
        ("if (e.code === 'ENOENT') return; throw e;", "if (e.code === 'ENOENT') continue; throw e;"),
        ("snapshot(path.join(caseDirectory, name), directory, identity)", "snapshot(path.join(observedDirectory, name), directory, identity)"),
        ("      const label = originalLabel(name);", "      if (observedDirectory !== caseDirectory && /^CP7_FG_MANDOR_NATIVE9_STRICT(?:_BUSINESS_DAY_FIRST_ATTEMPT)?\\.json$/.test(name)) continue;\n      const label = originalLabel(name);"),
        ("    }\n  };\n  const watcher =", "    }\n    }\n  };\n  const watcher ="),
        ("auditor/scripts/cp7_accessory_nonpayable", "auditor/scripts/current-mandor-afui-preparation"),
        ("AFUI_JOB_START_MONOTONIC", "MANDOR_NATIVE_JOB_START_MONOTONIC"),
        ("path.join(HERE, 'runtime_supervisor.py')", "path.join(HERE, '../current-mandor-shop-native-qualification/runtime_supervisor.py')"),
        ("caseDirectory: path.join(c.out, 'AFUI_CASE_STDOUT')", "caseDirectory: path.join(c.out, 'MANDOR_CASE_STDOUT')"),
        ("'afui-original-' + run", "'mandor-original-' + run"),
        ("'AFUI_DURABLE_RUNTIME.json'", "'MANDOR_DURABLE_RUNTIME.json'"),
    )
    for before, after in routes:
        require(text.count(before) == 1 and after not in text, 'MANDOR_TRANSPORT_ONE_REVIEWED_SOURCE_ROUTE:' + before)
        text = text.replace(before, after, 1)
    recovered = text
    for before, after in reversed(routes):
        require(recovered.count(after) == 1, 'MANDOR_TRANSPORT_ONE_EXACT_INVERSE_ROUTE')
        recovered = recovered.replace(after, before, 1)
    require(recovered.encode() == raw, 'MANDOR_TRANSPORT_COMPLETE_ORIGINAL_NOT_RECOVERED')
    return text, dict(retained=PIN, derived=dict(bytes=len(text.encode()), sha256=sha256(text.encode()).hexdigest()),
        reversible_routes=len(routes), entire_original_recovered=True, fixed_proof_directories=2,
        existing_single_worker_and_one_watcher_preserved=True, all_identity_hash_CRC_official_uploader_signal_and_350_minute_retention_deadline_unchanged=True,
        no_new_worker_or_schedule=True, actual_ERP_cases=0, financial_acceptance_credit=0, production_go=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser();parser.add_argument('--check', action='store_true', required=True);parser.parse_args()
    text, proof = derive()
    require((HERE / 'durable_action.mjs').read_bytes() == text.encode(), 'MANDOR_TRANSPORT_EXACT_REVIEWABLE_MODULE')
    print(json.dumps(proof, sort_keys=True))
