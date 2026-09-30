"""X04 continuations across inherited writers and the CP7 FG/report readers.

The existing independent-worksheet amounts remain fixed. No SKU laundry price
is introduced, and a legal free laundry service does not make estimated cloth
or another missing HPP component final. Fixtures are disposable only.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
import cp6_bd_revision_cases as revision
import cp6_bf_combined_probe as combined
import cp7_fg_cases as fg
import cp7_finance_cases as finance

b = combined.b


def differences(expected, actual, path=''):
    if isinstance(expected, dict) and isinstance(actual, dict):
        return [d for key in sorted(set(expected)|set(actual))
                for d in differences(expected.get(key), actual.get(key), path+'.'+key)]
    if isinstance(expected, list) and isinstance(actual, list) and len(expected)==len(actual):
        return [d for i, (left, right) in enumerate(zip(expected, actual))
                for d in differences(left, right, path+'.'+str(i))]
    return [] if expected==actual else [dict(path=path, expected=expected, actual=actual)]



def canonical_card(value):
    """Compare exact instants across WIB/UTC without rounding microseconds."""
    if isinstance(value, list):
        return [canonical_card(child) for child in value]
    if isinstance(value, dict):
        result = {}
        for key, child in value.items():
            if key in ('physical_at', 'recorded_at') and child is not None:
                parsed = datetime.fromisoformat(child)
                assert parsed.utcoffset() is not None, ('X04_NAIVE_TIMESTAMP', key, child)
                result[key] = parsed.astimezone(timezone.utc).isoformat(timespec='microseconds')
            else:
                result[key] = canonical_card(child)
        return result
    return value


def reports(cur, today):
    snapshot = finance.read(cur, today, **{'from': str(today-timedelta(days=14))})['snapshot']
    position, performance = snapshot['financial_position'], snapshot['performance']
    return dict(WIP=D(position['wip_inventory']),
                FG_INVENTORY=D(position['fg_inventory']),
                COGS=D(performance['cogs_gl']))


def new_positions(cur, before):
    return cur.execute("""select distinct l.id::text,l.product_id::text,p.sku,
        m.location_id::text,m.quality_grade::text
        from erp.fg_lots l join erp.products p on p.id=l.product_id
        join erp.fg_stock_movements m on m.lot_id=l.id
        where not(l.id=any(%s::uuid[])) order by 1,4,5""", (before,)).fetchall()


def projections(cur, positions):
    observations = []
    for lot, product, sku, location, grade in positions:
        f = dict(lot=lot, product=product, sku=sku, location=location)
        workspace = fg.workspace(cur, f, show_zero=True, limit=100)
        rows = [r for r in workspace['page']['rows'] if r['lot_id']==lot
                and r['location_id']==location and r['quality_grade']==grade]
        assert len(rows)==1, ('X04_POSITION_MISSING', f, workspace)
        row = rows[0]
        assert grade=='GRADE_A', ('X04_DECLARED_GOOD_SOURCE', grade)
        card = fg.ledger(cur, f, limit=100)
        physical = b.one(cur, """select coalesce(sum(qty_signed),0) from erp.fg_stock_movements
            where lot_id=%s and location_id=%s and quality_grade=%s""", lot, location, grade)
        # These cases end without an open sale reservation. Core helpers assert
        # the independent fixed quantities/costs; these checks bind CP7 readers.
        assert D(row['physical_qty'])==physical and D(row['available_qty'])==physical
        assert D(row['reserved_qty'])==0 and D(card['balances']['physical_qty'])==physical
        pending_laundry = b.one(cur, 'select erp.bd_lot_laundry_unknown_v1(%s)', lot)
        if pending_laundry:
            assert row['valuation']['state']=='UNKNOWN' and row['valuation']['value'] is None
            assert row['valuation']['unit_cost'] is None
        if row['valuation']['state']=='KNOWN' and physical>0:
            assert D(row['valuation']['unit_cost'])>0, ('X04_FREE_IS_NOT_ZERO_WHOLE_HPP', row)
        assert card['page']['next_offset'] is None
        native_groups = dict(cur.execute("""select id::text,
            erp.bf_commercial_sku_at_v1(product_id,physical_at)
            from erp.fg_stock_movements where lot_id=%s and location_id=%s and quality_grade=%s""",
            (lot, location, grade)).fetchall())
        assert {r['id']: r['commercial_sku_at_transaction'] for r in card['page']['rows']}==native_groups
        observations.append(dict(product=product, sku=sku, lot=lot, location=location,
                                 grade=grade, row=row, card=card,
                                 pending_laundry=pending_laundry))
    assert observations, 'X04_SOURCE_MUST_CREATE_ACTUAL_FG'
    return observations


def pinned_po(cur, today, mismatch=False):
    # A timezone spelling is equivalent; a one-microsecond or money change is not.
    wib = dict(physical_at='2026-09-30T09:00:00.123456+07:00', amount='1.00')
    utc = dict(physical_at='2026-09-30T02:00:00.123456+00:00', amount='1.00')
    assert canonical_card(wib)==canonical_card(utc)
    assert canonical_card(wib)!=canonical_card(dict(utc, physical_at='2026-09-30T02:00:00.123457+00:00'))
    assert canonical_card(wib)!=canonical_card(dict(utc, amount='1.01'))
    f = combined.fixture(cur, today, True)
    wash = combined.wash(cur, f, range(4), 11)
    combined.finish(cur, f, [wash], range(3), 13, partial=True)
    old_lots = combined.lots(cur, f)[:3]
    old_values = [b.lot_value(cur, lot) for lot in old_lots]
    cards = [fg.ledger(cur, dict(product=p, lot=lot, location=combined.base.LOCATION))
             for p, lot in zip(f['roots'][:3], old_lots)]
    combined.move34(cur, f, 14, changed_recipe=mismatch)
    if mismatch:
        refusal = b.refused(cur, lambda: combined.finish(cur, f, [wash], [3], 15), 'BF_PO_NEW_MEMBER')
        assert refusal['ok'], refusal
        assert combined.lots(cur, f)[3] is None
        expected = [5, 8, 3]
    else:
        combined.finish(cur, f, [wash], [3], 15)
        lot = combined.lots(cur, f)[3]
        recipe = b.one(cur, """select erp.bf_recipe_basis_v1(bom_version_id)
            from erp.po_accessory_bom_commitments where po_id=%s and product_id=%s""", f['po'], f['roots'][3])
        assert recipe[0]['qty']==1 and D(str(recipe[0]['standard']))==D('3.17'), recipe
        assert b.one(cur, 'select version_id::text from erp.bf_po_boms_v1 where po_id=%s and sku_id=%s',
                     f['po'], f['a']['id'])==f['versions'][f['a']['id']]
        assert b.one(cur, "select erp.cp6_lot_work_cost_v2620c(%s,'LABOR')", lot)==120
        expected = [5, 8, 3, 4]
    assert [b.lot_value(cur, lot) for lot in old_lots]==old_values
    assert [combined.stock(cur, lot) for lot in combined.lots(cur, f) if lot] == expected
    serialization_differences = []
    for product, lot, before in zip(f['roots'][:3], old_lots, cards):
        after = fg.ledger(cur, dict(product=product, lot=lot, location=combined.base.LOCATION))
        serialization_differences.extend(differences(before['page']['rows'], after['page']['rows']))
        assert canonical_card(after['page']['rows'])==canonical_card(before['page']['rows']), dict(
            code='X04_OLD_CARD_COMPARISON', differences=differences(before['page']['rows'], after['page']['rows']),
            hpp_completeness=b.one(cur, 'select to_jsonb(x) from erp.get_hpp_completeness(%s) x', f['po']))
        assert after['balances']==before['balances']
    return dict(status='PASS',recipe_mismatch=mismatch,physical=expected,
                original_cards_and_values_immutable=True,
                exact_instant_comparison=True, serialization_differences=serialization_differences,
                original_pin_and_work_basis=True if not mismatch else 'REFUSED_BEFORE_NEW_LOT')


def continuation(cur, today, operation):
    before_lots = [r[0] for r in cur.execute('select id::text from erp.fg_lots').fetchall()]
    before_report, before_books = reports(cur, today), combined.books(cur)
    result = operation(cur, today)
    assert result.get('status') in ('PASS', 'FAIL', 'INCOMPLETE', 'COUNTEREXAMPLE'), result
    after_report, after_books = reports(cur, today), combined.books(cur)
    delta = {k: after_report[k]-before_report[k] for k in before_report}
    assert delta == {k: after_books[k]-before_books[k] for k in before_books}, (delta, before_books, after_books)
    observed = projections(cur, new_positions(cur, before_lots))
    return dict(result, cp7_report_matches_source_GL_delta=delta,
                cp7_fg_and_cards=observed, full_X04_acceptance=False,
                production_go=False, independent_acceptance=False)


def free(cur, today):
    return revision.free_path(b, cur, b.case_day(today))


def cases(cur, today):
    operations = [
        ('VENDOR_FREE_WAIVED', free),
        ('PO_PIN_COMPATIBLE', pinned_po),
        ('PO_PIN_MISMATCH_REFUSED', lambda c, d: pinned_po(c, d, True)),
        ('REWORK_OLD_CONTRACTOR', lambda c, d: combined.range_rework(c, d, True, False)),
        ('REWORK_NEW_CONTRACTOR', lambda c, d: combined.range_rework(c, d, True, True)),
        ('MOVED_RANGE_PENDING_INVOICE_RETURN', lambda c, d: combined.late_invoice_return(c, d, True)),
    ]
    return [('F03_X04_'+name, lambda operation=op: continuation(cur, today, operation))
            for name, op in operations]


def http_cases(http, today):
    def pin():
        owner = http.login('OWNER', 'x04-pinned-po')
        with http.connect() as conn, conn.cursor() as cur:
            # Restore the disposable legacy DRAFT setup grant before HTTP.
            had = cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
            acl = cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
            if not had: cur.execute('grant usage on schema erp to authenticated')
            source = continuation(cur, today, pinned_po)
            assert source['status']=='PASS', source
            b.api.admin(cur)
            if not had: cur.execute('revoke usage on schema erp from authenticated')
            assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
            report = finance.read(cur, today, **{'from': str(today-timedelta(days=14))})
            conn.commit()
        serialization_differences = []
        for observation in source['cp7_fg_and_cards']:
            query = dict(product_id=observation['product'], lot_id=observation['lot'],
                         location_id=observation['location'], quality_grade=observation['grade'], limit=100)
            response = owner.rpc('erp_cp7_get_fg_ledger_v1', dict(p_query=query))
            assert response['status']==200, response
            serialization_differences.extend(differences(observation['card']['page'], response['body']['page']))
            assert canonical_card(response['body']['page'])==canonical_card(observation['card']['page']), dict(
                code='X04_HTTP_CARD_COMPARISON', differences=differences(observation['card']['page'], response['body']['page']))
            assert response['body']['balances']==observation['card']['balances'], dict(
                code='X04_HTTP_BALANCE_COMPARISON', differences=differences(observation['card']['balances'], response['body']['balances']))
        query = finance.query(today, **{'from': str(today-timedelta(days=14))})
        response = owner.rpc('erp_cp7_get_finance_report_v1', dict(p_query=query))
        assert response['status']==200, response
        for section in ('financial_position', 'performance'):
            assert response['body']['snapshot'][section]==report['snapshot'][section]
        assert http.anon_rpc('erp_cp7_get_finance_report_v1', dict(p_query=query))['status'] in (401,403)
        return dict(status='PASS', real_Auth_HTTP=True, native_source=source,
                    no_legacy_schema_grant_during_HTTP=True, product_and_report_readers_agree=True,
                    exact_instant_comparison=True, serialization_differences=serialization_differences)
    return [('F03_X04_HTTP_PINNED_PO_FG_REPORT', pin)]
