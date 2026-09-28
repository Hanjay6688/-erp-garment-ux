"""P02 native source-capture spike on the unchanged accepted CP6 package.

Only isolated cp6_rollback. A single read-only SELECT captures six bounded
source collections. Native fixtures roll back; no operational connection,
actor-facing facade, persistence or planner result is claimed.
"""
from pathlib import Path
from datetime import timedelta
import json
import uuid

import psycopg

ROOT = Path(__file__).resolve().parents[1]
SQL = (ROOT/'scripts/cp7-src/snapshot/capture_probe.sql').read_text()


def capture(cur, root):
    return cur.execute(SQL, (root,), prepare=False).fetchone()[0]


def read_only_missing(url):
    # Repeat the P00 target guard before opening an isolated read-only session.
    from psycopg.conninfo import conninfo_to_dict
    info = conninfo_to_dict(url)
    assert info.get('dbname') == 'cp6_rollback' and info.get('host') in ('127.0.0.1', 'localhost')
    with psycopg.connect(url) as conn, conn.cursor() as cur:
        conn.read_only = True
        conn.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
        result = capture(cur, uuid.uuid4())
        assert result['status'] == 'INCOMPLETE' and result['counts']['physical'] == 0
        assert result['sources']['lot_cost'] == []
        assert cur.execute("select current_setting('transaction_read_only')").fetchone()[0] == 'on'
        conn.rollback()
    return dict(status='PASS',missing_root='INCOMPLETE',read_only_transaction=True)


def cases(cur, today):
    import cp6_bf_probe as bf
    from cp6_bd_probe import two_size_fixture
    b, base = bf.b, bf.b.chain.base

    def filled():
        b.api.admin(cur)
        (root, size), = bf.products(cur, ('31',), tag='CP7-P02-'+uuid.uuid4().hex[:8])
        a = two_size_fixture(cur, bf.b.case_day(today), 'CP7-P02-A',
            size_quantities=[(size, 6), (base.SIZE, 4)])
        z = two_size_fixture(cur, bf.b.case_day(today), 'CP7-P02-B',
            size_quantities=[(size, 7), (base.SIZE, 3)])
        b.api.admin(cur)
        now = cur.execute('select clock_timestamp()').fetchone()[0]
        customer = base.create_customer(cur, 'P02-'+uuid.uuid4().hex[:8])
        lot, sale = uuid.uuid4(), uuid.uuid4()
        # Administrative fixture: prove the reader on a stock+draft+pending-
        # cost combination. These inserts are rolled back by strict_group.
        # The CP6 business command oracles are tested in their own family.
        cur.execute('set local session_replication_role=replica')
        try:
            cur.execute("""insert into erp.fg_lots(id,lot_number,product_id,initial_qty_pcs,cached_qty_pcs,produced_at,lot_origin)
              values(%s,%s,%s,9,9,%s,'OTHER')""",
              (lot, 'P02-'+lot.hex[:12], root, now-timedelta(minutes=4)))
            cur.execute("""insert into erp.fg_stock_movements(product_id,lot_id,location_id,quality_grade,movement_type,
              qty_signed,unit_hpp_snapshot,source_type,source_id,physical_at,system_created_at)
              values(%s,%s,%s,'GRADE_A','ADJUSTMENT',9,0,'P02_PROBE',%s,%s,%s)""",
              (root, lot, base.LOCATION, uuid.uuid4(), now-timedelta(minutes=3), now-timedelta(minutes=2)))
            cur.execute("""insert into erp.sales_headers(id,sale_number,customer_id,sale_date,status,source_location_id,created_at)
              values(%s,%s,%s,%s,'DRAFT',%s,%s)""",
              (sale, 'P02-'+sale.hex[:12], customer, now-timedelta(minutes=2),
                base.LOCATION, now-timedelta(minutes=2)))
            cur.execute("""insert into erp.sales_items(sale_id,product_id,qty_pcs,unit_price_snapshot)
              values(%s,%s,2,10000)""", (sale, root))
        finally:
            cur.execute('set local session_replication_role=origin')

        result = capture(cur, root)
        sources = result['sources']
        children = [row for row in sources['cutting_candidates']
            if row['cutting_group_id'] in (a['group'], z['group'])]
        actual = dict(status=result['status'], physical=len(sources['physical']),
            child_group_ids=sorted(set(row['cutting_group_id'] for row in children)),
            child_quantities=sorted(int(row['cut_qty_pcs']) for row in children),
            child_match=[row['match'] for row in children],
            stock=[row['qty_signed_pcs'] for row in sources['stock_movements']
                if row['lot_id'] == str(lot)],
            sale=[row['qty_pcs'] for row in sources['sales_lines']
                if row['sale_id'] == str(sale)],
            cost=[row['valuation'] for row in sources['lot_cost']
                if row['lot_id'] == str(lot)],
            count_integrity=all(len(sources[k]) == n for k,n in result['counts'].items()),
            one_cutoff=len(set(result['snapshot'][key] for key in
                ('effective_as_of', 'known_as_of', 'generated_at')))==1)
        expected = dict(status='COMPLETE',physical=1,
            child_group_ids=sorted([a['group'], z['group']]),
            child_quantities=[6,7],child_match=['UNBOUND_CANDIDATE']*2,
            stock=['9'],sale=['2'],
            cost=[{'state':'UNKNOWN','reason':'PENDING_COST_OR_NO_HPP'}],
            count_integrity=True,one_cutoff=True)
        return dict(status='PASS' if actual==expected else 'FAIL',
            expected=expected,actual=actual,read_only_query=True,
            fixture='native transaction: legitimate two-child cutting chain; admin-only FG/draft cost-pending fixture')

    return [('P02_ONE_ROOT_TWO_CHILD_PENDING_COST', filled)]


def run():
    import cp6_bf_probe as bfp
    import cp6_auditor_runner as runner
    import cp7_p00_catalogue as p00
    import cp6_t3_package_run as package_run

    url = package_run.boundary.ADMIN
    entry = p00.run(url, package_run.boundary)
    assert entry['status'] == 'PASS'
    missing = read_only_missing(url)
    group = runner.strict_group('CP7_P02_SOURCE_CAPTURE',cases,bfp.verified)
    success = missing['status'] == 'PASS' and group['status'] == 'PASS'
    result = dict(label='CP7_P02_SOURCE_CAPTURE',status='PASS' if success else 'INCOMPLETE',
        groups={'p00_catalogue':entry,'read_only_missing':missing,
                'native_fixture':{k:group.get(k) for k in ('status','counts','database_remaining','complete_boundary_restored','error')}},
        production_go=False, independent_acceptance=False,
        actor_facade='NOT_RUN',coherent_persistence='NOT_RUN',concurrency='NOT_RUN')
    out = ROOT/'cp6-proof/t3';out.mkdir(parents=True,exist_ok=True)
    (out/'CP7_P02_SOURCE_CAPTURE.json').write_text(json.dumps(result,indent=2,default=str)+'\n')
    print(json.dumps(result,default=str),flush=True)
    return result


if __name__ == '__main__':
    import cp6_t3_package_run as package_run
    package_run._writer_runtime = lambda browser_mode=False: run()
    package_run.run('install')
