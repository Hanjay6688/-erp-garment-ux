"""Exact old sorted-jsonb-array SHA256, streamed one row at a time for QA."""
from contextlib import closing,contextmanager
from hashlib import sha256
from pathlib import Path
import inspect,json
from psycopg import sql
from psycopg.rows import tuple_row

HERE=Path(__file__).resolve().parent


def array_fingerprint(rows):
    digest=sha256(b'[');count=0
    for value in rows:
        if not isinstance(value,str):raise ValueError('STREAM_JSONB_ROW_TEXT_REQUIRED')
        if count:digest.update(b', ')
        digest.update(value.encode('UTF8'));count+=1
    digest.update(b']');return [count,digest.hexdigest()]


def table_fingerprint(cur,name):
    query=sql.SQL('select to_jsonb(r)::text from {} r order by to_jsonb(r)::text').format(sql.Identifier(*name))
    with cur.connection.cursor(row_factory=tuple_row)as scan:
        with closing(scan.stream(query))as rows:
            return array_fingerprint(row[0]for row in rows)


def derived(catalog):
    binding=json.loads((HERE/'BINDING.json').read_bytes());original=inspect.getsource(catalog._data)
    assert original==binding['catalog_data_source']
    assert sha256(original.encode()).hexdigest()==binding['catalog_data_source_sha256']
    start=original.index('            row=cur.execute(');end=original.index('\n        sequences=',start)
    old=original[start:end]
    assert old.count('jsonb_agg(to_jsonb(r)order by to_jsonb(r)::text)')==1
    assert old.endswith("            result['.'.join(name)]=list(row)")
    replacement="            result['.'.join(name)]=table_fingerprint(cur,name)"
    code=original[:start]+replacement+original[end:]
    namespace=dict(vars(catalog),table_fingerprint=table_fingerprint)
    exec(compile(code,'<exact-streamed-catalog-data>','exec'),namespace)
    return namespace['_data'],dict(original_source_sha256=binding['catalog_data_source_sha256'],
        derived_source_sha256=sha256(code.encode()).hexdigest(),old_jsonb_array_text_hash_algorithm_unchanged=True,
        namespace_table_selection_authority_GUC_and_all_sequences_unchanged=True,
        excluded_tables_added=0,rows_or_fields_skipped=0,qualified_role_oracles_unchanged=True)


@contextmanager
def bound(catalog):
    original=catalog._data;candidate,proof=derived(catalog)
    catalog._data=candidate
    try:yield dict(proof,original=original,candidate=candidate)
    finally:
        assert catalog._data is candidate,'STREAM_DATA_CALLBACK_UNEXPECTEDLY_REPLACED'
        catalog._data=original


def validate(cur,context):
    assert cur.connection.info.host in ('localhost','127.0.0.1')and cur.connection.info.port==54322
    assert cur.execute('select current_database()').fetchone()==('cp6_rollback',)
    original=context['original'];candidate=context['candidate']
    before=original(cur);after=candidate(cur)
    assert before==after,'STREAM_DATA_LEGACY_WHOLE_DATABASE_HASH_MISMATCH'
    # Temporary synthetic data only. The original algorithm must reproduce the
    # real 256MiB array failure; the streamed digest retains every duplicate.
    with cur.connection.transaction():
        cur.execute('create temporary table cp7_fingerprint_large_regression(payload text)on commit drop')
        cur.execute("insert into cp7_fingerprint_large_regression select repeat('x',300000)from generate_series(1,1024)")
        failed=None
        try:
            with cur.connection.transaction():
                cur.execute("select encode(sha256(convert_to(jsonb_agg(to_jsonb(r)order by to_jsonb(r)::text)::text,'UTF8')),'hex')from cp7_fingerprint_large_regression r").fetchone()
        except Exception as error:
            failed=getattr(error,'sqlstate',None)
            assert failed=='54000'and '268435455'in str(error)
        assert failed=='54000','STREAM_DATA_EXPECTED_ARRAY_LIMIT_NOT_REPRODUCED'
        streamed=table_fingerprint(cur,('pg_temp','cp7_fingerprint_large_regression'))
        text='{"payload": "'+'x'*300000+'"}'
        expected=array_fingerprint(text for _ in range(1024))
        assert streamed==expected and streamed[0]==1024
        cur.execute('drop table cp7_fingerprint_large_regression')
    assert original(cur)==candidate(cur)==before
    return dict(status='PASS',all_scoped_tables_and_sequences_exact=len(before),old_hashes_equal_before_and_after=True,
        actual_old_array_limit_reproduced=True,old_SQLSTATE=failed,large_rows=1024,minimum_large_payload_bytes=307200000,
        large_streamed_digest=streamed,duplicate_multiplicity_preserved=True,
        excluded_tables=0,skipped_rows_or_fields=0,temporary_regression_fully_removed=True,
        ERP_rows_sequences_and_catalog_definitions_unchanged=True,ordinary_statement_limits_changed=False)
