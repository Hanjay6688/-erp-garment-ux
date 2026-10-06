#!/usr/bin/env python3
"""P19 equivalence check: old (git ref) vs working-tree definitions of the
fabric plan/needs/recipe_state and the reminder condition_rows, compared as
exact JSON text on random edge-case and clean datasets.

LOCAL_PG16_DEV tool for auditors and writers, not qualification evidence.
Requires a disposable database that already has the CP7 analysis and reminder
bundles installed. Everything runs in one transaction that is rolled back.

usage: cp7_p19_equivalence.py DSN BASE_REF [N_PER_MODE] [SEED]
"""
import json,random,subprocess,sys,uuid
from pathlib import Path
import psycopg
ROOT=Path(__file__).resolve().parents[1]
FABRIC='scripts/cp7-src/planning/fabric-requirements.sql';REMINDER='scripts/cp7-src/reminders/rule-condition-source.sql'

def functions(src,schema,prefix,names,internal):
    out=[]
    for name in names:
        i=src.index(f'create function {prefix}.{name}(');j=src.index('$$;',src.index('$$',i)+2)+3
        f=src[i:j].replace(f'create function {prefix}.{name}(',f'create function {schema}.{name}(',1)
        for o in internal:f=f.replace(f'{prefix}.{o}(',f'{schema}.{o}(')
        out.append(f)
    return '\n'.join(out)
def install(cur,ref):
    old={p:subprocess.check_output(['git','-C',str(ROOT),'show',f'{ref}:{p}'],text=True)for p in(FABRIC,REMINDER)}
    new={p:(ROOT/p).read_text()for p in(FABRIC,REMINDER)}
    for schema,src in(('p19_old',old),('p19_new',new)):
        cur.execute(f'create schema {schema}')
        cur.execute(functions(src[FABRIC],schema,'cp7_fabric_native',('index','recipe_state','plan','needs'),('index','recipe_state','plan')))
        cur.execute(functions(src[REMINDER],schema,'cp7_reminder_native',('condition_rows',),()))

rnd=random.Random(int(sys.argv[4]) if len(sys.argv)>4 else 20261006);pick=rnd.choice
U=lambda:str(uuid.UUID(int=rnd.getrandbits(128),version=4))
def clean_dataset():
    M=rnd.randint(1,3);mats=[{'id':U(),'material_sku':f'F{i}','material_name':f'Kain {i}','material_type':'FABRIC','unit_code':'M','is_active':True,'accessory_category_id':None,'created_at':'2025-01-01T00:00:00+00:00'} for i in range(M)]
    good={'id':U(),'location_type':'RAW_MATERIAL_WAREHOUSE','is_active':True};locs=[good]+([{'id':U(),'location_type':'CUTTING_AREA','is_active':True}] if rnd.random()<0.2 else [])
    T=rnd.randint(1,6);targets=[f'{U()}:{U()}' for _ in range(T)];tm={t:pick(mats)['id'] for t in targets}
    sel=[{'id':U(),'revision':'1','target_key':t,'config':{'material_id':tm[t],'unit':'M','qty_per_good_pcs':pick(['1.5','2','0.5']),'material_hash':None,'pattern_id':None}} for t in targets]
    rolls=[{'id':U(),'material_id':pick(mats)['id'],'status':pick(['AVAILABLE','HALF_USED']),'consistent':True,
      'stock':[{'location_id':good['id'],'qty':pick(['10','40','100','250','3'])}]} for _ in range(rnd.randint(0,8))]
    if rnd.random()<0.1 and rolls:rolls[0]['stock'][0]['qty']='-2'
    drafts=[]
    for _ in range(rnd.randint(0,3)):
        t=pick(targets);rs=[r for r in rolls if r['material_id']==tm[t]] or rolls
        if not rs:break
        drafts.append({'id':U(),'revision':'1','source_location_id':good['id'] if rnd.random()<0.9 else locs[-1]['id'],
          'intents':[{'id':U(),'target_key':t}] if rnd.random()<0.9 else [],
          'lines':[{'id':U(),'roll_id':pick(rs)['id'],'qty_issued':pick(['1','5','8','30'])} for _ in range(rnd.randint(1,2))]})
    coms=[{'id':U(),'commitment_id':U(),'po_number':f'PO{i}','line_number':'1','material_id':pick(mats)['id'],
       'location_id':good['id'] if rnd.random()<0.85 else locs[-1]['id'],'expected_date':pick(['2026-10-01','2026-10-06','2026-10-10','2026-11-30',None,'2026-10-12']),
       'remaining':pick(['100','0','12.5','40'])} for i in range(rnd.randint(0,3))]
    rows=[{'target_key':t,'conditional_gap_pcs':pick(['93','0','10','40','150']),'refs':[],'production_policy':{'policy':{'state':pick(['ACTIVE']*6+['PAUSED'])}},
      'net':{'inputs':{'deadline':pick(['2026-10-20T00:00:00Z','2026-10-08T00:00:00Z','2026-12-31T00:00:00Z',None])}}} for t in targets]
    match=[{'target_key':pick(targets),'result':{'match':'UNKNOWN'}}] if rnd.random()<0.15 else []
    c={'captured_at':'2026-10-06T00:00:00Z','fabric_source':{'selected':sel,'materials':mats,'patterns':[],
      'physical':{'contract_version':'cp7.fabric-physical.v1','drafts':drafts,'rolls':rolls,'locations':locs,'commitments':coms}}}
    return c,{'match_results':match,'rows':rows}
def dataset():
    M=rnd.randint(1,4);mats=[]
    for i in range(M):
        mats.append({'id':U(),'material_sku':f'F{i}','material_name':f'Kain {i}','material_type':pick(['FABRIC']*5+['ACCESSORY']),
          'unit_code':pick(['M','M','M','yd']),'is_active':pick([True]*6+[False]),'accessory_category_id':None,'created_at':'2025-01-01T00:00:00+00:00'})
    locs=[{'id':U(),'location_type':pick(['RAW_MATERIAL_WAREHOUSE']*3+['CUTTING_AREA']),'is_active':pick([True]*4+[False])} for _ in range(rnd.randint(1,3))]
    extra_loc=U()
    T=rnd.randint(1,12);targets=[f'{U()}:{U()}' for _ in range(T)]
    pats=[{'id':U(),'pattern_code':'P1','revision':'1','is_active':pick([True,True,False])} for _ in range(rnd.randint(0,2))]
    sel=[]
    for t in targets:
        if rnd.random()<0.15:continue
        m=pick(mats);pid=pick([None,None]+[p['id'] for p in pats]+[U()])
        sel.append({'id':U(),'revision':str(rnd.randint(1,3)),'target_key':t,'config':{'material_id':pick([m['id']]*8+[U()]),'unit':pick([m['unit_code']]*6+['PCS']),
          'qty_per_good_pcs':pick(['1.5','2','0.75','3.125']),'material_hash':'BAD' if rnd.random()<0.08 else None,'pattern_id':pid,'pattern_hash':'BAD' if rnd.random()<0.3 else None}})
    rolls=[]
    for _ in range(rnd.randint(0,20)):
        st=[]
        for l in rnd.sample(locs+[{'id':extra_loc}],k=rnd.randint(0,2)):
            st.append({'location_id':l['id'],'qty':pick(['10','4','0.5','25','-3','7.25'])})
        r={'id':U(),'material_id':pick([m['id'] for m in mats]+[U()]),'status':pick(['AVAILABLE','AVAILABLE','HALF_USED','USED','RESERVED']),'stock':st}
        c=rnd.random()
        if c<0.85:r['consistent']=True
        elif c<0.95:r['consistent']=False
        rolls.append(r)
    drafts=[]
    for _ in range(rnd.randint(0,8)):
        intents=[{'id':U(),'target_key':pick(targets)} for _ in range(pick([0,1,1,1,2]))]
        if intents and rnd.random()<0.2:intents.append({'id':U(),'target_key':intents[0]['target_key']})
        lines=[{'id':U(),'roll_id':(pick(rolls)['id'] if rolls and rnd.random()<0.9 else U()),'qty_issued':pick(['1','2.5','6','12','0.25'])} for _ in range(pick([0,1,1,2,3]))]
        d={'id':U(),'revision':str(rnd.randint(1,5)),'source_location_id':pick([l['id'] for l in locs]+[None,extra_loc]),'intents':intents,'lines':lines}
        drafts.append(d)
    coms=[{'id':U(),'commitment_id':U(),'po_number':f'PO{i}','line_number':'1','material_id':pick([m['id'] for m in mats]+[U()]),
       'location_id':pick([l['id'] for l in locs]+[extra_loc]),'expected_date':pick(['2026-10-01','2026-10-06','2026-10-10','2026-11-30',None]),
       'remaining':pick(['100','0','12.5','-1','3'])} for i in range(rnd.randint(0,6))]
    rows=[]
    for t in targets:
        r={'target_key':t,'conditional_gap_pcs':pick(['93','0','10','1.5',None]),'refs':[{'kind':'X','id':t,'revision':'1'}],
           'net':{'inputs':{'deadline':pick(['2026-10-20T00:00:00Z','2026-10-07T00:00:00Z',None])}}}
        pol=pick(['ACTIVE','ACTIVE','PAUSED','STOPPED',None])
        r['production_policy']={'policy':{'state':pol}} if pol else {}
        rows.append(r)
    match=[{'target_key':pick(targets),'result':{'match':pick(['UNKNOWN','NEEDS_CHECK','CONFIRMED_TARGET'])}} for _ in range(rnd.randint(0,2))]
    phys={'contract_version':'cp7.fabric-physical.v1','drafts':drafts,'rolls':rolls,'locations':locs,'commitments':coms}
    if rnd.random()<0.05:phys=None
    fs={'selected':sel,'materials':mats,'patterns':pats}
    if phys is not None:fs['physical']=phys
    c={'captured_at':pick(['2026-10-06T00:00:00Z','2026-10-05T18:30:00Z']),'fabric_source':fs}
    return c,{'match_results':match,'rows':rows}
def fact(unit):
    st=pick(['KNOWN','ASSUMED','UNKNOWN','ASSUMED'])
    f={'state':st,'unit':unit,'refs':[{'kind':'X','id':U(),'revision':'1'}]}
    if st!='UNKNOWN':f['value']=pick(['0','10','150','3.5'])
    else:f['reason']=pick(['SOURCE_INPUT_NOT_PROVEN','FABRIC_WIP_IDENTITY_UNRESOLVED'])
    return f
def condition_dataset():
    T=rnd.randint(0,8);ts=[f'{U()}:{U()}' for _ in range(T)]
    recs=[{'target':{'kind':'PRODUCT','key':t,'product_id':t.split(':')[0]},'production_state':pick(['ACTIVE','PAUSED']),'q_conditional':fact('PCS')} for t in ts]
    needs=[]
    for t in ts:
        for _ in range(rnd.randint(0,2)):needs.append({'target_key':t,'material_key':pick([f'ACCESSORY:{U()}']*4+[None]),'additional_external':fact('PCS')})
        if rnd.random()<0.7:needs.append({'target_key':t,'material_key':pick([f'FABRIC_MATERIAL:{U()}',f'FABRIC_UNREVIEWED:{t}']),'additional_external':fact(pick(['M','yd']))})
    labels=[]
    for t in ts:
        if rnd.random()<0.85:labels.append({'target_key':t,'sku':pick(['S1','S2',None]),'product_name':pick(['Kemeja','Celana'])})
        if rnd.random()<0.2:labels.append({'target_key':t,'sku':'DUP','product_name':'Duplikat'})
    if rnd.random()<0.1:labels.append({'target_key':None,'sku':'N','product_name':'tanpa'})
    rnd.shuffle(labels)
    e={'source_state':pick(['UNCHANGED']*5+['ARCHIVED_STALE']),'analysis':{'semantic_hash':U(),'recommendations':recs,'material_needs':needs},'product_labels':labels}
    ar=None
    if rnd.random()<0.6:
        ids=[U() for _ in range(rnd.randint(0,5))];pages=[]
        for _ in range(rnd.randint(1,3)):
            rows=[]
            for _ in range(rnd.randint(0,3)):
                if not ids:break
                rows.append({'id':pick(ids),'due_date':pick(['2026-10-01','2026-10-10',None]),'number':f'INV-{rnd.randint(1,99)}','customer_name':'Pelanggan','financial':{'open_balance':pick(['100.00',None,'0.00'])},'amount':rnd.randint(1,500)})
            pages.append({'page':{'rows':rows}})
        conds=[{'source_id':i,'state':pick(['OVERDUE','DUE_TODAY','ZERO_BALANCE','NOT_DUE_YET','DRAFT_ONLY','INACTIVE_DOCUMENT','UNKNOWN_X']),'source_revision':'1','native_source_hash':U(),'business_resolved':pick([True,False])} for i in set(r['id'] for p in pages for r in p['page']['rows'])]
        if rnd.random()<0.1:conds.append({'source_id':U(),'state':'OVERDUE','source_revision':'1','native_source_hash':U(),'business_resolved':False})
        ar={'as_of':'2026-10-06','conditions':conds,'pages':pages}
    ap=None
    if rnd.random()<0.5:
        ap={'as_of':'2026-10-06','rows':[{'condition':{'state':pick(['OVERDUE','NOT_DUE_YET','INVOICE_PENDING','ZERO_BALANCE']),'source_revision':'1','native_source_hash':U(),'business_resolved':False},
            'liability':{'purchase_id':U(),'purchase_number':'PB-1','supplier_name':pick(['Pemasok A',None])},'due_date':pick(['2026-10-01',None]),'balance':{'remaining':pick(['50.00',None])}} for _ in range(rnd.randint(0,3))]}
    pol=[]
    if rnd.random()<0.6:
        for rule in['PRODUCTION_GAP','ACCESSORY_NEED','FABRIC_NEED','AR_DUE','AP_DUE']:
            if rnd.random()<0.7:
                unit={'PRODUCTION_GAP':'PCS','ACCESSORY_NEED':'PCS','FABRIC_NEED':pick(['M','yd']),'AR_DUE':'DAY','AP_DUE':'DAY'}[rule]
                pol.append({'policy_id':U(),'rule_id':rule,'scope_kind':'GLOBAL','scope_key':'*','revision':'1','previous_id':None,
                  'config':{'enabled':pick([True,True,False]),'threshold_value':pick(['0','5','100']),'threshold_unit':unit,'cooldown_minutes':'0',
                  'quiet':{'enabled':False,'starts_at':None,'ends_at':None,'timezone':'Asia/Jakarta'}},'reason':'fixture','created_at':'2026-10-05T00:00:00Z','created_by':U()})
    return e,ar,ap,pol

def fabric_case(cur,mode):
    c,n=clean_dataset() if mode=='clean' else dataset()
    h={x[0]:x[1] for x in cur.execute("select x->>'id',cp7_fabric_native.material_hash(x) from jsonb_array_elements(%s::jsonb)x",(json.dumps(c['fabric_source']['materials']),)).fetchall()}
    for s in c['fabric_source']['selected']:
        cfg=s['config']
        if cfg.get('material_hash')!='BAD':cfg['material_hash']=h.get(cfg['material_id'],'MISSING')
        p=next((x for x in c['fabric_source']['patterns'] if x['id']==cfg.get('pattern_id')),None)
        if p is not None and cfg.get('pattern_hash')!='BAD':
            cfg['pattern_hash']=cur.execute("select encode(extensions.digest(convert_to(%s::jsonb::text,'UTF8'),'sha256'),'hex')",(json.dumps(p),)).fetchone()[0]
    res=[]
    for schema in('p19_old','p19_new'):
        cur.execute('savepoint s')
        try:
            plan=cur.execute(f'select {schema}.plan(%s::jsonb,%s::jsonb)',(json.dumps(c),json.dumps(n))).fetchone()[0]
            rows=[cur.execute(f"select {schema}.needs(%s::jsonb,%s::jsonb,'[\"A\"]'::jsonb,%s::jsonb)::text",(json.dumps(c),json.dumps(r),json.dumps(plan))).fetchone()[0] for r in n['rows']]
            core=dict(targets=json.dumps(plan.get('targets'),sort_keys=True),source=plan.get('physical_source'),
              index=json.dumps(plan['index'] if 'index' in plan else {k:plan[k] for k in('selected','materials','patterns')},sort_keys=True))
            res.append(('OK',core,rows));cur.execute('release savepoint s')
        except psycopg.Error as e:cur.execute('rollback to savepoint s');res.append(('ERR',str(e).split(chr(10))[0]))
    return res[0]==res[1],res[0][0]
def condition_case(cur):
    e,ar,ap,pol=condition_dataset();res=[]
    for schema in('p19_old','p19_new'):
        cur.execute('savepoint s')
        try:res.append(('OK',cur.execute(f"select {schema}.condition_rows(%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,'2026-10-06T03:00:00Z')::text",
            (json.dumps(e),json.dumps(ar) if ar is not None else None,json.dumps(ap) if ap is not None else None,json.dumps(pol))).fetchone()[0]));cur.execute('release savepoint s')
        except psycopg.Error as x:cur.execute('rollback to savepoint s');res.append(('ERR',str(x).split(chr(10))[0]))
    return res[0]==res[1],res[0][0]
def main():
    dsn,ref=sys.argv[1],sys.argv[2];n=int(sys.argv[3]) if len(sys.argv)>3 else 300
    report=dict(contract='cp7.p19-equivalence.v1',base_ref=ref,local_only=True,qualification=False,suites={})
    with psycopg.connect(dsn) as conn,conn.cursor() as cur:
        install(cur,ref)
        for suite,fn in(('fabric_edge',lambda:fabric_case(cur,'edge')),('fabric_clean',lambda:fabric_case(cur,'clean')),('condition_rows',lambda:condition_case(cur))):
            same=diff=errors=0
            for _ in range(n):
                ok,kind=fn()
                if not ok:diff+=1
                elif kind=='ERR':errors+=1
                else:same+=1
            report['suites'][suite]=dict(datasets=n,identical_result=same,identical_refusal=errors,mismatch=diff)
        conn.rollback()
    report['status']='PASS' if all(s['mismatch']==0 for s in report['suites'].values()) else 'FAIL'
    print(json.dumps(report,indent=1))
    sys.exit(0 if report['status']=='PASS' else 1)
if __name__=='__main__':main()
