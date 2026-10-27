"""Prepared disposable repair; source/oracle tests and runtime proof precede adoption."""
from pathlib import Path
from hashlib import sha256
import re

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PARENT=ROOT/'scripts/cp7_finance_capture/finance_capture.sql'
REPORT='cp7_finance_capture.report_unit(jsonb)'
UNIT='cp7_finance_capture.run_unit(uuid)'
RESULT='cp7_finance_capture.result(uuid)'
CHUNK='cp7_finance_capture.book_chunk(text,date,text,integer,pg_snapshot)'
HELPER='cp7_finance_capture.report_book_diagnostic_v1(date,integer)'


def extract(source,name):
    pattern=r'create function '+re.escape(name)+r'\([^\n]+?\n.*?as \$\$(.*?)\$\$;'
    matches=re.findall(pattern,source,re.S)
    if len(matches)!=1:raise ValueError('CONSISTENT_CAPTURE_PARENT_FUNCTION_REQUIRED:'+name)
    return matches[0]


def once(body,old,new):
    if body.count(old)!=1:raise ValueError('CONSISTENT_CAPTURE_SOURCE_ANCHOR_CHANGED')
    return body.replace(old,new,1)


def derived():
    source=PARENT.read_text()
    original={signature:extract(source,signature.split('(')[0]) for signature in (REPORT,UNIT,RESULT,CHUNK)}
    chunk=re.findall(r'create function cp7_finance_capture.chunk_rows\(\)returns integer language sql immutable set search_path=\'\'as \$\$select (\d+)\$\$;',source)
    if len(chunk)!=1:raise ValueError('CONSISTENT_CAPTURE_CHUNK_POLICY_CHANGED')
    size=int(chunk[0]);assert size>0
    report=once(original[REPORT],'declare r jsonb;snap pg_snapshot;',
        'declare r jsonb;snap pg_snapshot;expected_book text;')
    report=once(report,'begin\n select cp7_finance.workspace(',
        'begin\n with whole as materialized(select cp7_finance_capture.report_book_diagnostic_v1(as_of,'
        +str(size)+') as book)\n select cp7_finance.workspace(')
    old="""  (select count(*)from erp.journal_entries j where j.transaction_date<=as_of),
  (select count(*)from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.transaction_date<=as_of),
  (select count(*)from erp.account_daily_balances b where b.balance_date<=as_of),
  (select count(*)from erp.cash_accounts a)
 into r,snap,n_journal,n_line,n_book,n_cash;"""
    new="""  (whole.book->'rows'->>'journal')::bigint,(whole.book->'rows'->>'line')::bigint,
  (whole.book->'rows'->>'book')::bigint,(whole.book->'rows'->>'cash')::bigint,
  whole.book->>'signature'
 into r,snap,n_journal,n_line,n_book,n_cash,expected_book
 from whole;"""
    report=once(report,old,new)
    report=once(report,"return jsonb_build_object('report',r,'snapshot',snap::text,'read_at',r->>'captured_at',",
        "return jsonb_build_object('report',r,'snapshot',snap::text,'read_at',r->>'captured_at',\n  'expected_book_signature',expected_book,")
    unit=once(original[UNIT],"report_read_at=(r->>'read_at')::timestamptz,",
        "report_book_signature=r->>'expected_book_signature',report_read_at=(r->>'read_at')::timestamptz,")
    unit=once(unit," update cp7_finance_capture.captures set book_signature=sealed,source_hash=",
        " if c.report_book_signature is null or sealed is distinct from c.report_book_signature then\n"
        "  raise exception 'CP7_FINANCE_CAPTURE_SOURCE_CHANGED';\n end if;\n"
        " update cp7_finance_capture.captures set book_signature=sealed,source_hash=")
    result=once(original[RESULT],"case when c.report_snapshot is null then 'ROW_COUNTS'else 'ROW_COUNTS_AND_SNAPSHOT'end",
        "'ROW_COUNTS_AND_REPORT_BOOK_SIGNATURE'")
    return dict(original=original,changed={REPORT:report,UNIT:unit,RESULT:result},chunk_rows=size,
        parent_sha256=sha256(source.encode()).hexdigest())


def row(cur,signature):
    return cur.execute('select p.prosrc,p.provolatile,p.prosecdef,pg_get_userbyid(p.proowner),p.proconfig,pg_get_functiondef(p.oid) '
        'from pg_proc p where p.oid=%s::regprocedure',(signature,)).fetchone()


def install_for_rollback(cur,catalog):
    assert cur.connection.info.host in ('localhost','127.0.0.1') and cur.connection.info.port==54322
    assert cur.execute('select current_database()').fetchone()==('cp6_rollback',)
    import json
    gate=json.loads((HERE/'PREPARED.json').read_bytes())
    if not gate['allow_database_execution']:raise ValueError('CONSISTENT_CAPTURE_NOT_ADMITTED')
    proposal=derived()
    before=catalog._catalog_rows(cur);data=catalog._data(cur)
    live={signature:row(cur,signature) for signature in proposal['original']}
    for signature,body in proposal['original'].items():
        if live[signature][0]!=body:raise ValueError('CONSISTENT_CAPTURE_LIVE_PARENT_CHANGED:'+signature)
    assert live[REPORT][1:4]==('s',True,'cp7_finance_read')
    assert live[CHUNK][1:4]==('s',True,'cp7_finance_read')
    assert live[UNIT][1:4]==('v',False,'cp7_capture')
    assert live[RESULT][1:4]==('s',False,'cp7_capture')
    assert cur.execute('select cp7_finance_capture.chunk_rows()').fetchone()==(proposal['chunk_rows'],)
    assert cur.execute('select count(*)from cp7_finance_capture.captures').fetchone()==(0,)
    assert cur.execute('select count(*)from cp7_finance_capture.chunks').fetchone()==(0,)
    assert cur.execute('select to_regprocedure(%s)',(HELPER,)).fetchone()==(None,)
    cur.execute('alter table cp7_finance_capture.captures add column report_book_signature text '
        "check(report_book_signature is null or report_book_signature~'^[0-9a-f]{64}$')")
    cur.execute((HERE/'book_signature.sql').read_text(),prepare=False)
    for signature,body in proposal['changed'].items():
        original=live[signature]
        definition=once(original[5],original[0],body)
        cur.execute(definition,prepare=False)
        assert row(cur,signature)==(body,*original[1:5],definition)
    assert row(cur,CHUNK)==live[CHUNK]
    assert catalog._data(cur)==data,'DIAGNOSTIC_INSTALL_CHANGED_DATA'
    for role in ('anon','authenticated','service_role','cp7_capture'):
        assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,HELPER)).fetchone()[0]
    return dict(parent_sha256=proposal['parent_sha256'],original_catalog=before,
        original_data=data,chunk_rows=proposal['chunk_rows'],new_private_functions=1,
        new_private_columns=1,changed_private_functions=3,public_rpcs_changed=0,
        Native_money_stock_HPP_definitions_unchanged=True,product_adoption=False,
        full_database_restore_required=True,production_go=False)
