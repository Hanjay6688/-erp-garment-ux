"""Disposable browser fixtures and independent observations for AT identity flow."""
from pathlib import Path
from datetime import timedelta
import hashlib,json,os,sys
import psycopg
import cp6_ao_ap_installed as api
import cp6_initial_import_production_trial as production
import cp6_ap_flow_fixture as browser_seed
import cp6_as_probe as peer
import cp6_at_probe as audit
import cp6_at_runtime as runtime
from cp6_ao_ap_inventory import data

ADMIN='postgresql://supabase_admin:postgres@127.0.0.1:54322/cp6_rollback'
OUT=Path('cp6-proof/at-browser')


def seed(cur):
    runtime.verified(cur)
    browser_seed.OUT.mkdir(parents=True,exist_ok=True)
    browser_seed.browser_foundation(cur)
    today=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
    api.production.prior.set_open_period(cur,today-timedelta(days=90));api.admin(cur)
    cases=[]
    for versioned in (False,True):
        f=production.fixture(api,cur,today)
        _,sources=production.finalize(api,cur,f)
        first,model,size=cur.execute('select id,model_id,size_id from erp.products where sku=%s',(f['code'],)).fetchone()
        brand_code=f['code']+'B'
        brand=cur.execute('insert into erp.brands(brand_code,brand_name) values(%s,%s) returning id',(brand_code,brand_code)).fetchone()[0]
        if versioned:
            _,second=audit.series(cur,f['code'],model,brand,size,peer.invoice.at(today-timedelta(days=6),0),peer.invoice.at(today-timedelta(days=4),12))
        else:
            second=cur.execute('''insert into erp.products(sku,product_name,model_id,brand_id,size_id,color_name,is_active,effective_from)
                values(%s,'AT browser second brand',%s,%s,%s,'Blue',true,%s) returning id''',
                (f['code'],model,brand,size,peer.invoice.at(today-timedelta(days=6),0))).fetchone()[0]
        cases.append(dict(batch_id=f['batch'],code=f['code'],brand=brand_code,first_product=first,expected_product=second,
                          opening_item_id=sources['WIP']['opening_item_id'],location=f['code']+'F',day=str(today-timedelta(days=3)),versioned=versioned))
    runtime.verified(cur)
    return dict(cases=cases)


def state(cur,batch):
    ledger=production.effects(api,cur)
    all_ledger=dict(cur.execute('select account_id::text,sum(debit-credit)::text from erp.journal_lines group by account_id having sum(debit-credit)<>0 order by account_id').fetchall())
    outputs=cur.execute('''select o.id,l.id,l.product_id,o.qty_pcs,h.total_cost,
        exists(select 1 from erp.initial_import_wip_output_reversals r where r.output_id=o.id)
        from erp.initial_import_wip_outputs o join erp.initial_import_production_sources s on s.opening_item_id=o.opening_item_id
        join erp.fg_lots l on l.id=o.lot_id left join erp.hpp_versions h on h.lot_id=l.id and h.is_current
        where s.batch_id=%s order by o.id''',(batch,)).fetchall()
    source=next(x for x in api.read(cur,batch)['batch']['production_sources'] if x['balance_type']=='WIP')
    stocks=dict(cur.execute('''select p.id::text,coalesce(sum(m.qty_signed),0)::text
        from erp.products p left join erp.fg_stock_movements m on m.product_id=p.id
        where p.sku=(select pr.sku from erp.opening_balance_items i join erp.opening_balance_headers h on h.id=i.opening_id
          join erp.products pr on pr.id=i.product_id where h.migration_batch_id=%s and i.balance_type='BS')
        group by p.id''',(batch,)).fetchall())
    return dict(ledger=ledger,all_ledger=all_ledger,outputs=outputs,stocks=stocks,remaining=source['remaining_qty_pcs'])


def main():
    assert os.environ.get('CP6_AT_BROWSER_CONFIRM')=='cp6_rollback'
    OUT.mkdir(parents=True,exist_ok=True)
    with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:
        assert cur.execute('select current_database()').fetchone()==('cp6_rollback',)
        mode=sys.argv[1]
        if mode=='seed':
            value=seed(cur);(OUT/'FIXTURE.json').write_text(json.dumps(value,indent=2,default=str)+'\n')
        elif mode=='boundary':
            snap=data(cur);value=dict(sha256=hashlib.sha256(json.dumps(snap,sort_keys=True,default=str).encode()).hexdigest(),tables=len(snap))
        elif mode=='state':value=state(cur,sys.argv[2])
        elif mode=='verify':
            production.truth(cur);value=runtime.verified(cur)
        else:raise AssertionError('UNKNOWN_MODE')
        print(json.dumps(value,default=str))


if __name__=='__main__':main()
