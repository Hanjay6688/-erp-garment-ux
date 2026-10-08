"""Read-only CP7 install-file ownership check; never connect or execute SQL.

Compose the explicit F03/F04/F05 product in its declared install order. A SQL
file outside that composition must have an explicit diagnostic owner. This is
file reachability, not proof that a feature is complete or Native-qualified.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SQL_ROOT = ROOT / 'scripts/cp7-src'
PROBE_FILE = 'scripts/cp7-src/snapshot/capture_probe.sql'
PROBE_OWNER = 'scripts/cp7_p02_snapshot_probe.py'


def diagnostic_owner():
    """Check the declared probe is actually read and passed to its SQL runner."""
    tree = ast.parse((ROOT / PROBE_OWNER).read_text(), filename=PROBE_OWNER)
    reads_probe = any(
        isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == 'SQL'
                for target in node.targets)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Attribute)
        and node.value.func.attr == 'read_text'
        and any(isinstance(value, ast.Constant) and value.value == PROBE_FILE
                for value in ast.walk(node.value))
        for node in tree.body
    )
    executes_probe = any(
        isinstance(node, ast.FunctionDef) and node.name == 'capture'
        and any(isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr == 'execute'
                and call.args and isinstance(call.args[0], ast.Name)
                and call.args[0].id == 'SQL'
                for call in ast.walk(node))
        for node in tree.body
    )
    if not reads_probe or not executes_probe:
        raise AssertionError('CP7_DIAGNOSTIC_SQL_OWNER_MISSING: ' + PROBE_FILE)
    return {
        'owner': PROBE_OWNER,
        'purpose': 'ISOLATED_READ_ONLY_P02_DIAGNOSTIC_NOT_AN_INSTALLED_RPC',
        'sha256': hashlib.sha256((ROOT / PROBE_FILE).read_bytes()).hexdigest(),
        'owner_sha256': hashlib.sha256((ROOT / PROBE_OWNER).read_bytes()).hexdigest(),
    }


def inspect():
    observed = {}
    original_read = Path.read_text

    def record(path, *args, **kwargs):
        value = original_read(path, *args, **kwargs)
        absolute = path.resolve()
        if absolute.is_relative_to(SQL_ROOT) and absolute.suffix == '.sql':
            observed[str(absolute.relative_to(ROOT))] = hashlib.sha256(
                value.encode('utf-8')).hexdigest()
        return value

    with patch.object(Path, 'read_text', record):
        import cp7_f03_bundle as f03
        import cp7_planning_bundle as planning
        import cp7_baseline_bundle as baseline
        import cp7_supply_bundle as supply
        import cp7_schedule_bundle as schedule
        import cp7_analysis_bundle as analysis
        import cp7_reminder_v2_bundle as attention
        product = '\n'.join((
            f03.bundle(), planning.extension(), baseline.extension(),
            supply.extension(), schedule.extension(),
            analysis.predecessor.extension(), analysis.extension(),
            attention.extension(),
        ))

    all_sql = {str(path.relative_to(ROOT)) for path in SQL_ROOT.rglob('*.sql')}
    diagnostics = {PROBE_FILE: diagnostic_owner()}
    diagnostic_overlap = sorted(set(observed) & set(diagnostics))
    orphans = sorted(all_sql - set(observed) - set(diagnostics))
    missing = sorted((set(observed) | set(diagnostics)) - all_sql)
    result = {
        'classification': 'READ_ONLY_EXACT_PRODUCT_FILE_REACHABILITY_NOT_NATIVE_EXECUTION',
        'source_head': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'status': 'FAIL' if orphans or missing or diagnostic_overlap else 'PASS',
        'product_sha256': hashlib.sha256(product.encode('utf-8')).hexdigest(),
        'installed_sql_count': len(observed),
        'diagnostic_sql_count': len(diagnostics),
        'total_sql_count': len(all_sql),
        'installed_sql': dict(sorted(observed.items())),
        'diagnostic_sql': diagnostics,
        'unowned_sql': orphans,
        'missing_sql': missing,
        'diagnostic_also_installed': diagnostic_overlap,
        'native_execution': False,
        'feature_acceptance': False,
        'production_go': False,
    }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path,
                        help='Retain exact file hashes in a JSON receipt.')
    args = parser.parse_args()
    result = inspect()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in (
        'status', 'source_head', 'product_sha256', 'installed_sql_count',
        'diagnostic_sql_count', 'total_sql_count', 'unowned_sql', 'missing_sql',
        'diagnostic_also_installed', 'native_execution', 'feature_acceptance',
    )}))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
