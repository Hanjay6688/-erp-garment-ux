"""Disposable 1,200 commercial SKUs x three physical sizes, using Native writers.

All values below are synthetic test inputs, never proposed factory policy.
The retained BB helper changes the disposable accounting period control before
posting. Its caller must restore the complete preinstall database after use.
This module neither grants access nor supplies an alternate calculation engine.
"""
from collections import defaultdict
from contextlib import contextmanager
from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
import json

import cp7_p19_scale_cases as scale
from cp7_current_model_target_installation import catalog

SKU_COUNT, SIZE_COUNT, VARIANT_COUNT, BATCH_VARIANTS = 1200, 3, 3600, 300
LABEL = 'OW12A_FACTORY_1200X3_SYNTHETIC_NOT_OWNER_POLICY'


def inputs():
    value = deepcopy(scale.SYNTHETIC)
    value.update(label=LABEL, sizes_per_model=SIZE_COUNT,
                 products_per_import_batch=BATCH_VARIANTS,
                 sale_rounds=[dict(days_before_today=2, qty_pcs=3),
                              dict(days_before_today=1, qty_pcs=2)],
                 profile_reason=LABEL, policy_reason=LABEL, sale_reason=LABEL)
    return value


@contextmanager
def synthetic_inputs():
    original = scale.SYNTHETIC
    scale.SYNTHETIC = inputs()
    try:
        yield scale.SYNTHETIC
    finally:
        scale.SYNTHETIC = original


def commercial(cur, today, rows, log, settings):
    """Create current membership through SAVE_GROUPS; never backdate a new SKU."""
    groups = defaultdict(list)
    for row in rows:
        groups[(row['code'], row['model'])].append(row['root'])
    assert len(groups) == SKU_COUNT and all(len(set(v)) == SIZE_COUNT for v in groups.values())
    ordered, skus = list(groups.values()), []
    for start in range(0, len(ordered), scale.SKU_GROUP_PAGE):
        scale.b.api.admin(cur)
        at = cur.execute('select clock_timestamp()').fetchone()[0]
        batch = [scale.bf.group(cur, roots, at,
                 settings=dict(price=None, bom=None, work_rates=[], laundry_rates=[]))
                 for roots in ordered[start:start + scale.SKU_GROUP_PAGE]]
        scale.timed(log, 'commercial_sku_writer', lambda: scale.bf.save(cur, batch, at))
        skus.extend(group['id'] for group in batch)
    return skus


def seed(conn, cur, today, report):
    assert conn.info.host in ('localhost', '127.0.0.1')
    assert cur.execute('select current_database()').fetchone() == ('cp6_rollback',)
    before = scale.current_targets(cur)
    assert len(before) + VARIANT_COUNT <= scale.STAGED_BOUNDS['job_targets']
    log = scale.Phases()
    log.commit = conn.commit
    report.update(status='INCOMPLETE', synthetic_label=LABEL,
                  committed_writer_calls=True, accounting_period_fixture_control=True,
                  complete_preinstall_backup_restore_required=True,
                  requested_commercial_skus=SKU_COUNT, sizes_per_sku=SIZE_COUNT,
                  requested_variants=VARIANT_COUNT, browser_or_Auth_credit=False,
                  owner_policy_claim=False, production_go=False)
    with synthetic_inputs() as settings:
        report['synthetic_inputs'] = deepcopy(settings)
        rows = []
        for _ in range(VARIANT_COUNT // BATCH_VARIANTS):
            rows.extend(scale.import_batch(cur, today, BATCH_VARIANTS, log))
            report['imported_variants'] = len(rows)
        scale.sell(cur, today, rows, log)
        # Historical physical sales belong to their original product identities.
        # A new current commercial group must not rewrite those facts.
        protected = {'erp.sales_headers','erp.sales_items','erp.sale_stock_allocations',
                     'erp.fg_stock_movements','erp.fg_lots','erp.journal_entries',
                     'erp.journal_lines','erp.hpp_versions','erp.hpp_version_components'}
        scale.b.api.admin(cur)
        before_membership = catalog._data(cur)
        assert protected <= set(before_membership)
        skus = commercial(cur, today, rows, log, settings)
        scale.b.api.admin(cur)
        after_membership = catalog._data(cur)
        assert all(before_membership[key] == after_membership[key] for key in protected), 'FACTORY_CURRENT_SKU_REWROTE_POSTED_HISTORY'
        report['current_membership_posted_history_guard'] = dict(
            tables=sorted(protected), all_rows_exact=True, historical_sales_relabelled=False)

        scale.profile(cur, [row['root'] for row in rows], log)
        scale.activate(cur, skus, log)
    scale.b.api.admin(cur)
    assert cur.execute("select(clock_timestamp()at time zone'Asia/Jakarta')::date").fetchone()[0] == today
    roots = [row['root'] for row in rows]
    assert len(roots) == len(set(roots)) == VARIANT_COUNT
    members = cur.execute("""select m.product_root::text,v.sku_id::text,p.size_id::text,
        (select count(*)from erp.bf_sku_members_v1 z where z.version_id=v.id)
        from erp.products p
        join erp.bf_sku_versions_v1 v on v.id=erp.bf_version_at_v1(p.id,clock_timestamp())
        join erp.bf_sku_members_v1 m on m.version_id=v.id and m.product_root=p.id
        where p.id=any(%s::uuid[]) order by m.product_root""", (roots,)).fetchall()
    observed = defaultdict(set)
    assert {r[0] for r in members} == set(roots) and len(members) == VARIANT_COUNT
    for root, sku, size, count in members:
        assert count == SIZE_COUNT
        observed[sku].add(size)
    assert set(observed) == set(skus) and all(len(sizes) == SIZE_COUNT for sizes in observed.values())
    stock = cur.execute("""select product_id::text,sum(qty_signed)
        from erp.fg_stock_movements where product_id=any(%s::uuid[])
        group by product_id order by product_id""", ([r['product'] for r in rows],)).fetchall()
    expected_pcs = Decimal(settings['opening_fg_pcs']) - sum(Decimal(s['qty_pcs']) for s in settings['sale_rounds'])
    assert len(stock) == VARIANT_COUNT and all(qty == expected_pcs for _, qty in stock)
    after = scale.current_targets(cur)
    targets = sorted(row['target'] for row in rows)
    assert len(after) == len(before) + VARIANT_COUNT and set(before) <= set(after)
    assert set(targets) == set(after) - set(before)
    report.update(status='PASS', commercial_skus=len(observed), variants=len(rows),
                  preexisting_targets=len(before), total_targets=len(after),
                  target_keys=targets, all_current_target_keys=after,
                  target_keys_sha256=sha256('\n'.join(targets).encode()).hexdigest(),
                  sku_size_membership_sha256=sha256(json.dumps(members).encode()).hexdigest(),
                  physical_pcs_per_variant=str(expected_pcs), every_variant_stock_exact=True,
                  current_native_membership_verified=True, historical_sales_precede_current_membership=True, writer_phases=dict(log),
                  synthetic_module_binding_restored=True)
    conn.commit()
    return report


def coverage(original, pages, fixture):
    """Require every current target and every factory variant, without sampling."""
    expected = fixture['all_current_target_keys']
    labels = [row['target_key'] for row in original['product_labels']]
    analysis = original['analysis']
    result = scale.coverage(labels, [row['target']['key'] for row in analysis['recommendations']],
                            analysis['generation_warnings'], analysis['status'], expected)
    assert result['complete'] and pages['targets_total'] == len(expected)
    assert set(fixture['target_keys']) <= set(labels)
    assert analysis['snapshot']['capture_complete'] is True
    assert analysis['quality']['quantity'] == 'COMPLETE'
    # A global BLOCKED result does not qualify the factory cohort as analysed.
    assert analysis['status'] != 'BLOCKED', ('FACTORY_ANALYSIS_BLOCKED', analysis['generation_warnings'])
    return dict(result, factory_variants=VARIANT_COUNT, all_pages_verified=True,
                factory_target_keys_sha256=fixture['target_keys_sha256'])
