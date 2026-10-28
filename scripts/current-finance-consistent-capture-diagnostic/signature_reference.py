"""Independent direct-table oracle; never calls the candidate or book_chunk."""
from hashlib import sha256
from psycopg.pq import TransactionStatus

QUERIES={
 'journal':"select 'journal:'||j.id||':'||encode(sha256(convert_to(to_jsonb(j)::text,'UTF8')),'hex')from erp.journal_entries j where j.transaction_date<=%s::date order by j.id",
 'line':"select 'line:'||l.id||':'||encode(sha256(convert_to(to_jsonb(l)::text,'UTF8')),'hex')from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.transaction_date<=%s::date order by l.id",
 'book':"select 'book:'||b.account_id||':'||b.balance_date||':'||encode(sha256(convert_to(to_jsonb(b)::text,'UTF8')),'hex')from erp.account_daily_balances b where b.balance_date<=%s::date order by b.account_id,b.balance_date",
 'cash':"select 'cash:'||a.id||':'||encode(sha256(convert_to(to_jsonb(a)::text,'UTF8')),'hex')from erp.cash_accounts a order by a.id"
}


def signature(cur,as_of,chunk_size):
    assert type(chunk_size)is int and chunk_size>0
    zone=cur.execute('show TimeZone').fetchone()[0]
    cur.execute("select set_config('TimeZone','UTC',true)")
    try:
        pieces=[];counts={};unit=1
        for family,query in QUERIES.items():
            rows=[r[0]for r in cur.execute(query,()if family=='cash'else(as_of,)).fetchall()]
            counts[family]=len(rows)
            for start in range(0,len(rows),chunk_size):
                chunk=rows[start:start+chunk_size]
                pieces.append(f'{family}:{unit}:{len(chunk)}:'+sha256('\n'.join(chunk).encode()).hexdigest())
                unit+=1
        return dict(rows=counts,signature=sha256('\n'.join(pieces).encode()).hexdigest(),chunks=unit-1)
    finally:
        if cur.connection.info.transaction_status!=TransactionStatus.INERROR:
            cur.execute("select set_config('TimeZone',%s,true)",(zone,))
