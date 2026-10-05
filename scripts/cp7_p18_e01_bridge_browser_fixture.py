"""Only accepted E01 Native controls on the isolated browser database."""
from datetime import date
from copy import deepcopy
from urllib.parse import urlparse
import contextlib
import io
import hashlib
import json
import os
import sys

import psycopg
import cp7_p18_e01_bridge_cases as cases
import cp7_identity_cases as policies
import cp6_bf_probe as commercial


def select_stock_target(cur, f):
    """An explicit disposable scenario on the actual E01 sold physical root.

    Never seed a recommendation or relabel an unreviewed policy. Preserve
    Native economic settings and posted E01 facts, then use public Native
    commercial-master/policy/profile commands before freezing the browser run.
    Comparison roots, capacity and material installation remain unreviewed.
    """
    cases.b.api.admin(cur)
    rows=cur.execute('select distinct p.identity_root_id::text,p.size_id::text,p.model_id::text '
                     'from erp.sales_items i join erp.products p on p.id=i.product_id where i.sale_id=%s',
                     (f['sale'],)).fetchall()
    assert len(rows)==1,('P18_E01_EXACT_SOLD_ROOT_REQUIRED',rows)
    root,size,model=rows[0]
    at=cur.execute('select clock_timestamp()').fetchone()[0]
    basis=cur.execute('select erp.bf_legacy_basis_v1(%s::uuid[],%s)',([root],at)).fetchone()[0]
    assert len(basis)==1 and basis[0]['product_root']==root
    existing=cur.execute('select s.id::text,v.settings from erp.bf_sku_members_v1 m '
                         'join erp.bf_sku_versions_v1 v on v.id=m.version_id '
                         'join erp.bf_skus_v1 s on s.id=v.sku_id '
                         'where m.product_root=%s and v.effective_to is null',(root,)).fetchall()
    if existing:
        assert len(existing)==1
        sku,settings=existing[0]
    else:
        rates=[dict(contractor_id=str(contractor),work_component_id=str(component),rate=str(rate))
               for contractor,component,rate in cur.execute('select contractor_id,work_component_id,rate_per_pcs '
                   'from erp.contractor_work_rates where model_id=%s and effective_from<=%s '
                   'and(effective_to is null or effective_to>%s) order by contractor_id,work_component_id,id',
                   (model,at,at)).fetchall()]
        assert rates, 'P18_E01_NATIVE_WORK_RATE_REQUIRED'
        settings=dict(price=basis[0]['price'],bom=deepcopy(basis[0]['bom']),work_rates=rates,
                      laundry_rates=[])
        # Laundry is vendor-authoritative under the unchanged Native contract.
        # An empty SKU override does not replace any vendor rate or old charge.
        g=commercial.group(cur,[root],at,settings=settings)
        commercial.save(cur,[g],at);sku=g['id']
    current=cur.execute('select erp.bf_legacy_basis_v1(%s::uuid[],%s)',([root],at)).fetchone()[0]
    assert current[0]['price']==basis[0]['price'] and current[0]['bom']==basis[0]['bom'],(current,basis)
    selected=policies.get(cur,[sku])['rows']
    assert len(selected)==1 and selected[0]['sku_id']==sku
    policies.apply(cur,[policies.proposal(selected[0],'ACTIVE')])
    baseline=cases.analysis.previous.baseline
    row=baseline.get(cur,[root])['rows'][0]
    baseline.save(cur,dict(root_id=root,product_version_id=row['product_version_id'],expected_revision=row['revision'],
        reason='P18 disposable explicit forecast scenario: actual E01 root, selected mean10 L3 R7 B0; no factory defaults',
        config=dict(mean_mode='SELECTED_MANUAL',daily_pcs='10',minimum_available_days='20',
                    lead_days='3',review_days='7',buffer_days='0')))
    cases.literal(cur,f,'175.00')
    f.update(target_root=root,target_size=size,selected_stock_scenario=dict(commercial_sku_id=sku,
        Native_economic_settings=deepcopy(settings),forecast_assumption='SELECTED_MEAN10_L3_R7_B0_TARGET100',
        other_roots_reactivated=False,capacity_or_installed_material_assumption=False))


def main():
    target = os.environ['AUDITOR_BROWSER_DB_URL']
    url = urlparse(target)
    assert url.hostname in ('localhost', '127.0.0.1') and url.path == '/cp6_auditor_browser', 'DISPOSABLE_BROWSER_ONLY'
    operation, payload = sys.argv[1], json.load(sys.stdin)
    with psycopg.connect(target) as conn, conn.cursor() as cur:
        had = cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        acl = cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        if not had:
            cur.execute('grant usage on schema erp to authenticated')
        if operation == 'prepare':
            # The worksheet prints checkpoints; retain them inside the returned
            # trace without corrupting the fixture's one JSON response.
            with contextlib.redirect_stdout(io.StringIO()):
                fixture, trace = cases.prepare(cur, date.fromisoformat(payload['today']))
            select_stock_target(cur, fixture)
            result = dict(fixture=fixture, trace=trace)
        elif operation == 'inverse':
            result = cases.inverse(cur, payload['fixture'])
            cases.literal(cur, payload['fixture'], '375.00')
        elif operation in ('deactivate', 'restore'):
            cur.execute('update erp.app_users set is_active=%s where auth_user_id=%s',
                        (operation == 'restore', payload['actor']))
            result = dict(status='PASS')
        elif operation == 'state':
            f = payload['fixture']
            detail = cases.worksheet.source.read(cur, f)['detail']
            result = dict(physical=cases.worksheet.physical(cur, f), financial=detail['financial'],
                          analysis_count=cur.execute('select count(*) from cp7_analysis_native.runs where actor=%s',
                                                     (payload['actor'],)).fetchone()[0],
                          appendix_count=cur.execute('select count(*) from cp7_reminder_native.obligation_reports where actor=%s',
                                                     (payload['actor'],)).fetchone()[0])
            cases.b.api.admin(cur)
            snapshot = cases.b.boundary.snapshot(cur)
            result['operational_boundary_sha256'] = hashlib.sha256(
                json.dumps(snapshot, sort_keys=True, separators=(',', ':'),
                           default=str).encode()).hexdigest()
        else:
            raise ValueError('UNKNOWN_E01_BRIDGE_FIXTURE_ACTION')
        cases.b.api.admin(cur)
        if not had:
            cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0] == acl
        conn.commit()
    print(json.dumps(result, default=str))


if __name__ == '__main__':
    main()
