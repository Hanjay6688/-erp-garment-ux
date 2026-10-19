"""Versioned repair of Sol's invoice readback, using unchanged Native fixtures.

The BD document owns DRAFT. The core payable is created at POST. Observation is
SELECT-only; original business fixtures, temporary ACL lease, and amounts stay
as declared in the first execution. No failed case is silently relabelled.
"""
from datetime import date
from decimal import Decimal
import json
import os
import sys
from urllib.parse import urlparse

import journey_fixture as original
import psycopg

c = original.c


def invoice_rows(document_rows, core_rows):
    """Strict pure binding control: one document ID and equal amount after POST."""
    documents = {r[0]: r for r in document_rows}
    cores = {r[0]: r for r in core_rows}
    assert len(documents) == len(document_rows) and len(cores) == len(core_rows), 'SOL_Q2_DUPLICATE_INVOICE_ID'
    assert set(cores) <= set(documents), 'SOL_Q2_CORE_WITHOUT_DOCUMENT'
    for ident, document in documents.items():
        assert len(document) == 4 and document[2] in ('DRAFT', 'POSTED', 'REVERSED', 'CANCELLED')
        if document[2] in ('DRAFT', 'CANCELLED'):
            assert ident not in cores, 'SOL_Q2_CORE_BEFORE_DOCUMENT_POST'
        elif document[2] in ('POSTED', 'REVERSED'):
            core = cores.get(ident)
            assert core is not None, 'SOL_Q2_POSTED_DOCUMENT_WITHOUT_CORE'
            allowed = ('POSTED', 'PARTIAL_PAID', 'PAID') if document[2] == 'POSTED' else ('REVERSED',)
            assert core[1] == document[1] and core[2] in allowed, 'SOL_Q2_CORE_DOCUMENT_IDENTITY_STATUS'
            assert Decimal(core[3]) == Decimal(document[3]), 'SOL_Q2_CORE_DOCUMENT_AMOUNT'
    return document_rows


def observe(cur, p):
    out = original.observe(cur, p)
    c.b.api.admin(cur)
    core = out['invoices']
    documents = [list(row) for row in cur.execute(
        'select id::text,invoice_number,status,header_total::text '
        'from erp.bd_laundry_invoices_v1 where vendor_id=%s order by id',
        (p['vendor'],)).fetchall()]
    out['native_invoices'] = core
    out['invoices'] = invoice_rows(documents, core)
    out['invoice_observation'] = dict(document_table='erp.bd_laundry_invoices_v1',
        amount_column='header_total', payable_table='erp.vendor_invoices',
        payable_amount_column='total_amount', exact_id_status_and_amount_binding=True,
        status_mapping='BD POSTED -> core POSTED/PARTIAL_PAID/PAID; BD REVERSED -> core REVERSED; DRAFT/CANCELLED -> no core')
    return out


def main():
    target = os.environ['AUDITOR_BROWSER_DB_URL']
    parsed = urlparse(target)
    assert parsed.hostname in ('localhost', '127.0.0.1') and parsed.path == '/cp6_auditor_browser', 'SOL_Q2_LOOPBACK_BROWSER_ONLY'
    p = json.load(sys.stdin)
    operation = sys.argv[1]
    assert operation in ('prepare', 'observe', 'claim_prepare', 'claim_observe')
    with psycopg.connect(target) as conn, conn.cursor() as cur:
        # Same lease as both originals; no additional EXECUTE or product grant.
        acl = cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        had = cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        if not had:
            cur.execute('grant usage on schema erp to authenticated')
        if operation in ('prepare', 'claim_prepare'):
            result = original.prepare(cur, date.fromisoformat(p['today']))
            if operation == 'claim_prepare':
                result.update(today=p['today'], claim_number='SOLR4-CL-' + result['po'][:12])
        else:
            result = observe(cur, p)
            if operation == 'claim_observe':
                c.b.api.admin(cur)
                result['claims'] = [list(row) for row in cur.execute(
                    'select id::text,claim_number,status,compensation_amount::text,resolution_date::text '
                    'from erp.laundry_claims where claim_number=%s order by id',
                    (p['claim_number'],)).fetchall()]
        c.b.api.admin(cur)
        if not had:
            cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0] == acl
        conn.commit()
    print(json.dumps(result, default=str))


if __name__ == '__main__':
    main()
