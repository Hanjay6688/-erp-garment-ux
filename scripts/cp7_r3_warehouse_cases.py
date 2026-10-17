"""R3-03 (owner D16-1, "selesain biar gausa sembunyiin"): Ringkasan Gudang reads real stock (menu warehouse-dashboard).

Native, race and real-Auth HTTP cases for scripts/cp7-src/warehouse-summary/summary.sql (cp7_warehouse_summary_bundle.py),
spliced into the CP17 harness through cp7_r3_cases.py. Stock is made only by Native writers: a roll received through the
Native purchase post and cut through Buat Potongan (erp_cp7_save_cutting_auto_po_v1), an accessory receipt through
Pembelian & Penerimaan, finished goods through the Native FG receipt and a sales draft reservation, transfers, counts, FG
adjustments and a fabric minimum through their own screens' facades. The oracles are independent: Python sums of the raw
rows of erp.material_stock_movements / erp.fg_stock_movements and counts of the Native document tables, and the detail
reads the summary must equal (erp_cp7_get_materials_v1, erp_get_accessory_service_workspace_v1, erp_cp7_get_fg_v1), never
the summary's own answer alone. Access is checked against the seeded roles' permission rows (erp.app_role_permissions),
the same keys as src/auth/accessCatalog.ts.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from decimal import Decimal as D,ROUND_HALF_UP
import json,threading,time,uuid
import cp7_snapshot_cases as auth
import cp7_master_cases as master
import cp7_auto_po_cases as po
import cp7_material_cases as material
import cp7_material_unrolled_cases as unrolled
import cp7_procurement_cases as receipt
import cp7_fg_cases as fg
import cp7_warehouse_summary_bundle as bundle
b=auth.b
refused=auth.refused

NATIVE=['CP17_R3_03_WAREHOUSE_RECEIPT_CUTTING_EQUALS_NATIVE_AND_READS','CP17_R3_03_WAREHOUSE_VALUES_ONLY_WITH_HPP_VIEW',
        'CP17_R3_03_WAREHOUSE_SECTIONS_FOLLOW_KEYS','CP17_R3_03_WAREHOUSE_DENIED_WITHOUT_DASHBOARD_KEY',
        'CP17_R3_03_WAREHOUSE_ATTENTION_FROM_NATIVE_ROWS','CP17_R3_03_WAREHOUSE_READ_ONLY_AND_PRIVATE']
RACES=['CP17_RACE_R3_03_WAREHOUSE_TRANSFER_DURING_READ_NEVER_HALF']
HTTP=['CP17_HTTP_R3_03_WAREHOUSE_OWNER_GUDANG_AND_DENIED']
BROWSER=['CP17_BROWSER_R3_03_WAREHOUSE_SUMMARY_DESKTOP','CP17_BROWSER_R3_03_WAREHOUSE_SUMMARY_MOBILE']
FUNCTIONS=bundle.FUNCTIONS
DASH='warehouse.dashboard.view'
SECTION_KEYS=dict(materials='warehouse.material.view',accessories='warehouse.accessory.view',finished_goods='warehouse.fg.view')
# Each attention check and the keys it needs (the server rule, mirrored for the oracle).
ATTENTION_KEYS=dict(MATERIAL_BALANCE_REVIEW=('warehouse.material.view',),ACCESSORY_OUTSIDE_ACCESSORY_LOCATIONS=('warehouse.material.view',),
    ACCESSORY_NEGATIVE=('warehouse.accessory.view',),FG_POSITION_REVIEW=('warehouse.fg.view',),FABRIC_BELOW_MINIMUM=('warehouse.material.view','master.fabric.view'),
    RECEIPT_DRAFT=('warehouse.procurement.view',),MATERIAL_TRANSFER_DRAFT=('warehouse.material.view',),
    MATERIAL_COUNT_DRAFT=('warehouse.material.view','warehouse.stock.adjust'),FG_ADJUSTMENT_DRAFT=('warehouse.fg.view','warehouse.stock.adjust'))

def one(cur,sql,args=()):return cur.execute(sql,args).fetchone()[0]
def cp17():
    import cp7_cp17_fix_cases as m
    return m
def q6(x):return D(x).quantize(D('0.000001'),rounding=ROUND_HALF_UP)
def q2(x):return D(x).quantize(D('0.01'),rounding=ROUND_HALF_UP)

# ---------------------------------------------------------------- reads (as the screen calls them)
def read(cur,query=None,subject=None):
    auth.actor(cur,subject);r=one(cur,'select public.erp_cp7_get_warehouse_summary_v1(%s::jsonb)',(json.dumps(query or {}),));b.api.admin(cur);return r
def read_all(cur,subject=None,q=''):
    """Every page of one search (one transaction, nothing else writes): the first answer and all location rows."""
    first=None;rows=[];off=0
    while True:
        r=read(cur,dict(q=q,offset=off,limit=100),subject);first=first or r;rows+=r['page']['rows']
        assert r['totals']==first['totals'] and r['attention']==first['attention'],'CP7_R3_03_PAGES_DISAGREE'
        if r['page']['next_offset'] is None:break
        off=r['page']['next_offset']
    assert len(rows)==int(first['page']['total']) and len({x['location_id'] for x in rows})==len(rows)
    return first,rows
def material_rows(cur,subject=None):
    rows=[];off=0
    while True:
        auth.actor(cur,subject);r=one(cur,'select public.erp_cp7_get_materials_v1(%s::jsonb)',(json.dumps(dict(offset=off,limit=100)),));b.api.admin(cur)
        rows+=r['page']['rows']
        if r['page']['next_offset'] is None:return rows
        off=r['page']['next_offset']
def fg_rows(cur,subject=None):
    rows=[];off=0
    while True:
        auth.actor(cur,subject);r=one(cur,'select public.erp_cp7_get_fg_v1(%s::jsonb)',(json.dumps(dict(purpose='SUMMARY',offset=off,limit=100)),));b.api.admin(cur)
        rows+=r['page']['rows']
        if r['page']['next_offset'] is None:return r,rows
        off=r['page']['next_offset']
def accessory_rows(cur,subject=None):
    rows=[];page=1
    while True:
        auth.actor(cur,subject);r=one(cur,'select public.erp_get_accessory_service_workspace_v1(%s::jsonb)',(json.dumps(dict(page=page,page_size=50)),));b.api.admin(cur)
        rows+=r['stock']
        if len(rows)>=int(r['stock_total']) or not r['stock']:return rows
        page+=1

# ---------------------------------------------------------------- the summary as plain dicts
def by_location(rows):
    """{location: dict(mat={(kind,unit):(qty,rolls,balances,conflict)},mv,mu,acc={unit:(qty,items,balances,conflict)},av,au,fg=(...),fv,fu)}"""
    out={}
    for r in rows:
        e=out[r['location_id']]=dict(mat=None,acc=None,fg=None)
        if r['materials'] is not None:
            e['mat']={(x['kind'],x['unit_code']):(D(x['qty']),int(x['rolls']),int(x['balances']),x['quality']=='CONFLICT') for x in r['materials']['lines']}
            if 'valuation' in r['materials']:e['mv']=(D(r['materials']['valuation']['value']),int(r['materials']['valuation']['unknown_count']))
        if r['accessories'] is not None:
            e['acc']={x['unit_code']:(D(x['qty']),int(x['items']),int(x['balances']),x['quality']=='CONFLICT') for x in r['accessories']['lines']}
            if 'valuation' in r['accessories']:e['av']=(D(r['accessories']['valuation']['value']),int(r['accessories']['valuation']['unknown_count']))
        f=r['finished_goods']
        if f is not None:
            e['fg']=(D(f['physical_qty']),D(f['reserved_qty']),D(f['available_qty']),int(f['positions']),f['quality']=='CONFLICT',{g['quality_grade']:D(g['physical_qty']) for g in f['grades']})
            if 'valuation' in f:e['fv']=(D(f['valuation']['value']),int(f['valuation']['unknown_count']))
    return out
def quantities(summary_rows):
    """The summary rows without any value (for comparing a role with and without finance.hpp.view)."""
    return {k:dict(mat=v['mat'],acc=v['acc'],fg=v['fg']) for k,v in by_location(summary_rows).items()}
def at(text):return datetime.fromisoformat(text.replace('Z','+00:00'))

# ---------------------------------------------------------------- independent oracle (raw Native rows, Python sums)
def native(cur,now):
    b.api.admin(cur)
    loc={r[0]:(r[1],r[2]) for r in cur.execute('select id::text,location_type,is_active from erp.locations')}
    mat={r[0]:(r[1],r[2],r[3],r[4]) for r in cur.execute('select id::text,material_type,unit_code,moving_average_cost,is_active from erp.materials')}
    roll={r[0]:r[1] for r in cur.execute('select id::text,material_id::text from erp.material_rolls')}
    bal={};acc={}
    for m,rl,l,q,t in cur.execute('select material_id::text,roll_id::text,location_id::text,qty_signed,physical_at from erp.material_stock_movements').fetchall():
        if t<=now:bal[(m,rl,l)]=bal.get((m,rl,l),D(0))+q
        if mat[m][0]=='ACCESSORY' and loc[l]==('RAW_MATERIAL_WAREHOUSE',True):acc[(m,l)]=acc.get((m,l),D(0))+q
    bal={k:v for k,v in bal.items() if v!=0};acc={k:v for k,v in acc.items() if v!=0}
    out={};att=dict(MATERIAL_BALANCE_REVIEW=0,ACCESSORY_OUTSIDE_ACCESSORY_LOCATIONS=0,ACCESSORY_NEGATIVE=0,FG_POSITION_REVIEW=0)
    blank=lambda:dict(mat={},mv=[D(0),0],acc={},av=[D(0),0],fg=None)
    per_material={}
    for (m,rl,l),q in bal.items():
        t,unit,mac,_=mat[m];per_material[m]=per_material.get(m,D(0))+q
        if t=='ACCESSORY':
            att['ACCESSORY_OUTSIDE_ACCESSORY_LOCATIONS']+=int(loc[l]!=('RAW_MATERIAL_WAREHOUSE',True));continue
        valid=(t=='FABRIC' and rl is not None and roll.get(rl)==m) or (t!='FABRIC' and rl is None)
        att['MATERIAL_BALANCE_REVIEW']+=int(q<0 or not valid)
        e=out.setdefault(l,blank());kind='FABRIC' if t=='FABRIC' else 'OTHER'
        qty,rolls,n,conflict=e['mat'].get((kind,unit),(D(0),0,0,False))
        e['mat'][(kind,unit)]=(qty+q,rolls+int(kind=='FABRIC' and valid and q>0),n+1,conflict or q<0 or not valid)
        if mac is None:e['mv'][1]+=1
        else:e['mv'][0]+=q6(q*mac)
    for (m,l),q in acc.items():
        unit,mac=mat[m][1],mat[m][2];att['ACCESSORY_NEGATIVE']+=int(q<0)
        e=out.setdefault(l,blank());qty,items,n,conflict=e['acc'].get(unit,(D(0),set(),0,False))
        e['acc'][unit]=(qty+q,items|{m},n+1,conflict or q<0)
        if mac is None:e['av'][1]+=1
        else:e['av'][0]+=q2(q*mac)
    listed={r[0] for r in cur.execute('select p.id::text from erp.products p join erp.sizes s on s.id=p.size_id join erp.brands r on r.id=p.brand_id')}
    lots={r[0]:r[1] for r in cur.execute('select id::text,product_id::text from erp.fg_lots')}
    moves=cur.execute('select id::text,product_id::text,lot_id::text,location_id::text,quality_grade::text,qty_signed,movement_type,physical_at,reversal_of_id::text from erp.fg_stock_movements').fetchall()
    undone={x[8] for x in moves if x[8] and x[7]<=now};pos={}
    for i,p,lot,l,g,q,kind,t,_ in moves:
        if t>now or p not in listed:continue
        x=pos.setdefault((p,lot,l,g),[D(0),D(0)]);x[0]+=D(q)
        if kind=='SALE_RESERVE' and i not in undone:x[1]+=abs(D(q))
    for (p,lot,l,g),(avail,res) in pos.items():
        phys=avail+res
        if phys==0 and avail==0 and res==0:continue
        bad=avail<0 or phys<0 or lots.get(lot)!=p;att['FG_POSITION_REVIEW']+=int(bad)
        e=out.setdefault(l,blank());ph,rs,av,n,conflict,grades=e['fg'] or (D(0),D(0),D(0),0,False,{})
        e['fg']=(ph+phys,rs+res,av+avail,n+1,conflict or bad,dict(grades,**{g:grades.get(g,D(0))+phys}))
    minimum=cur.execute("""select m.id::text,f.minimum_stock_qty from erp.materials m join erp.fabric_master_profiles f on f.material_id=m.id
        where m.material_type='FABRIC' and m.is_active and f.minimum_stock_qty>0""").fetchall()
    att['FABRIC_BELOW_MINIMUM']=sum(1 for m,mn in minimum if per_material.get(m,D(0))<mn)
    for kind,table in (('RECEIPT_DRAFT','material_purchase_headers'),('MATERIAL_TRANSFER_DRAFT','material_transfers'),
                       ('MATERIAL_COUNT_DRAFT','material_adjustments'),('FG_ADJUSTMENT_DRAFT','fg_adjustments')):
        att[kind]=len([1 for (s,) in cur.execute(f'select status::text from erp.{table}').fetchall() if s=='DRAFT'])
    for e in out.values():
        e['mv']=tuple(e['mv']);e['av']=tuple(e['av'])
        e['acc']={u:(q,len(items),n,c) for u,(q,items,n,c) in e['acc'].items()}
    return out,att
def expect_rows(oracle,sections,values):
    """The oracle restricted to what a role may see: locations holding stock of a visible section."""
    out={}
    for l,e in oracle.items():
        mat=e['mat'] if sections['materials'] else None;acc=e['acc'] if sections['accessories'] else None;f=e['fg'] if sections['finished_goods'] else None
        if not (mat or acc or f):continue
        x=dict(mat=None if mat is None else mat,acc=None if acc is None else acc,
               fg=None if not sections['finished_goods'] else (f or (D(0),D(0),D(0),0,False,{})))
        if sections['materials'] and mat is None:x['mat']={}
        if sections['accessories'] and acc is None:x['acc']={}
        if values:
            if sections['materials']:x['mv']=e['mv']
            if sections['accessories']:x['av']=e['av']
        out[l]=x
    return out
def compare(summary_rows,oracle,sections,values,fg_values=None):
    got=by_location(summary_rows);want=expect_rows(oracle,sections,values)
    assert set(got)==set(want),('CP7_R3_03_LOCATIONS_DIFFER',sorted(set(got)^set(want))[:10])
    for l,w in want.items():
        g=got[l]
        for key in ('mat','acc','fg'):
            assert g[key]==w[key],('CP7_R3_03_QTY_DIFFERS',key,l,g[key],w[key])
        for key in ('mv','av'):
            assert g.get(key)==w.get(key),('CP7_R3_03_VALUE_DIFFERS',key,l,g.get(key),w.get(key))
        if values and sections['finished_goods']:
            assert g['fv']==(fg_values or {}).get(l,(D(0),0)),('CP7_R3_03_FG_VALUE_DIFFERS',l,g['fv'],(fg_values or {}).get(l))
        if not values:assert 'mv' not in g and 'av' not in g and 'fv' not in g,('CP7_R3_03_VALUE_WITHOUT_HPP_VIEW',l)
def totals_of(oracle,sections):
    """Totals over every location (Python), in the summary's shape."""
    mat={};acc={};fgt=[D(0),D(0),D(0),0]
    for e in oracle.values():
        for k,(q,r,n,c) in e['mat'].items():
            x=mat.get(k,(D(0),0,0,False));mat[k]=(x[0]+q,x[1]+r,x[2]+n,x[3] or c)
        for u,(q,i,n,c) in e['acc'].items():
            x=acc.get(u,(D(0),0,0,False));acc[u]=(x[0]+q,None,x[2]+n,x[3] or c)
        if e['fg']:
            for j in range(4):fgt[j]+=e['fg'][j]
    return dict(mat=mat if sections['materials'] else None,acc={u:(q,n,c) for u,(q,_,n,c) in acc.items()} if sections['accessories'] else None,
                fg=tuple(fgt) if sections['finished_goods'] else None)
def summary_totals(answer):
    t=answer['totals']
    return dict(mat=None if t['materials'] is None else {(x['kind'],x['unit_code']):(D(x['qty']),int(x['rolls']),int(x['balances']),x['quality']=='CONFLICT') for x in t['materials']['lines']},
                acc=None if t['accessories'] is None else {x['unit_code']:(D(x['qty']),int(x['balances']),x['quality']=='CONFLICT') for x in t['accessories']['lines']},
                fg=None if t['finished_goods'] is None else tuple(D(t['finished_goods'][k]) for k in ('physical_qty','reserved_qty','available_qty'))+(int(t['finished_goods']['positions']),))
def role_permissions(cur,subject):
    b.api.admin(cur)
    role=one(cur,'select role_id from erp.app_users where auth_user_id=%s',(subject,))
    code=one(cur,'select role_code from erp.app_roles where id=%s',(role,))
    # erp.has_permission: a key of the role that is active in erp.app_permissions.
    keys={r[0] for r in cur.execute('select rp.permission_key from erp.app_role_permissions rp join erp.app_permissions p on p.permission_key=rp.permission_key and p.is_active where rp.role_id=%s',(role,))}
    # The Native resolver grants the protected OWNER every active key (v2.6.17); read them from the catalog table.
    if code=='OWNER':keys|={r[0] for r in cur.execute('select permission_key from erp.app_permissions where is_active')}
    return keys
def expected_sections(keys):return {k:v in keys for k,v in SECTION_KEYS.items()}
def expected_attention(keys):return sorted(k for k,need in ATTENTION_KEYS.items() if all(x in keys for x in need))
def custom(cur,keys):return receipt.custom(cur,list(keys))[0]

# ---------------------------------------------------------------- fixtures (Native writers only)
def cut_roll(cur,today,issued=4):
    """A roll of 10 received through the Native purchase post at its own raw warehouse, then `issued` cut through Buat
    Potongan (PO made with the cutting, roll issued by the Native cutting post)."""
    g=po.receipt(cur,today);b.api.admin(cur)
    g['code']=one(cur,'select location_code from erp.locations where id=%s',(g['location'],))
    g['unit']=one(cur,'select unit_code from erp.materials where id=%s',(g['material'],))
    if issued:
        g['cut']=po.command(cur,po.post_body(g,qty=issued,pieces=issued));assert po.roll_stock(cur,g)==10-issued
    return g
def stocked(cur,today):
    """Every kind present: fabric received and cut, an accessory receipt, finished goods with a reservation."""
    g=cut_roll(cur,today);a=unrolled.fixture(cur,today,'ACCESSORY');f=fg.fixture(cur,today);fg.draft(cur,f,4);b.api.admin(cur)
    return dict(fabric=g,accessory=a,fg=f)
def location_rows(cur,location,now):
    """Native rows of one location: (material, roll) balances and their value."""
    b.api.admin(cur)
    return cur.execute("""select s.material_id::text,s.roll_id::text,sum(s.qty_signed),m.moving_average_cost from erp.material_stock_movements s
        join erp.materials m on m.id=s.material_id where s.location_id=%s and s.physical_at<=%s group by 1,2,4 having sum(s.qty_signed)<>0""",(location,now)).fetchall()


def cases(cur,today):
    def receipt_cutting():
        owner=master.role_actor(cur,'OWNER')
        g=cut_roll(cur,today,0)
        first=read(cur,dict(q=g['code']),owner);row=first['page']['rows']
        assert len(row)==1 and row[0]['location_id']==str(g['location']),first['page']
        assert row[0]['materials']['lines']==[dict(kind='FABRIC',unit_code=g['unit'],qty=row[0]['materials']['lines'][0]['qty'],rolls='1',balances='1',quality='KNOWN')]
        assert D(row[0]['materials']['lines'][0]['qty'])==10
        others=lambda answer_rows:{k:v for k,v in by_location(answer_rows).items() if k!=str(g['location'])}
        _,before_all=read_all(cur,owner)
        # The cutting issue through Buat Potongan: only this roll at this location changes.
        g['cut']=po.command(cur,po.post_body(g,qty=4,pieces=4))
        after=read(cur,dict(q=g['code']),owner);line=after['page']['rows'][0]['materials']['lines'][0]
        native_rows=location_rows(cur,g['location'],at(after['read_at']))
        assert (D(line['qty']),line['rolls'])==(sum(r[2] for r in native_rows),'1')==(D(6),'1'),(line,native_rows)
        assert D(after['page']['rows'][0]['materials']['valuation']['value'])==sum(q6(r[2]*r[3]) for r in native_rows),after['page']['rows'][0]
        # Every kind present, then the whole summary against the raw rows and against the detail reads.
        a=unrolled.fixture(cur,today,'ACCESSORY');f=fg.fixture(cur,today);fg.draft(cur,f,4);b.api.admin(cur)
        answer,rows=read_all(cur,owner);now=at(answer['read_at'])
        oracle,att=native(cur,now);sections=dict(materials=True,accessories=True,finished_goods=True)
        fr,frows=fg_rows(cur,owner);fvals={}
        for r in frows:
            v=fvals.setdefault(r['location_id'],[D(0),0])
            if r['valuation']['state']=='KNOWN':v[0]+=D(r['valuation']['value'])
            else:v[1]+=1
        compare(rows,oracle,sections,True,{k:tuple(v) for k,v in fvals.items()})
        assert summary_totals(answer)==totals_of(oracle,sections),(summary_totals(answer),totals_of(oracle,sections))
        assert {x['kind']:int(x['count']) for x in answer['attention'] if x['kind'] in att}=={k:v for k,v in att.items()},(answer['attention'],att)
        # The detail reads: Bahan & Roll (without accessories), Aksesori, Ringkasan Barang Jadi.
        mrows=material_rows(cur,owner);per={};mval={}
        for r in mrows:
            if r['material_type']=='ACCESSORY':continue
            k=(r['location_id'],'FABRIC' if r['material_type']=='FABRIC' else 'OTHER',r['unit_code']);per[k]=per.get(k,D(0))+D(r['qty'])
            v=mval.setdefault(r['location_id'],[D(0),0])
            if r['valuation']['state']=='KNOWN':v[0]+=D(r['valuation']['value'])
            else:v[1]+=1
        mine=by_location(rows)
        assert {(l,k[0],k[1]):x[0] for l,e in mine.items() for k,x in e['mat'].items()}==per,'CP7_R3_03_NOT_EQUAL_BAHAN_ROLL'
        assert {l:e['mv'] for l,e in mine.items() if e['mat']}=={k:tuple(v) for k,v in mval.items()},'CP7_R3_03_VALUE_NOT_EQUAL_BAHAN_ROLL'
        outside=sum(1 for r in mrows if r['material_type']=='ACCESSORY' and r['availability'] in('LOCATION_INACTIVE','LOCATION_REVIEW'))
        arows=accessory_rows(cur,owner);aper={};aval={}
        for r in arows:
            k=(r['location_id'],r['unit']);aper[k]=aper.get(k,D(0))+D(r['qty'])
            v=aval.setdefault(r['location_id'],[D(0),0])
            if r['value'] is None:v[1]+=1
            else:v[0]+=D(r['value'])
        assert {(l,u):x[0] for l,e in mine.items() for u,x in e['acc'].items()}==aper,'CP7_R3_03_NOT_EQUAL_AKSESORI'
        assert {l:e['av'] for l,e in mine.items() if e['acc']}=={k:tuple(v) for k,v in aval.items()},'CP7_R3_03_VALUE_NOT_EQUAL_AKSESORI'
        fper={}
        for r in frows:
            x=fper.setdefault(r['location_id'],[D(0),D(0),D(0),0]);x[0]+=D(r['physical_qty']);x[1]+=D(r['reserved_qty']);x[2]+=D(r['available_qty']);x[3]+=1
        assert {l:e['fg'][:4] for l,e in mine.items() if e['fg'][3]}=={k:tuple(v) for k,v in fper.items()},'CP7_R3_03_NOT_EQUAL_BARANG_JADI'
        assert tuple(D(answer['totals']['finished_goods'][k]) for k in ('physical_qty','reserved_qty','available_qty'))==tuple(D(fr['totals'][k]) for k in ('physical_qty','reserved_qty','available_qty'))
        # The cutting changed nothing at any other location (the accessory and FG fixtures came after it).
        changed=others(rows);added={str(a['location']),str(f['location'])}
        assert {k:v for k,v in changed.items() if k not in added}=={k:v for k,v in others(before_all).items() if k not in added},'CP7_R3_03_CUTTING_MOVED_OTHER_LOCATIONS'
        fgloc=mine[str(f['location'])]['fg'];assert fgloc[1]>=4
        return dict(status='PASS',roll_after_receipt='10',roll_after_cutting='6',rolls=1,locations=len(rows),
                    equals_native_rows=True,equals_bahan_roll=True,equals_aksesori=True,equals_barang_jadi=True,
                    accessory_outside_accessory_locations=outside,attention=att)

    def values_only_with_hpp():
        s=stocked(cur,today);owner=master.role_actor(cur,'OWNER')
        plain=custom(cur,(DASH,)+tuple(SECTION_KEYS.values()));gudang=master.role_actor(cur,'GUDANG')
        finance=custom(cur,(DASH,'warehouse.fg.view','finance.hpp.view'))
        o,orows=read_all(cur,owner);p,prows=read_all(cur,plain);gd,grows=read_all(cur,gudang);fi,firows=read_all(cur,finance)
        assert o['financial_captured'] is True and all('valuation' in x[k] for x in orows for k in ('materials','accessories','finished_goods'))
        for answer,rows in ((p,prows),(gd,grows)):
            assert answer['financial_captured'] is False and 'valuation' not in json.dumps(answer),'CP7_R3_03_VALUE_WITHOUT_HPP_VIEW'
            assert quantities(rows)==quantities(orows) and summary_totals(answer)==summary_totals(o)
        assert fi['financial_captured'] is True and fi['totals']['materials'] is None and fi['totals']['accessories'] is None and 'valuation' in fi['totals']['finished_goods']
        assert {k:v['fg'] for k,v in quantities(firows).items()}=={k:v['fg'] for k,v in quantities(orows).items() if v['fg'][3]}
        # Its FG values are what Ringkasan Barang Jadi gives this same role (the HPP completeness depends on the role).
        own={}
        for r in fg_rows(cur,finance)[1]:
            v=own.setdefault(r['location_id'],[D(0),0])
            if r['valuation']['state']=='KNOWN':v[0]+=D(r['valuation']['value'])
            else:v[1]+=1
        assert {k:v['fv'] for k,v in by_location(firows).items()}=={k:tuple(v) for k,v in own.items()},'CP7_R3_03_FG_VALUE_NOT_EQUAL_FOR_ROLE'
        loc=next(x for x in orows if x['location_id']==str(s['fabric']['location']))
        native_rows=location_rows(cur,s['fabric']['location'],at(o['read_at']))
        assert D(loc['materials']['valuation']['value'])==sum(q6(r[2]*r[3]) for r in native_rows)
        return dict(status='PASS',owner_values=True,no_value_without_hpp=dict(custom_role=True,GUDANG=True),same_quantities=True,
                    finance_role_sees_fg_values_only=True,fabric_value=loc['materials']['valuation']['value'])

    def sections_follow_keys():
        stocked(cur,today);owner=master.role_actor(cur,'OWNER');_,orows=read_all(cur,owner)
        fg_loc={r['location_id'] for r in fg_rows(cur,owner)[1]}
        mat_loc={r['location_id'] for r in material_rows(cur,owner) if r['material_type']!='ACCESSORY'}
        acc_loc={r['location_id'] for r in accessory_rows(cur,owner)}
        out={}
        actors=dict(FG_ONLY=custom(cur,(DASH,'warehouse.fg.view')),MATERIAL_ONLY=custom(cur,(DASH,'warehouse.material.view')),
                    ACCESSORY_ONLY=custom(cur,(DASH,'warehouse.accessory.view')),DASHBOARD_ONLY=custom(cur,(DASH,)),
                    PROCUREMENT=custom(cur,(DASH,'warehouse.procurement.view')),GUDANG=master.role_actor(cur,'GUDANG'),OWNER=owner)
        for name,subject in actors.items():
            keys=role_permissions(cur,subject);sec=expected_sections(keys)
            answer,rows=read_all(cur,subject)
            assert answer['sections']==sec,(name,answer['sections'],sec)
            assert all((answer['totals'][k] is None)==(not v) for k,v in sec.items()),(name,answer['totals'])
            assert all((x[k] is None)==(not v) for x in rows for k,v in sec.items()),name
            want=(mat_loc if sec['materials'] else set())|(acc_loc if sec['accessories'] else set())|(fg_loc if sec['finished_goods'] else set())
            assert {x['location_id'] for x in rows}==want,(name,len(want))
            assert sorted(x['kind'] for x in answer['attention'])==expected_attention(keys),(name,answer['attention'])
            if sec==dict(materials=True,accessories=True,finished_goods=True):
                assert quantities(rows)==quantities(orows),name
            out[name]=dict(sections=[k for k,v in sec.items() if v],locations=len(rows),checks=len(answer['attention']))
        g=out['GUDANG'];assert g['sections']==['materials','accessories','finished_goods'] and 'warehouse.stock.adjust' not in role_permissions(cur,actors['GUDANG'])
        return dict(status='PASS',per_role=out,catalog_keys=dict(page=DASH,**SECTION_KEYS))

    def denied():
        f=cut_roll(cur,today,0);before=b.boundary.snapshot(cur)
        nodash=custom(cur,tuple(SECTION_KEYS.values())+('finance.hpp.view','warehouse.stock.adjust','master.fabric.view'))
        qc=master.role_actor(cur,'PRODUKSI_QC');assert DASH not in role_permissions(cur,qc)
        inactive=master.role_actor(cur,'OWNER');cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(inactive,))
        before=b.boundary.snapshot(cur)
        out=dict(no_dashboard_key=refused(cur,lambda:read(cur,dict(q=f['code']),nodash),'CP7_WAREHOUSE_SUMMARY_DENIED'),
                 produksi_qc=refused(cur,lambda:read(cur,{},qc),'CP7_WAREHOUSE_SUMMARY_DENIED'),
                 inactive_user=refused(cur,lambda:read(cur,{},inactive),'CP7_WAREHOUSE_SUMMARY_DENIED'),
                 unknown_user=refused(cur,lambda:read(cur,{},str(uuid.uuid4())),'CP7_WAREHOUSE_SUMMARY_DENIED'))
        def as_role(role):
            b.api.admin(cur);cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps(dict(sub=str(uuid.uuid4()),role=role)),))
            cur.execute(f'set local role {role}');return one(cur,"select public.erp_cp7_get_warehouse_summary_v1('{}'::jsonb)")
        out['anon']=refused(cur,lambda:as_role('anon'),'permission denied')
        out['service_role']=refused(cur,lambda:as_role('service_role'),'permission denied')
        out['jwt_role_anon']=refused(cur,lambda:auth.actor(cur,None,'anon') or one(cur,"select public.erp_cp7_get_warehouse_summary_v1('{}'::jsonb)"),'CP7_WAREHOUSE_SUMMARY_DENIED')
        for name,q in (('unknown_key',dict(location_id=str(f['location']))),('limit_0',dict(limit=0)),('limit_101',dict(limit=101)),('limit_text',dict(limit='5')),
                       ('offset_negative',dict(offset=-1)),('q_number',dict(q=5)),('q_long',dict(q='x'*121)),('not_object',[1])):
            out['query_'+name]=refused(cur,lambda:read(cur,q),'CP7_WAREHOUSE_SUMMARY_QUERY')
        cp17().unchanged(cur,before,'warehouse summary refusals')
        assert DASH in role_permissions(cur,master.role_actor(cur,'GUDANG'))
        return dict(status='PASS',errcode='42501',**out)

    def attention():
        owner=master.role_actor(cur,'OWNER');gudang=master.role_actor(cur,'GUDANG')
        def observed(subject):
            r=read(cur,dict(limit=1),subject);return {x['kind']:int(x['count']) for x in r['attention']},r
        def check(label):
            o,r=observed(owner);_,att=native(cur,at(r['read_at']))
            assert o==att,(label,o,att);return o,r
        start,_=check('before')
        import cp7_material_count_cases as count
        import cp7_fg_adjustment_cases as fgadj
        receipt.command(cur,'SAVE_DRAFT',receipt.fixture(cur,today)['payload'])
        m=material.fixture(cur,today);material.draft(cur,m)
        count.draft(cur,material.fixture(cur,today))
        f=fg.fixture(cur,today);fgadj.draft(cur,f)
        t=master.tag();fab=master.create(cur,'FABRIC',master.fabric_fields('KAIN-'+t,minimum_stock_qty='50'))
        after,r=check('after')
        delta={k:after[k]-start.get(k,0) for k in after}
        assert {k:delta[k] for k in ('RECEIPT_DRAFT','MATERIAL_TRANSFER_DRAFT','MATERIAL_COUNT_DRAFT','FG_ADJUSTMENT_DRAFT','FABRIC_BELOW_MINIMUM')}==dict(
            RECEIPT_DRAFT=1,MATERIAL_TRANSFER_DRAFT=1,MATERIAL_COUNT_DRAFT=1,FG_ADJUSTMENT_DRAFT=1,FABRIC_BELOW_MINIMUM=1),delta
        low=next(x for x in r['attention'] if x['kind']=='FABRIC_BELOW_MINIMUM')
        assert len(low['rows'])==min(10,after['FABRIC_BELOW_MINIMUM']) and all(D(x['qty'])<D(x['minimum_qty']) for x in low['rows'])
        b.api.admin(cur);assert one(cur,'select minimum_stock_qty from erp.fabric_master_profiles where material_id=%s',(fab['id'],))==50
        g,_=observed(gudang);keys=role_permissions(cur,gudang)
        assert sorted(g)==expected_attention(keys) and all(g[k]==after[k] for k in g),(g,after)
        return dict(status='PASS',checks=sorted(after),increments=delta,equals_native_tables=True,gudang_checks=sorted(g))

    def read_only_private():
        verified=bundle.verify(cur);stocked(cur,today);owner=master.role_actor(cur,'OWNER');gudang=master.role_actor(cur,'GUDANG')
        before=b.boundary.snapshot(cur);cur.execute('savepoint r303_read_only');cur.execute('set local transaction_read_only=on')
        try:
            for subject in (owner,gudang):read_all(cur,subject)
            read(cur,dict(q='zzz-tidak-ada-'+uuid.uuid4().hex),owner)
        finally:cur.execute('rollback to savepoint r303_read_only');b.api.admin(cur)
        cp17().unchanged(cur,before,'warehouse summary reads')
        empty=read(cur,dict(q='zzz-tidak-ada-'+uuid.uuid4().hex),owner)
        assert empty['page']==dict(rows=[],total='0',offset=0,limit=25,next_offset=None) and empty['business_DML'] is False
        for name in ('access_now()','workspace(jsonb)'):
            for who in bundle.OUTSIDERS:
                assert not one(cur,"select has_function_privilege(%s,%s,'EXECUTE')",(who,bundle.SCHEMA+'.'+name)),(who,name)
        return dict(status='PASS',bundle=verified,reads_in_read_only_transaction=True,boundary_unchanged=True,empty_search=empty['page'])

    named=[receipt_cutting,values_only_with_hpp,sections_follow_keys,denied,attention,read_only_private]
    assert len(named)==len(NATIVE)
    return list(zip(NATIVE,named))


def races(tools,today):
    def transfer_during_read():
        """A writer moves 0.1 of the roll from A to B through the Native transfer post, commit after commit; every answer read
        meanwhile holds A + B = 10 and its total equals its rows, also when a commit lands while the read runs."""
        with tools.connect()as conn,conn.cursor()as cur:
            f=material.fixture(cur,today);owner=master.role_actor(cur,'OWNER');b.api.admin(cur)
            unit=one(cur,'select unit_code from erp.materials where id=%s',(f['material'],));conn.commit()
        commits=[];done=threading.Event();errors=[]
        def writer():
            try:
                with tools.connect()as conn,conn.cursor()as cur:
                    for _ in range(60):
                        d,_p=material.draft(cur,f,qty='0.1');material.post(cur,d);conn.commit();commits.append(time.monotonic())
            except Exception as e:errors.append(str(e).splitlines()[0])
            finally:done.set()
        reads=[];seen=set();during=0
        with ThreadPoolExecutor(max_workers=1)as pool:
            future=pool.submit(writer)
            with tools.connect()as conn,conn.cursor()as cur:
                while not done.is_set() or len(reads)<5:
                    started=time.monotonic();r=read(cur,dict(q=f['tag']),owner);ended=time.monotonic();conn.commit()
                    rows={x['location_id']:x for x in r['page']['rows']}
                    qty=lambda loc:sum((D(l['qty']) for l in rows[loc]['materials']['lines'] if l['unit_code']==unit),D(0)) if loc in rows else D(0)
                    a,bq=qty(f['location']),qty(f['destination'])
                    total=sum((D(l['qty']) for l in r['totals']['materials']['lines'] if l['unit_code']==unit),D(0))
                    assert a+bq==total==D(10) and (a*10)%1==0,('CP7_R3_03_HALF_APPLIED',str(a),str(bq),str(total))
                    seen.add((str(a),str(bq)));reads.append((started,ended))
                    if len(reads)>2000:break
            future.result(timeout=300)
        assert not errors,errors
        during=sum(1 for s,e in reads if any(s<c<e for c in commits))
        with tools.connect()as conn,conn.cursor()as cur:
            b.api.admin(cur)
            final=dict(cur.execute('select location_id::text,sum(qty_signed) from erp.material_stock_movements where roll_id=%s group by 1',(f['roll'],)).fetchall())
        assert final=={f['location']:D(4),f['destination']:D(6)} and len(commits)==60,final
        assert during>0 and len(seen)>=2,('CP7_R3_03_NO_READ_OVERLAPPED_A_COMMIT',during,len(seen))
        return dict(status='PASS',transfers_committed=len(commits),reads=len(reads),reads_with_a_commit_inside=during,states_seen=len(seen),
                    every_answer_A_plus_B=10,final=dict(A='4',B='6'))
    return list(zip(RACES,[transfer_during_read]))


def http_cases(http,today):
    def owner_gudang_denied():
        owner=http.login('OWNER','cp17-r3-03-owner');gudang=http.login('GUDANG','cp17-r3-03-gudang')
        code='CP17_R303_NODASH_'+uuid.uuid4().hex[:8].upper()
        with http.connect()as conn,conn.cursor()as cur:
            g=cut_roll(cur,today);a=unrolled.fixture(cur,today,'ACCESSORY');b.api.admin(cur)
            role=cur.execute("insert into erp.app_roles(role_code,role_name,is_system,is_protected,is_active)values(%s,'CP17 R3-03 tanpa ringkasan gudang',false,false,true)returning id",(code,)).fetchone()[0]
            for key in tuple(SECTION_KEYS.values())+('finance.hpp.view',):cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)',(role,key))
            conn.commit()
        nodash=http.login(code,'cp17-r3-03-nodash')
        o=owner.rpc('erp_cp7_get_warehouse_summary_v1',dict(p_query=dict(q=g['code'])));assert o['status']==200,o
        gd=gudang.rpc('erp_cp7_get_warehouse_summary_v1',dict(p_query=dict(q=g['code'])));assert gd['status']==200,gd
        with http.connect()as conn,conn.cursor()as cur:
            native_rows=location_rows(cur,g['location'],at(o['body']['read_at']));keys=role_permissions(cur,gudang.auth_user_id);conn.rollback()
        line=o['body']['page']['rows'][0]['materials']['lines'][0]
        assert (D(line['qty']),line['rolls'])==(sum(r[2] for r in native_rows),'1')==(D(6),'1'),(line,native_rows)
        assert D(o['body']['page']['rows'][0]['materials']['valuation']['value'])==sum(q6(r[2]*r[3]) for r in native_rows)
        assert gd['body']['financial_captured'] is False and 'valuation' not in json.dumps(gd['body'])
        assert quantities(gd['body']['page']['rows'])==quantities(o['body']['page']['rows'])
        assert sorted(x['kind'] for x in gd['body']['attention'])==expected_attention(keys) and 'MATERIAL_COUNT_DRAFT' in {x['kind'] for x in o['body']['attention']}
        # The accessory receipt's location through both roles.
        ao=owner.rpc('erp_cp7_get_warehouse_summary_v1',dict(p_query=dict(q=a['tag'])))['body'];ag=gudang.rpc('erp_cp7_get_warehouse_summary_v1',dict(p_query=dict(q=a['tag'])))['body']
        acc=[x for x in ao['page']['rows'] if x['location_id']==a['location']][0]['accessories']['lines']
        assert [(D(l['qty']),l['items'])for l in acc]==[(D(10),'1')] and quantities(ag['page']['rows'])==quantities(ao['page']['rows']),acc
        denied=nodash.rpc('erp_cp7_get_warehouse_summary_v1',dict(p_query={}))
        assert denied['status']==403 and 'CP7_WAREHOUSE_SUMMARY_DENIED' in json.dumps(denied['body']),denied
        anon=http.anon_rpc('erp_cp7_get_warehouse_summary_v1',dict(p_query={}));assert anon['status'] in(401,403),anon
        bad=owner.rpc('erp_cp7_get_warehouse_summary_v1',dict(p_query=dict(limit=101)));assert bad['status']>=400 and 'CP7_WAREHOUSE_SUMMARY_QUERY' in json.dumps(bad['body']),bad
        return dict(status='PASS',real_Auth=True,owner=dict(qty='6',rolls=1,value=True),gudang=dict(no_value=True,same_quantities=True,checks=sorted(x['kind'] for x in gd['body']['attention'])),
                    without_dashboard_key=denied['status'],anon=anon['status'],bad_query=bad['status'])
    return list(zip(HTTP,[owner_gudang_denied]))


# ---------------------------------------------------------------- browser fixture (committed on the browser copy)
def id_number(x):
    """id-ID text as the screen writes it: '.' between thousands, ',' before the decimals, no trailing zeros."""
    s=format(D(x).normalize(),'f');neg=s.startswith('-');s=s.lstrip('-');w,_,f=s.partition('.')
    w='{:,}'.format(int(w)).replace(',','.')
    return ('-' if neg else '')+w+(','+f if f else '')
def browser_fixture(cur,today):
    """A roll of 10 received and 4 cut through Buat Potongan at its own warehouse (the native case's fixture), committed."""
    g=cut_roll(cur,today);b.api.admin(cur)
    return dict(location=str(g['location']),code=g['code'],name=one(cur,'select location_name from erp.locations where id=%s',(g['location'],)),unit=g['unit'],roll=str(g['roll']))
def browser_state(cur,p):
    """Native rows of the fixture location: quantity and roll count as the screen should write them, and the value text."""
    now=one(cur,'select statement_timestamp()');rows=location_rows(cur,p['location'],now)
    qty=sum((r[2] for r in rows),D(0));value=sum((q6(r[2]*r[3]) for r in rows if r[3] is not None),D(0))
    return dict(qty=str(qty),qty_text=id_number(qty)+' '+p['unit'],rolls=sum(1 for r in rows if r[1] is not None and r[2]>0),
                value_text='Rp'+id_number(q2(value)),movements=one(cur,'select count(*) from erp.material_stock_movements where location_id=%s',(p['location'],)))
