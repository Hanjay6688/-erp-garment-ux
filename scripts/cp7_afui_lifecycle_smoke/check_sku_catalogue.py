"""Prove the exact SKU capture against Global's independent SQL fingerprint."""
from hashlib import file_digest, sha256
from pathlib import Path
from types import ModuleType
import json
import os
import sys

import psycopg

CANDIDATE = Path(sys.argv[1]).resolve()
OUTPUT = CANDIDATE / 'cp6-proof/t3'
HERE = Path(__file__).resolve().parent


def load(name, path, raw):
    module = ModuleType(name)
    module.__file__ = str(path)
    exec(compile(raw, module.__file__, 'exec', dont_inherit=True), module.__dict__)
    return module


capture_path = CANDIDATE / 'scripts/current-sku-automatic-composite-preparation/global_parent_catalogue.py'
source = (HERE / 'sku_global_parent_catalogue.py').read_bytes()
with capture_path.open('xb') as stream:
    stream.write(source)
observer = load('exact_current_sku_capture', capture_path, source)
primitive = HERE.parents[0] / 'cp7_accessory_nonpayable/complete_original_io.py'
raw = primitive.read_bytes()
assert len(raw) == 5951 and sha256(raw).hexdigest() == 'f7c732004e1f5f0f2fe7ac7e08a6f049e6d41f0074fca7336c66736aaf522170'
originals = load('exact_complete_original_io', primitive, raw)
options = dict(host='127.0.0.1', port=54322, user='postgres', password=os.environ['CP7_SKU_SMOKE_PASSWORD'],
               connect_timeout=5, options='-c search_path=public -c TimeZone=Asia/Jakarta')
with psycopg.connect(dbname='cp6_rollback', autocommit=True, **options) as seed:
    seed.execute('create schema cp7_sku_census_smoke')
    seed.execute('create table cp7_sku_census_smoke.fixture (id integer generated always as identity, value text not null)')
    seed.execute("insert into cp7_sku_census_smoke.fixture (value) values ('tiny isolated fixture')")

capture, _, groups = observer.exact_readers()
context = capture.__globals__
catalogue_sql, _ = context['catalogue_profile'].derive()
sql_body = catalogue_sql.split('$catalogue$')[1]
report = {}
sentinel = object()


def unchanged_exercise(conn, cursor, database, url, case_report, state):
    assert cursor.connection is conn and database == 'fixture' and url is None and state is sentinel
    assert case_report is report and case_report['Global_parent_catalogue']['status'] == 'ACTUAL_FULL25_SKU_CATALOGUE_OBSERVED'
    assert cursor.execute("select current_setting('search_path'), current_setting('TimeZone'), current_setting('transaction_read_only')").fetchone() == ('public', 'Asia/Jakarta', 'on')
    assert cursor.execute('select id,value from cp7_sku_census_smoke.fixture').fetchall() == [(1, 'tiny isolated fixture')]
    return sentinel


bound = observer.bind(unchanged_exercise, originals)
with psycopg.connect(dbname='postgres', **options) as wrong, wrong.cursor() as cursor:
    try:
        bound(wrong, cursor, 'fixture', None, {}, sentinel)
    except ValueError as error:
        assert str(error) == 'SKU_GLOBAL_FIXED_DISPOSABLE_DATABASE_REQUIRED'
    else:
        raise AssertionError('The catalogue observer admitted the wrong database')
assert not (OUTPUT / observer.ORIGINAL).exists()

with psycopg.connect(dbname='cp6_rollback', **options) as conn, conn.cursor() as cursor:
    conn.read_only = True
    assert bound(conn, cursor, 'fixture', None, report, sentinel) is sentinel
    with context['metadata_context'](cursor):
        independent = cursor.execute(sql_body).fetchone()[0]
    assert cursor.execute("select current_setting('search_path'), current_setting('TimeZone')").fetchone() == ('public', 'Asia/Jakarta')
receipt = report['Global_parent_catalogue']
assert independent == receipt['fingerprint'] and independent['groups'] == 25
path = OUTPUT / observer.ORIGINAL
with path.open('rb') as stream:
    assert receipt['original']['sha256'] == file_digest(stream, 'sha256').hexdigest()
value = json.loads(path.read_bytes())
assert set(value) == groups and any(row[0] == 'cp7_sku_census_smoke.fixture' for row in value['relations'])
assert receipt['actual_ERP_case_credit'] == 0 and receipt['complete_input_review'] is False
receipt.update(status='PASS_ISOLATED_SKU_GLOBAL_CATALOGUE_CAPTURE', observer_bytes=len(source),
               observer_sha256=sha256(source).hexdigest(), independent_native_SQL_fingerprint_equal=True,
               fixture_unchanged=True, settings_restored=True, wrong_database_refused=True,
               original_exercise_boundary_preserved=True, transaction_read_only=True)
(OUTPUT / 'SKU_GLOBAL_CATALOGUE_FIXTURE_RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, sort_keys=True))
