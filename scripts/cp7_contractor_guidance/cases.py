"""OW-05b Native cases: the Mandor correction workspace names real menus, lists every redo step, shows its history.

Business rows come only from the retained writers (the OW05 correction fixture and command, sewing, the CP17
laundry/QC/FG chain and PO finish). The original OW05 readers are read side by side on the same state inside a
rolled-back savepoint, so every case shows that only the guidance text, menu, source link, after steps and history
are added; blocker rows, order, ids, statuses and the correction command stay the same.
"""
from pathlib import Path
import json
import re
import uuid

from cp7_contractor_correction import native_cases as n
from cp7_contractor_guidance import native_delta
import cp7_r3_hpp_pool_cases as hp

auth=n.auth
b=auth.b
IDS=('OW05B_REAL_CHAIN_BLOCKERS_NAME_REAL_MENUS_AND_OPEN',
     'OW05B_EVERY_KIND_AND_BRANCH_GUIDED',
     'OW05B_AFTER_STEPS_COMPLETE_IN_ORDER',
     'OW05B_HISTORY_TWO_CORRECTIONS_VISIBLE',
     'OW05B_CORRECTION_COMMAND_UNCHANGED',
     'OW05B_GUIDANCE_READERS_PRIVATE')
REASON='OW05b petunjuk koreksi mandor'
ORIGINALS=None  # set by the probe: the exact OW05 definitions this stage replaced
AS_OWNER=None   # set by the probe: the verified predecessor role switch
APP=Path(__file__).resolve().parents[2]/'src/App.tsx'
STALE=('layar Nota/Gaji','WIP & Jahit','layar PO','Bahan Mandor','layar BS','layar Pool HPP','layar Kain Kantong','layar Bahan')
AFTER_MENUS=('Produksi › WIP & Sewing','Keuangan › Nota Ambil Aksesori','Produksi › Laundry','Produksi › QC & Final SKU',
             'Produksi › Barang BS & Rework','Penjualan › Penjualan & Invoice','Gudang › Kain kantong',
             'Keuangan › HPP & Rekalkulasi','Keuangan › Payroll & Kasbon')
SOURCES={'PAYROLL':'PAYROLL_PAYMENT','QC':'QC_INSPECTION','LAUNDRY':'LAUNDRY_DELIVERY','REWORK':'REWORK_ORDER',
         'MATERIAL_ISSUE':'CONTRACTOR_MATERIAL_RECEIVABLE','PICKUP_DRAFT':'CUTTING_GROUP','FG_LOT':'QC_ITEM',
         'ACCESSORY_NOTE':'QC_ITEM','BS':'QC_ITEM'}


def one(cur,sql,args=()):
    return cur.execute(sql,args).fetchone()[0]


def nav():
    """The app's own menu: section -> items, read from src/App.tsx (the sidebar the operator sees)."""
    text=APP.read_text()
    block=re.search(r"\n  Produksi: \[.*?\n  Keuangan: \[[^\]]*\],",text,re.S).group(0)
    return {m.group(1):re.findall(r"'([^']+)'",m.group(2))for m in re.finditer(r"\n  ([A-Za-z]+): \[([^\]]*)\]",block)}


def menus_in(text,menu):
    """Every 'Section › Item' named in a text must be an actual sidebar item."""
    found=[]
    for m in re.finditer(r'([A-Z][a-z]+) › ',text):
        items=menu.get(m.group(1))
        assert items is not None,('OW05B_UNKNOWN_MENU_SECTION',m.group(1),text)
        rest=text[m.end():]
        hit=[i for i in items if rest.startswith(i)]
        assert hit,('OW05B_UNKNOWN_MENU_ITEM',m.group(1),rest[:40])
        found.append(m.group(1)+' › '+max(hit,key=len))
    return found


def guided(item,menu):
    assert set(item)>={'order','kind','id','step','menu','source'},item
    assert isinstance(item['step'],str)and len(item['step'])>=20,item
    assert not any(s in item['step']for s in STALE),item
    named=menus_in(item['step'],menu)
    if item['menu']is None:
        assert'belum'in item['step']or item['kind']in('GROUP_STATE','WIP_HISTORY'),item
    else:
        assert menus_in(item['menu'],menu)==[item['menu']]and item['menu']in named,item
    if item['source']is not None:
        assert item['source']['source_type']==SOURCES[item['kind']],item
        uuid.UUID(item['source']['source_id'])
    return named


def original(cur,fn):
    """The same state read through the exact OW05 readers, then restored."""
    name='ow05b_original_'+uuid.uuid4().hex
    cur.execute('savepoint '+name)
    try:
        with AS_OWNER(cur,'postgres'):
            for sig in native_delta.SIGNATURES:cur.execute(ORIGINALS[sig],prepare=False)
        b.api.admin(cur)
        return fn()
    finally:
        cur.execute('rollback to savepoint '+name);cur.execute('release savepoint '+name);b.api.admin(cur)


def strip(item):
    return{k:v for k,v in item.items()if k not in('step','menu','source')}


def resolve(cur,source):
    auth.actor(cur)
    r=one(cur,'select public.erp_cp7_resolve_transaction_source_v1(%s::jsonb)',(json.dumps(source),))
    b.api.admin(cur);return r


def guide(cur,item):
    b.api.admin(cur)
    return one(cur,'select cp7_contractor_guidance.guide_v1(%s::jsonb)',(json.dumps(item),))


def cases(cur,today):
    menu=nav()

    def repost(g):
        # After a correction the retained sewing facade needs the explicit OLD/NEW rate choice (D16-2/3/4).
        w=n.old.sewing_workspace(cur,g)
        p=dict(action='RECORD',group_id=g['group'],qty_pcs='4',physical_at=g['at'](10).isoformat(),
            review_token=w['review_token'],change_reason=REASON,rate_choice='OLD')
        auth.actor(cur)
        one(cur,'select public.erp_cp7_save_sewing_completion_v1(%s,%s,%s)',(json.dumps(p),str(uuid.uuid4()),w['group_version']))
        b.api.admin(cur)

    def real_chain():
        assert one(cur,"select to_regprocedure('public.erp_cp7_resolve_transaction_source_v1(jsonb)')is not null")
        c=hp.cp17();f=c.finish_fixture(cur,today,label='OW05B-RC');po=f['po'];b.api.admin(cur)
        c.finish_command(cur,c.finish_workspace(cur,po),reason=REASON+' PO selesai')
        assert c.po_state(cur,po)['status']=='FINISHED'
        w=n.workspace(cur,po);old=original(cur,lambda:n.workspace(cur,po))
        kinds=[x['kind']for x in w['blockers']]
        # The finished chain's own blockers (Native6 3093e2d3 showed them; WORK_JOURNAL is covered by the every-kind case).
        assert {'PO_STATE','QC','FG_LOT','LAUNDRY','SEWING','WORK','GROUP_STATE','WIP_HISTORY'}<=set(kinds),kinds
        assert [strip(x)for x in w['blockers']]==[strip(x)for x in old['blockers']]
        assert set(w)==set(old)|{'after_steps','history'}and w['history']==[]
        assert all(w[k]==old[k]for k in old if k not in('blockers','review_token','after_step'))
        named={x['kind']:guided(x,menu)for x in w['blockers']}
        po_state=[x for x in w['blockers']if x['kind']=='PO_STATE'][0]
        assert po_state['menu']=='Keuangan › HPP & Rekalkulasi'and'Buka ulang PO'in po_state['step'],po_state
        opened={}
        for x in w['blockers']:
            if x['source']is None:continue
            r=resolve(cur,x['source']);d=r['document']
            opened[x['kind']+':'+x['id']]=dict(status=r['status'],route=d and d['route'],number=d and d['number'])
        routes={x['kind']:opened[x['kind']+':'+x['id']]['route']for x in w['blockers']if x['source']is not None}
        assert routes.get('QC')=='qc'and routes.get('LAUNDRY')=='laundry'and routes.get('FG_LOT')=='qc',opened
        assert all(v['status']=='AVAILABLE'for v in opened.values()),opened
        return dict(status='PASS',po=f['number'],kinds=kinds,menus_named=named,opened=opened,
            rows_order_ids_statuses_unchanged=True,old_screen_names_absent=list(STALE))

    def every_kind():
        kinds=native_delta.kinds(ORIGINALS[native_delta.BLOCKERS])
        assert kinds==native_delta.KINDS and len(kinds)==19,kinds
        probes=[]
        for kind in kinds:
            statuses={'PO_STATE':('FINISHED','ON_HOLD','CANCELLED'),'PAYROLL':('PAID','APPROVED','DRAFT'),
                      'MATERIAL_ISSUE':('DRAFT','POSTED'),'ACCESSORY_NOTE':('UNALLOCATED','ALLOCATED')}.get(kind,(None,))
            for status in statuses:
                item=dict(order=10,kind=kind,id=str(uuid.uuid4()),number='X-1',status=status,step='lama')
                out=guide(cur,item)
                assert strip(out)==strip(item),(item,out)
                probes.append(dict(kind=kind,status=status,menu=out['menu'],menus_named=guided(out,menu),
                    source=out['source']and out['source']['source_type'],step=out['step']))
        no_screen=sorted({p['kind']+':'+str(p['status'])for p in probes if p['menu']is None})
        # Random ids reach the 'no row' branches: manual BS, non-sewing work; PO hold/cancel and legacy scrap have no screen.
        assert no_screen==['BS:None','GROUP_STATE:None','PO_STATE:CANCELLED','PO_STATE:ON_HOLD','SCRAP:None','WIP_HISTORY:None',
            'WORK:None','WORK_JOURNAL:None'],no_screen
        detail=auth.refused(cur,lambda:guide(cur,dict(order=1,kind='NEW_KIND',id=str(uuid.uuid4()),step='x')),
            'CP7_MANDOR_GUIDANCE_KIND_UNKNOWN')
        return dict(status='PASS',kinds=len(kinds),probes=probes,without_screen_says_so=no_screen,unknown_kind_refused=detail,
            not_reached_with_real_rows=['MATERIAL_ISSUE non-accessory (kain/bahan) branch'])

    def after_steps():
        g=n.fixture(cur,today);w=n.workspace(cur,g['po'])
        assert w['eligible']and w['after_step'].startswith('Catat ulang hasil jahit'),w
        assert not any(s in w['after_step']for s in STALE)
        menus_in(w['after_step'],menu)
        steps=w['after_steps']
        assert tuple(s['menu']for s in steps)==AFTER_MENUS,steps
        for s in steps:
            assert set(s)=={'menu','step'}and menus_in(s['menu'],menu)==[s['menu']]and len(s['step'])>=20,s
            menus_in(s['step'],menu)
        return dict(status='PASS',after_step=w['after_step'],after_steps=steps)

    def history():
        g=n.fixture(cur,today);first=g['mandor'];other=n.fixture(cur,today)
        assert n.workspace(cur,g['po'])['history']==[]
        _,r=n.correct(cur,g)
        second=g['target']
        repost(g)
        w=n.workspace(cur,g['po'])
        assert not w['eligible']and len(w['history'])==1,w  # visible while blockers are open
        terminal=str(one(cur,"""select st.id from erp.sewing_terminal_events st where st.po_id=%s and st.event_kind='SELESAI_DIJAHIT'
            and not exists(select 1 from erp.sewing_terminal_events rv where rv.reversal_of_id=st.id)""",(g['po'],)))
        n.old.sewing_command(cur,n.old.sewing_workspace(cur,g),event=terminal)
        g['pickup']=r['replacements'][0]['new_pickup_id'];g['mandor']=second
        g['completion']=str(one(cur,"select id from erp.work_completion_events where po_id=%s and contractor_id=%s",(g['po'],second)))
        g['target']=n.old.mandor_row(cur,'OW05B-H-'+uuid.uuid4().hex[:8])
        n.correct(cur,g,generations=2)
        w=n.workspace(cur,g['po']);h=w['history']
        names=lambda cid:one(cur,'select contractor_name from erp.contractors where id=%s',(cid,))
        actor=one(cur,'select full_name from erp.app_users where auth_user_id=%s',(auth.base.OPERATOR_AUTH,))
        assert actor and[(x['old_contractor_id'],x['new_contractor_id'])for x in h]==[(second,g['target']),(first,second)],h
        assert all(x['old_contractor_name']==names(x['old_contractor_id'])and x['new_contractor_name']==names(x['new_contractor_id'])
            and x['reason']==n.REASON and x['actor_name']==actor and x['pickup_count']==1 for x in h),h
        assert h[0]['generation_no']>h[1]['generation_no']and h[0]['recorded_at']>=h[1]['recorded_at'],h
        stored=one(cur,'select count(*)from cp7_contractor_correction.history_v1 where po_id=%s',(g['po'],))
        assert stored==2 and n.workspace(cur,other['po'])['history']==[]
        return dict(status='PASS',history=h,newest_first=True,other_po_history_empty=True,visible_while_blocked=True)

    def command_unchanged():
        g=n.fixture(cur,today);w=n.workspace(cur,g['po'])
        old=original(cur,lambda:n.workspace(cur,g['po']))
        # The token is over the facts the operator decides on, not the wording of the guidance: same facts, same token,
        # so a reviewed workspace from before the guidance stage still corrects exactly as before.
        assert w['review_token']==old['review_token']
        key=str(uuid.uuid4());_,r=n.correct(cur,g,key)
        assert set(r)=={'contract_version','po_id','po_number','old_contractor_id','contractor_id','request_id','status',
            'replacements','sewing_repost_required','wage_history_reassigned'},r
        assert n.command(cur,n.payload(w,g['target']),key)==r
        stored=cur.execute('select reason,result from cp7_contractor_correction.history_v1 where po_id=%s',(g['po'],)).fetchall()
        assert stored==[(n.REASON,r)],stored
        return dict(status='PASS',response_keys=sorted(r),replay_identical=True,one_history_row=True)

    def private():
        details=[]
        for sql in('select cp7_contractor_guidance.history_v1(%s)','select cp7_contractor_guidance.guide_v1(%s::jsonb)',
                   'select cp7_contractor_guidance.after_steps_v1()'):
            args=(str(uuid.uuid4()),)if'history'in sql else(json.dumps(dict(kind='QC',id=str(uuid.uuid4()))),)if'guide'in sql else()
            def attempt(sql=sql,args=args):
                auth.actor(cur);return one(cur,sql,args)
            details.append(auth.refused(cur,attempt,'permission denied'))
        b.api.admin(cur)
        return dict(status='PASS',authenticated_direct_call_refused=details)

    operations=(real_chain,every_kind,after_steps,history,command_unchanged,private)
    assert len(operations)==len(IDS)
    return list(zip(IDS,operations))
