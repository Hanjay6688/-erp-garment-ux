#!/usr/bin/env python3
"""Random scenarios: AY vs AS per-account totals (open E), identical journals (closed E / non-invoice), no SQL errors."""
import random,subprocess,sys,uuid,json
S='/tmp/claude-0/-home-user--erp-garment-ux/6ab391f1-e30c-52b5-862e-6737ef5df873/scratchpad/rev7review/fuzz/'
PO='00000000-0000-0000-0000-0000000000a0'
def u(): return str(uuid.UUID(int=random.getrandbits(128)))
def ts(d,h=10): return f"((current_date-{d})+time '{h:02d}:00') at time zone 'Asia/Jakarta'"
def scen(seed,mode):
    random.seed(seed); q=[]
    E=random.randint(3,9)
    if mode!='noninv': q.append(f"insert into erp.settings values('E',(current_date-{E})::text);")
    if mode=='closed': q.append(f"update erp.accounting_period_control set closed_through=current_date-{E};")
    groups=[];batch=u() if random.random()<0.5 else None
    for gi in range(random.randint(1,3)):
        g=u();cut=random.randint(1,10);po=PO if gi==0 or random.random()<0.7 else u()
        b=batch if (batch and random.random()<0.7) else None
        pcs=random.choice([0,5,10,12])
        groups.append((g,po,b,cut,pcs))
        q.append(f"insert into erp.cutting_groups values('{g}','{po}',{repr(b) if b else 'null'},{ts(cut,8)});")
        q.append(f"insert into erp.v_cutting_group_totals values('{g}',{pcs});")
    if batch: q.append(f"insert into erp.v_cutting_batch_totals values('{batch}',{random.choice([0,sum(x[4] for x in groups if x[2]==batch)])});")
    marker=random.random()<0.8
    if marker: q.append(f"insert into erp.po_hpp_gl_material_state_v1 values('{PO}','SYNC',0,now()-interval '1 hour');")
    for (g,po,b,cut,pcs) in groups:
        for k in range(random.randint(0,3)):
            m=u();d=max(1,cut-random.randint(0,cut-1)) if k>0 else cut;ret=k>0 and random.random()<0.5
            qty=random.randint(1,5)*(1 if ret else -1);c=round(random.uniform(5,12),2)
            created=random.choice(["now()-interval '3 hour'","now()-interval '30 minute'"])
            q.append(f"insert into erp.material_stock_movements(id,source_id,source_type,qty_signed,unit_cost_snapshot,physical_at,system_created_at) values('{m}','{g}','{'CUTTING_GROUP_RETURN' if ret else 'CUTTING_GROUP'}',{qty},{c},{ts(d,8)},{created});")
            if random.random()<0.85 and 'hour' in created:
                q.append(f"insert into erp.po_hpp_gl_material_state_v1 values('{PO}','M:{m}',{round(-qty*random.uniform(5,12),2)},now()-interval '1 hour');")
    q.append("insert into erp.materials values('00000000-0000-0000-0000-0000000000ae','FABRIC');")
    for k in range(random.randint(0,2)):
        iss=u();it=u();d=random.randint(1,8)
        q.append(f"insert into erp.contractor_material_issues values('{iss}','{PO}','POSTED',{ts(d)});")
        q.append(f"insert into erp.contractor_material_issue_items values('{it}','{iss}','00000000-0000-0000-0000-0000000000ae',5,{round(random.uniform(1,3),2)});")
        q.append(f"insert into erp.material_stock_movements(source_id,source_type,qty_signed,unit_cost_snapshot,physical_at,system_created_at) values('{it}','CONTRACTOR_MATERIAL_ISSUE_ITEM',-5,1,{ts(d)},now()-interval '3 hour');")
        if random.random()<0.8: q.append(f"insert into erp.po_hpp_gl_material_state_v1 values('{PO}','C:{it}',{round(random.uniform(5,15),2)},now()-interval '1 hour');")
    lots=[]
    for li in range(random.randint(1,4)):
        l=u();g=random.choice(groups+[None]);g=g if (g and g[1]==PO) or g is None else None
        qc=random.randint(1,8);n=random.randint(1,10);origin='VOIDED_PRODUCTION' if random.random()<0.15 else 'PRODUCTION'
        lots.append((l,n,qc,origin))
        q.append(f"insert into erp.fg_lots values('{l}','{PO}','{origin}',{n},{ts(qc,13)},{repr(g[0]) if g else 'null'},null,null);")
        q.append(f"insert into erp.fg_stock_movements(id,lot_id,movement_type,qty_signed,physical_at) values('{u()}','{l}','QC_GOOD',{n},{ts(qc,13)});")
        if origin=='VOIDED_PRODUCTION':
            q.append(f"insert into erp.fg_stock_movements(lot_id,movement_type,qty_signed,physical_at,reversal_of_id) select lot_id,'REVERSAL',-qty_signed,{ts(max(0,qc-1),14)},id from erp.fg_stock_movements where lot_id='{l}' and movement_type='QC_GOOD';")
    # relabel chain
    live=[x for x in lots if x[3]=='PRODUCTION']
    conv=[]
    if live and random.random()<0.5:
        src=random.choice(live);depth=random.randint(1,3);cur=src[0];d=src[2];n=max(1,src[1]//2)
        for k in range(depth):
            d=max(0,d-1);dst=u();c=u();st=random.choice(['POSTED','POSTED','REVERSED'])
            q.append(f"insert into erp.fg_lots values('{dst}','{PO}','CONVERSION',{n},{ts(d,15)},null,null,null);")
            q.append(f"insert into erp.product_conversions values('{c}','{st}');")
            q.append(f"insert into erp.product_conversion_allocations(conversion_id,source_lot_id,destination_lot_id) values('{c}','{cur}','{dst}');")
            o=u();i=u()
            q.append(f"insert into erp.fg_stock_movements(id,lot_id,movement_type,qty_signed,physical_at) values('{o}','{cur}','REBRAND_OUT',-{n},{ts(d,15)}),('{i}','{dst}','REBRAND_IN',{n},{ts(d,15)});")
            if st=='REVERSED':
                q.append(f"insert into erp.fg_stock_movements(lot_id,movement_type,qty_signed,physical_at,reversal_of_id) values('{dst}','REVERSAL',-{n},now(),'{i}'),('{cur}','REVERSAL',{n},now(),'{o}');")
                break
            conv.append(dst);cur=dst
    allfg=[(x[0],x[1]) for x in live]+[(c,1) for c in conv]
    sid=u();q.append(f"insert into erp.sales_headers values('{sid}','POSTED',null);");si=u();q.append(f"insert into erp.sales_items values('{si}','{sid}');")
    for (l,n) in allfg:
        if random.random()<0.5:
            k=random.randint(1,max(1,n//2));d=random.randint(0,3);mid=u()
            q.append(f"insert into erp.fg_stock_movements(id,lot_id,movement_type,qty_signed,physical_at) values('{mid}','{l}','SALE',-{k},{ts(d,17)});")
            if random.random()<0.3:
                q.append(f"insert into erp.fg_stock_movements(lot_id,movement_type,qty_signed,physical_at,reversal_of_id) values('{l}','REVERSAL',{k},{ts(max(0,d-1),18)},'{mid}');")
            else: q.append(f"insert into erp.sale_stock_allocations(sale_item_id,lot_id,qty_pcs) values('{si}','{l}',{k});")
        if random.random()<0.3:
            q.append(f"insert into erp.fg_stock_movements(lot_id,movement_type,qty_signed,physical_at) values('{l}','{random.choice(['BS_OUT','ADJUSTMENT'])}',-1,{ts(random.randint(0,3),19)});")
    # hpp versions and states
    for (l,n,qc,origin) in lots:
        old=round(random.uniform(8,12),4);new=round(old+random.uniform(-2,2),4)
        q.append(f"insert into erp.hpp_versions(lot_id,version_no,qty_basis_pcs,total_cost,is_current,calculated_at) values('{l}',1,{n},{n*old},false,now()-interval '2 hour'),('{l}',2,{n},{n*new},true,now());")
        q.append(f"insert into erp.po_hpp_gl_lot_state_v1 values('{l}','{PO}',{old},now()-interval '1 hour');")
    for c in conv:
        q.append(f"insert into erp.hpp_versions(lot_id,version_no,qty_basis_pcs,total_cost,is_current,calculated_at) select '{c}',1,initial_qty_pcs,initial_qty_pcs*9.5,false,now()-interval '90 minute' from erp.fg_lots where id='{c}';")
        q.append(f"insert into erp.hpp_versions(lot_id,version_no,qty_basis_pcs,total_cost,is_current,calculated_at) select '{c}',2,initial_qty_pcs,initial_qty_pcs*{round(random.uniform(8,11),3)},true,now() from erp.fg_lots where id='{c}';")
    # old state: compute a consistent old state from old hpp via targets with old versions
    q.append("update erp.hpp_versions set is_current=not is_current;")
    q.append(f"insert into erp.po_hpp_gl_state select '{PO}',base_output_qty,hpp_total_cost,fg_value,cogs_value,other_out_value,now()-interval '1 hour' from erp.compute_po_hpp_gl_targets_v2620d('{PO}');")
    q.append("update erp.hpp_versions set is_current=not is_current;")
    return q
def run(seed,mode):
    q=scen(seed,mode)
    body='\n'.join(q)
    J="(select coalesce(jsonb_agg(x order by x::text),'[]') from (select j.transaction_date,l.mapping_key,l.debit,l.credit from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id) x)"
    T="(select coalesce(jsonb_object_agg(k,a),'{}') from (select case when mapping_key like 'OTHER%' then 'OTHER' else mapping_key end k,sum(debit-credit) a from erp.journal_lines group by 1) x)"
    sql=f"""\\set ON_ERROR_STOP 1
\\set QUIET 1
begin;
{body}
savepoint s;
select erp.sync_po_hpp_to_gl_as('{PO}',current_date-5);
select {J} asj,{T} ast \\gset
rollback to savepoint s;
select erp.sync_po_hpp_to_gl('{PO}',current_date-5);
\\t on
select json_build_object('same_j',{J}=:'asj'::jsonb,'same_t',{T}=:'ast'::jsonb,'as',:'ast'::jsonb,'ay',{T},'n',(select count(*) from erp.journal_entries));
rollback;
"""
    open(S+f'{mode}_{seed}.sql','w').write(sql)
    r=subprocess.run(['psql','-h','127.0.0.1','-U','postgres','-d','rev7r_main','-X','-f',S+f'{mode}_{seed}.sql'],capture_output=True,text=True)
    if r.returncode!=0: return ('ERR',r.stderr[-400:])
    out=[l for l in r.stdout.split('\n') if l.strip().startswith('{')]
    return ('OK',json.loads(out[-1]))
if __name__=='__main__':
    n=int(sys.argv[1]);bad=0
    for seed in range(int(sys.argv[2]) if len(sys.argv)>2 else 0,n):
        for mode in ['open','closed','noninv']:
            st,res=run(seed,mode)
            if st=='ERR': bad+=1;print(seed,mode,'ERR',res);continue
            ok=res['same_t'] if mode=='open' else res['same_j']
            # totals: compare numerically per key
            if mode=='open':
                a={k:float(v) for k,v in res['as'].items()};b={k:float(v) for k,v in res['ay'].items()}
                ok=all(abs(a.get(k,0)-b.get(k,0))<0.005 for k in set(a)|set(b))
            if not ok: bad+=1;print(seed,mode,'MISMATCH',res)
    print('done',n,'bad',bad)
