import re,os,gzip,json,sys
root='.'
texts=[]
texts.append(('FIXTURE',gzip.open('supabase/tests/fixtures/erp_enteng_cp45a_catalog_bootstrap.sql.gz','rt',encoding='utf-8',errors='replace').read()))
rel=sorted(f for f in os.listdir('supabase/release/cp6-t3') if f.endswith('.sql'))
relstamps={f[:14] for f in rel}
for f in sorted(os.listdir('supabase/migrations')):
    if f.endswith('.sql') and f[:14] not in relstamps:
        texts.append(('migrations/'+f,open('supabase/migrations/'+f,encoding='utf-8',errors='replace').read()))
for f in rel: texts.append(('release/cp6-t3/'+f,open('supabase/release/cp6-t3/'+f,encoding='utf-8',errors='replace').read()))
# order by stamp for migrations+release
def stamp(n):
    m=re.search(r'(\d{14})',n); return m.group(1) if m else '0'
head=texts[0]; rest=sorted(texts[1:],key=lambda t:stamp(t[0]))
texts=[head]+rest
fn={}
pat=re.compile(r'create\s+or\s+replace\s+function\s+((?:erp|public)\.[a-z0-9_]+)\s*\(',re.I)
for name,t in texts:
    for m in pat.finditer(t):
        start=m.start()
        # find body between first $tag$ ... $tag$
        mm=re.compile(r'\$([a-z_]*)\$').search(t,m.end())
        if not mm: continue
        tag=mm.group(0); end=t.find(tag,mm.end())
        if end<0: continue
        body=t[start:end+len(tag)]
        line=t[:start].count('\n')+1
        fn[m.group(1).lower()]=(name,line,body)
print('functions',len(fn),file=sys.stderr)
calls={}
for k,(f,l,b) in fn.items():
    calls[k]={c.lower() for c in re.findall(r'\b((?:erp|public)\.[a-z0-9_]+)\s*\(',b,re.I) if c.lower()!=k}
def refs_lock(b):
    return bool(re.search(r'accounting_period_control|closed_through|resolve_accounting_transaction_date|post_journal\s*\(|CLOSED_PERIOD|period_closed',b,re.I))
direct={k for k,(f,l,b) in fn.items() if re.search(r'accounting_period_control|closed_through',b,re.I)}
print('direct lock readers',len(direct),sorted(direct)[:80],file=sys.stderr)
def reach(k,depth=4):
    seen=set();frontier={k}
    for d in range(depth):
        nxt=set()
        for x in frontier:
            for c in calls.get(x,()):
                if c in seen: continue
                seen.add(c); nxt.add(c)
        frontier=nxt
    return seen
writers=sorted(k for k in fn if re.match(r'^(public\.erp_(save|post|reverse|set|manage|complete|finalize|apply|close|reopen|record|allocate|cancel|approve|pay)|erp\.(post_|reverse_|save_|finalize_|complete_|apply_|manage_|approve_|cancel_|pay_|post_|bb_manage|bc_|bd_post|bd_save|bd_reverse|be_|bf_save|bf_bind|set_))',k))
out=[]
for w in writers:
    r=reach(w)
    via_direct=sorted(r&direct)
    via_journal=('erp.post_journal' in r) or ('erp.post_journal' in calls.get(w,()))
    out.append((w,fn[w][0],fn[w][1],bool(via_direct),via_journal,via_direct[:3]))
json.dump(out,open('/tmp/claude-0/-home-user--erp-garment-ux/2a0eb6c3-bb79-5f14-b9f8-6487e74e773f/scratchpad/fable7/writers_lock.json','w'),indent=0)
print('writers',len(out))
nolock=[o for o in out if not o[3]]
print('writers without direct-lock reach (depth4):',len(nolock))
for o in nolock: print(o[0],'|',o[1],':',o[2],'| journal' if o[4] else '| NO_JOURNAL')
print('---- writers WITH direct lock reach:',len(out)-len(nolock))
for o in out:
    if o[3]: print(o[0],'|',o[1],':',o[2],'| via',o[5])
