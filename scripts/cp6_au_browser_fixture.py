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
if os.environ.get('CP6_T3_BROWSER')=='1':
    # T3: the combined candidate (release package + AW/AX T1); see scripts/cp6_t3_browser_verify.py.
    import cp6_t3_browser_verify as runtime
else:
    import cp6_au_runtime as runtime
from cp6_ao_ap_inventory import data

ADMIN='postgresql://supabase_admin:postgres@127.0.0.1:54322/cp6_rollback'
OUT=Path('cp6-proof/au-browser')


def seed(cur):
    runtime.verified(cur)
    browser_seed.OUT.mkdir(parents=True,exist_ok=True)
    browser_seed.browser_foundation(cur)
    today=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
    api.production.prior.set_open_period(cur,today-timedelta(days=90));api.admin(cur)
    cases=[]
    for versioned in (False,True):
        f=production.fixture(api,cur,today)
        api.upload(cur,f['batch'],'BRAND',[dict(brand_code=f['code'],brand_name='AT browser '+f['code'])])
        _,sources=production.finalize(api,cur,f)
        first,model,size=cur.execute('select id,model_id,size_id from erp.products where sku=%s',(f['code'],)).fetchone()
        brand_code=f['code']+'B'
        brand_name='AT browser versioned output' if versioned else 'AT browser cross brand output'
        brand=cur.execute('insert into erp.brands(brand_code,brand_name) values(%s,%s) returning id',(brand_code,brand_name)).fetchone()[0]
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


def identities(cur):
    """Resolve only the two known synthetic fixtures from the installed clone.

    The saved fixture file is evidence, never an input to network commands.
    """
    rows=cur.execute('''select h.migration_batch_id,p.sku,b.brand_code,original.id,p.id,s.opening_item_id,
        p.sku||'F',((statement_timestamp() at time zone 'Asia/Jakarta')::date-3)::text,
        b.brand_name='AT browser versioned output'
        from erp.brands b join erp.products p on p.brand_id=b.id and p.effective_to is null
        join erp.products original on original.sku=p.sku and original.brand_id<>b.id
        join erp.opening_balance_items i on i.product_id=original.id and i.balance_type='BS'
        join erp.opening_balance_headers h on h.id=i.opening_id
        join erp.initial_import_production_sources s on s.batch_id=h.migration_batch_id
        join erp.opening_balance_items wip on wip.id=s.opening_item_id and wip.balance_type='WIP'
        where b.brand_name in ('AT browser cross brand output','AT browser versioned output')
        order by b.brand_name''').fetchall()
    assert len(rows)==2 and [r[-1] for r in rows]==[False,True],'AT_BROWSER_FIXTURE_IDENTITIES_MISSING_OR_AMBIGUOUS'
    keys=('batch_id','code','brand','first_product','expected_product','opening_item_id','location','day','versioned')
    return dict(cases=[dict(zip(keys,row)) for row in rows])


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
    assert os.environ.get('CP6_AU_BROWSER_CONFIRM')=='cp6_rollback'
    OUT.mkdir(parents=True,exist_ok=True)
    with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:
        assert cur.execute('select current_database()').fetchone()==('cp6_rollback',)
        mode=sys.argv[1]
        if mode=='seed':
            value=seed(cur);(OUT/'FIXTURE.json').write_text(json.dumps(value,indent=2,default=str)+'\n')
        elif mode=='identities':value=identities(cur)
        elif mode=='boundary':
            snap=data(cur);value=dict(sha256=hashlib.sha256(json.dumps(snap,sort_keys=True,default=str).encode()).hexdigest(),tables=len(snap))
        elif mode=='state':value=state(cur,sys.argv[2])
        elif mode=='verify':
            production.truth(cur);value=runtime.verified(cur)
        else:raise AssertionError('UNKNOWN_MODE')
        print(json.dumps(value,default=str))


if __name__=='__main__':main()
