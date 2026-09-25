"""Disposable rev6 setup. Product master identities come from public initial-import RPC.
No product DDL, validator patch, response rewriting or posted-quantity edit.
Legacy seed products are excluded with a recorded visibility-only fixture update;
the browser uses the real search UI to scope transaction rows to the new model.
"""
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit
import json, os, sys, uuid
import psycopg
sys.path.insert(0, str(Path.cwd() / 'scripts'))
sys.path.append(str(Path.cwd().parent / 'auditor/scripts'))
import cp6_aw_probe as awp
import cp6_initial_import_production_trial as imports

def fixture(scope, today):
    url = os.environ['AUDITOR_BROWSER_DB_URL']
    assert urlsplit(url).path == '/cp6_auditor_browser'
    api, chain = awp.api, awp.chain
    prod = chain.production
    assert chain.work.fixture.production is prod, 'Fixture recipe module identity drift'
    with psycopg.connect(url) as conn, conn.cursor() as raw:
        cur = awp.OrdinaryDraftCursor(raw)
        api.admin(cur)
        before = cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        if not before: cur.execute('grant usage on schema erp to authenticated')
        prod.prior.set_open_period(cur, today - timedelta(days=90))
        # Known supported public CREATE/SAVE_FILE/VALIDATE/FINALIZE route.
        opening = imports.fixture(api, cur, today)
        api.upload(cur, opening['batch'], 'BRAND', [dict(brand_code=opening['code'], brand_name='GPT browser '+opening['code'])])
        imports.finalize(api, cur, opening)
        code = opening['code']
        api.admin(cur)
        model, contractor, product, size = cur.execute("""
            select m.id,c.id,p.id,p.size_id from erp.product_models m
            join erp.contractors c on c.contractor_code=m.model_code
            join erp.products p on p.model_id=m.id and p.sku=m.model_code
            where m.model_code=%s
        """, (code,)).fetchone()
        identities = dict(model=str(model), contractor=str(contractor), product=str(product), size=str(size))
        assert all(uuid.UUID(v).version == 4 for v in identities.values()), identities
        # Association only, before any new physical work; imported product already binds model and size.
        linked = cur.execute("""
            insert into erp.product_model_sizes(model_id,size_id,sort_order)
            values(%s,%s,1) on conflict(model_id,size_id) do nothing returning model_id
        """, (model,size)).fetchall()
        attendance_required=cur.execute('select attendance_required from erp.contractors where id=%s',(contractor,)).fetchone()[0]
        policy_day=today-timedelta(days=30)
        current_policy=cur.execute("""select id from erp.contractor_hpp_policy_versions
            where contractor_id=%s and effective_from<=%s and (effective_to is null or effective_to>=%s)
            order by effective_from desc,id desc limit 1""",(contractor,policy_day,policy_day)).fetchone()
        api.ordinary(cur)
        policy = cur.execute('select public.erp_set_contractor_hpp_policy_v1(%s::jsonb,%s,%s)', (
            json.dumps(dict(contractor_id=str(contractor),effective_from=str(policy_day),
                            is_special=False,attendance_required=attendance_required,reason='GPT disposable valid-UUID browser fixture')),
            uuid.uuid4(),current_policy[0] if current_policy else None)).fetchone()[0]
        pattern_code = 'G8U4-' + uuid.uuid4().hex[:16].upper()
        cur.execute('select public.erp_save_pattern_v1(%s::jsonb,%s,null)', (
            json.dumps(dict(code=pattern_code,revision='R1',name=pattern_code,sort_order=0,
                            change_reason='GPT valid-UUID browser fixture')),uuid.uuid4()))
        api.admin(cur)
        pattern = cur.execute('select id from erp.production_patterns where pattern_code=%s', (pattern_code,)).fetchone()[0]
        assert uuid.UUID(str(pattern)).version == 4
        # Recipe parameters only; candidate SQL and source files are never changed.
        old = (prod.MODEL,prod.CONTRACTOR,prod.PATTERN,prod.base.SIZE,chain.base.SIZE,prod.base.create_product)
        prod.MODEL,prod.CONTRACTOR,prod.PATTERN = str(model),str(contractor),str(pattern)
        prod.base.SIZE = chain.base.SIZE = str(size)
        prod.base.create_product = lambda c, tag: product
        sources=[]
        try:
            for _ in range(2 if scope == 'LAUNDRY' else 1):
                f=chain.work.draft(cur,today,Decimal(0))
                chain.peer.ordinary(cur)
                cur.execute('select erp.post_work_completion(%s)', (f['completion'],))
                prod.owner(cur)
                cur.execute('select public.erp_record_sewing_terminal_v1(%s::jsonb,%s)', (
                    json.dumps(dict(work_completion_id=str(f['completion']),qty_pcs=10,
                                    reason='GPT valid-UUID physical source')), uuid.uuid4()))
                api.admin(cur)
                day=cur.execute("select (physical_at at time zone 'Asia/Jakarta')::date from erp.work_completion_events where id=%s",(f['completion'],)).fetchone()[0]
                batch=cur.execute('select b.id from erp.cutting_distribution_batches b join erp.cutting_pickups p on p.id=b.pickup_id where p.cutting_group_id=%s',(f['group'],)).fetchone()[0]
                f.update(batch=str(batch),group=str(f['group']),day=day,product=str(product))
                f['delivery']=chain.laundry_action(cur,'POST_DELIVERY',dict(
                    distribution_batch_id=f['batch'],vendor_id=chain.base.VENDOR,wash_process_id=chain.base.BASE_PROCESS,
                    target_dyeing_color='Blue',physical_at=prod.at(day,11).isoformat(),
                    reason='GPT valid-UUID ten-piece delivery',
                    lines=[dict(size_id=str(size),qty_sent_pcs=10)]),chain.base.group_version(cur,f['group']))['delivery_id']
                if scope == 'QC': awp.r1.receipt(cur,f,prod.at(day,13),0)
                assert uuid.UUID(f['group']).version == 4
                sources.append(dict(group=f['group'],delivery=str(f['delivery']),batch=f['batch']))
        finally:
            prod.MODEL,prod.CONTRACTOR,prod.PATTERN,prod.base.SIZE,chain.base.SIZE,prod.base.create_product = old
        api.admin(cur)
        # Explicitly authorized disposable fixture isolation. No deactivation of live business facts.
        bad_model='a2000000-0000-0000-0000-000000000001'
        seed_before=cur.execute('select id,sku,is_active,is_portal_visible,model_id from erp.products where model_id=%s order by id',(bad_model,)).fetchall()
        physical_query = "select count(*),md5(coalesce(string_agg(to_jsonb(m)::text,',' order by m.id),'[]')) from erp.fg_stock_movements m"
        physical_before=cur.execute(physical_query).fetchone()
        cur.execute('update erp.products set is_portal_visible=false where model_id=%s and is_portal_visible',(bad_model,))
        hidden_count=cur.rowcount
        physical_after=cur.execute(physical_query).fetchone()
        assert physical_before == physical_after
        seed_after=cur.execute('select id,sku,is_active,is_portal_visible,model_id from erp.products where model_id=%s order by id',(bad_model,)).fetchall()
        if not before: cur.execute('revoke usage on schema erp from authenticated')
        after=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        assert after == before
        conn.commit()
        return dict(scope=scope,query=code,opening_batch=opening['batch'],
                    identities=identities,pattern=str(pattern),sources=sources,
                    expected_qty=20 if scope=='LAUNDRY' else 10,
                    master_identity_creation='public initial-import CREATE/SAVE_FILE/VALIDATE/FINALIZE',
                    pattern_creation='public.erp_save_pattern_v1',
                    cutting_creation='public.erp_save_cutting_group_before_sewing_v2 SAVE_DRAFT/POST',
                    model_size_association_rows_inserted=len(linked),
                    contractor_policy_api='public.erp_set_contractor_hpp_policy_v1',
                    setup_sql_notes=['model/size association before work','ordinary work drafts from existing recipe',
                                     'legacy seed product discovery flag only; transaction selection uses actual UI search'],
                    seed_product_visibility=dict(before=seed_before,after=seed_after,changed=hidden_count,
                                                 fg_movement_rows_unchanged=True),
                    schema_usage_before=before,schema_usage_after=after)

if __name__=='__main__':
    print(json.dumps(fixture(sys.argv[1],date.fromisoformat(sys.argv[2])),default=str))
