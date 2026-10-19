"""R5-02 (owner D17-2, Sol/Fable/Astra KNOWN-P19-DIRECT-LATENCY): account lookups once per query in the report readers.

Function counters of one direct capture with financial figures at 100 targets (qualification run 39173212515 of r4):
4.56 s server time, of which erp.account_id(text) 30,974 calls, 2.48 s with its guard. The owner report and the period
readiness it carries run the Native check readers (run_v268, run_v267, the HPP books, the opening and pocket checks), and
these compare every journal line with `erp.account_id('<KEY>')` written inline in the filter, so the mapping lookup and
its guard run once per row; the report is read twice per capture (capture, then the delivery re-check of `serve`).

Each of the eleven readers below is STABLE (it cannot write, and PostgreSQL may evaluate a STABLE call with constant
arguments once per scan); erp.account_id(text) is STABLE as well. In each, every inline `erp.account_id('<KEY>')` with a
literal key becomes `(select erp.account_id('<KEY>'))`, an uncorrelated scalar subquery that PostgreSQL evaluates once
per query when it is first needed and then reuses. Same mapping row, same guard; no number, filter or check changes.
Calls with a non-literal key stay as they are. Writers are not touched.

One difference exists only when a key has no mapping: the planner evaluates an inline STABLE call with constant
arguments while estimating, so the old text refuses ('Accounting mapping % is not configured') even when no row reaches
the filter, while an init plan refuses only when a row needs the value (writer-local PG16, scratchpad r5). Every key the
readers use is a core mapping (erp.expected_mapping_account_type), and erp.guard_accounting_mapping_semantics() refuses
to delete or rename a core mapping, so install refuses unless every one of these keys is mapped; after that the missing
key cannot occur.

Install: one hash-free anchor check per reader (the literal call count the Native text and the earlier CP7 deltas leave
in place), then the same regular-expression rewrite in SQL; uninstall restores every reader through the replayed
`originals` (two of them, the owner report and run_v267, are already captured by the note-report and kasbon deltas, which
this delta follows).
"""
import re

# signature -> literal erp.account_id('<KEY>') calls in the definition this delta finds installed.
READERS = {
    'erp._v268_financial_report_checks_pre_scope()': 2,
    'erp.bb_opening_credit_account_v1(uuid)': 6,
    'erp.compute_non_po_product_hpp_book_v2620f(uuid)': 4,
    'erp.compute_po_hpp_gl_book_v2620e(uuid)': 8,
    'erp.get_owner_financial_snapshot_v2(date,date,date)': 11,
    'erp.initial_prepayment_checks_v1()': 5,
    'erp.pocket_fabric_checks_v1()': 2,
    'erp.pocket_period_book_v1(uuid)': 4,
    'erp.run_v267_financial_truth_checks()': 7,
    'erp.run_v268_financial_report_checks()': 14,
    'erp.sale_lifecycle_po_hpp_amount_v2620d(uuid,uuid)': 6,
}
# Every literal key the readers use; all are core mappings (erp.expected_mapping_account_type is not null).
KEYS = ('AP_SUPPLIER', 'AP_VENDOR', 'AR_CUSTOMER', 'CASH', 'COGS', 'CONTRACTOR_PAYABLE', 'CONTRACTOR_RECEIVABLE', 'FG_INVENTORY',
        'GRNI_MATERIAL', 'MATERIAL_INVENTORY', 'MATERIAL_PURCHASE_VARIANCE', 'MATERIAL_RECOVERY', 'OPENING_EQUITY', 'OTHER_EXPENSE',
        'OTHER_INCOME', 'SALES_REVENUE', 'WIP')
CALL = re.compile(r"erp\.account_id\('([A-Z0-9_]+)'\)")
WRAPPED = re.compile(r"\(select erp\.account_id\('([A-Z0-9_]+)'\)\)")
SQL_CALL = r"erp\.account_id\('([A-Z0-9_]+)'\)"
SQL_WRAPPED = r"(select erp.account_id('\1'))"


def wrap(signature, definition):
    assert not WRAPPED.search(definition), ('R5_02_READER_ALREADY_WRAPPED', signature)
    assert re.search(r'(?im)^\s*(stable|immutable)\b|\bLANGUAGE \w+\s+(STABLE|IMMUTABLE)\b', definition), ('R5_02_READER_NOT_STABLE', signature)
    assert set(CALL.findall(definition)) <= set(KEYS), ('R5_02_READER_KEY_NOT_LISTED', signature)
    changed, n = CALL.subn(lambda m: "(select erp.account_id('%s'))" % m.group(1), definition)
    assert n == READERS[signature], ('R5_02_READER_SOURCE_CHANGED', signature, n, READERS[signature])
    return changed


def unwrap(signature, definition):
    """The installed reader as it was before this delta (the CP17 case runs both side by side)."""
    original, n = WRAPPED.subn(lambda m: "erp.account_id('%s')" % m.group(1), definition)
    assert n == READERS[signature] and not CALL.search(definition.replace("(select erp.account_id(", "")), ('R5_02_READER_NOT_WRAPPED', signature, n)
    return original


def capture(cur, originals):
    # The owner report and run_v267 are captured by the note-report and kasbon deltas, installed before this one.
    for signature in READERS:
        if signature not in originals:
            originals[signature] = cur.execute('select pg_get_functiondef(%s::regprocedure)', (signature,)).fetchone()[0]


def expected_definitions(expected, originals):
    """`expected` holds the definitions the earlier deltas leave; this delta wraps those (or the Native original)."""
    return {s: wrap(s, expected.get(s, originals[s])) for s in READERS}


def block(signature):
    """The install step of one reader: refuse unless its literal calls are exactly the expected ones, then rewrite."""
    return ("do $r5_02$\ndeclare definition text;\nbegin\n"
            " definition:=pg_get_functiondef('" + signature + "'::regprocedure);\n"
            " if position('(select erp.account_id(' in definition)>0\n"
            "  or (select count(*) from regexp_matches(definition,$c$" + SQL_CALL + "$c$,'g'))<>" + str(READERS[signature]) + " then\n"
            "  raise exception 'CP7_R5_02_READER_SOURCE_CHANGED: %','" + signature + "';end if;\n"
            " execute regexp_replace(definition,$c$" + SQL_CALL + "$c$,$w$" + SQL_WRAPPED + "$w$,'g');\n"
            "end $r5_02$;\n")


def extension():
    blocks = [block(signature) for signature in READERS]
    keys = ','.join("'" + k + "'" for k in KEYS)
    precondition = ("do $r5_02_keys$\nbegin\n"
                    " if exists(select 1 from unnest(array[" + keys + "]::text[]) k\n"
                    "  where erp.expected_mapping_account_type(k) is null\n"
                    "   or not exists(select 1 from erp.accounting_account_mappings m where m.mapping_key=k and m.account_id is not null)) then\n"
                    "  raise exception 'CP7_R5_02_ACCOUNT_MAPPING_MISSING';end if;\nend $r5_02_keys$;\n")
    return ('-- R5-02: account lookups once per query in the report readers (cp7_report_accounts_bundle.py).\n'
            + precondition + ''.join(blocks))


def verify(cur):
    for signature in READERS:
        definition = cur.execute('select pg_get_functiondef(%s::regprocedure)', (signature,)).fetchone()[0]
        assert wrap(signature, unwrap(signature, definition)) == definition, ('R5_02_READER_NOT_PATCHED', signature)
    missing = cur.execute('select k from unnest(%s::text[]) k where erp.expected_mapping_account_type(k) is null'
                          ' or not exists(select 1 from erp.accounting_account_mappings m where m.mapping_key=k and m.account_id is not null)',
                          (list(KEYS),)).fetchall()
    assert not missing, ('R5_02_ACCOUNT_MAPPING_MISSING', missing)
    return dict(stage='R5_02_REPORT_READERS_ACCOUNT_LOOKUP_ONCE', readers=len(READERS), core_keys=len(KEYS))
