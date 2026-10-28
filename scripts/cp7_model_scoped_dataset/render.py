"""Derive single-target model observations without changing the legacy dataset."""
from pathlib import Path
from hashlib import sha256
import json

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'cp7-src/model-native/source.sql'


def render():
    source = SOURCE.read_text()
    start = source.index('create function cp7_model_native.dataset(')
    sql = source[start:source.index('$$;', start) + 3]
    sql = sql.replace('cp7_model_native.dataset(', 'cp7_model_scoped_dataset.native_dataset(', 1)
    sql = sql.replace('cp7_planning.history_runs', 'cp7_model_history_runtime.runs')
    old = 'begin\n select *into r'
    assert sql.count(old) == 1
    sql = sql.replace(old, "begin\n q:=cp7_model_native.query(q);\n select *into r")
    old = " lo:=(r.query->>'from_date')::date;"
    assert sql.count(old) == 1
    sql = sql.replace(old, " if r.query->'target_key'is distinct from q->'target_key'\n  or r.result->>'scope'is distinct from'SINGLE_CURRENT_PHYSICAL_ROOT'then raise exception 'CP7_SCOPED_MODEL_TARGET_BINDING';end if;\n" + old)
    old = "  and h.query->>'group_mode'=r.query->>'group_mode'and(h.query->>'from_date')::date<=hi"
    assert sql.count(old) == 1
    sql = sql.replace(old, "  and h.query->'target_key'=q->'target_key'\n" + old)
    old = "where h.actor=p_actor and h.captured_at<=r.captured_at and h.query->>'group_mode'=r.query->>'group_mode'"
    assert sql.count(old) == 1
    sql = sql.replace(old, old + "\n   and h.query->'target_key'=q->'target_key'")
    sql = sql.replace("'NATIVE_HISTORY_RUN'", "'NATIVE_SCOPED_HISTORY_RUN'")
    sql = sql.replace("'CP7_MODEL_NATIVE_", "'CP7_SCOPED_MODEL_")
    header = '-- Derived from the exact legacy Native dataset; immutable scoped captures only.\n'
    return header + "create schema cp7_model_scoped_dataset authorization cp7_capture;\nrevoke all on schema cp7_model_scoped_dataset from public,anon,authenticated,service_role;\n\n" + sql + '\n\n' + (ROOT / 'binding.sql').read_text()


def manifest():
    return dict(contract='cp7.model-scoped-dataset.v1', private_functions=3, public_rpcs=0,
        new_tables=0, existing_replacements=0,
        legacy_source_sha256=sha256(SOURCE.read_bytes()).hexdigest(),
        sql_sha256=sha256(render().encode()).hexdigest(),
        known_at='ACTUAL_IMMUTABLE_NATIVE_CAPTURE_TIMES',
        legacy_history_and_model_runs_unchanged=True, model_caller_integrated=False,
        default_installer_changed=False, production_go=False)


if __name__ == '__main__':
    (ROOT / 'dataset.sql').write_text(render())
    (ROOT / 'MANIFEST.json').write_text(json.dumps(manifest(), indent=2) + '\n')
