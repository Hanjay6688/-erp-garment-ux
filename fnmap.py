import re,os,sys
root='.'
texts=[('FIXTURE',open('/tmp/claude-0/-home-user--erp-garment-ux/2a0eb6c3-bb79-5f14-b9f8-6487e74e773f/scratchpad/fable7/fixture.sql',encoding='utf-8',errors='replace').read())]
rel=sorted(f for f in os.listdir('supabase/release/cp6-t3') if f.endswith('.sql')); relstamps={f[:14] for f in rel}
rest=[]
for f in sorted(os.listdir('supabase/migrations')):
    if f.endswith('.sql') and f[:14] not in relstamps: rest.append(('migrations/'+f,open('supabase/migrations/'+f,encoding='utf-8',errors='replace').read()))
for f in rel: rest.append(('release/cp6-t3/'+f,open('supabase/release/cp6-t3/'+f,encoding='utf-8',errors='replace').read()))
rest.sort(key=lambda t:re.search(r'(\d{14})',t[0]).group(1))
texts+=rest
fn={}
pat=re.compile(r'create\s+or\s+replace\s+function\s+((?:erp|public)\.[a-z0-9_]+)\s*\(',re.I)
for name,t in texts:
    for m in pat.finditer(t):
        mm=re.compile(r'\$([a-z_]*)\$').search(t,m.end())
        if not mm: continue
        tag=mm.group(0); end=t.find(tag,mm.end())
        if end<0: continue
        fn[m.group(1).lower()]=(name,t[:m.start()].count('\n')+1,t[m.start():end+len(tag)])
names=sys.argv[1].split(','); pattern=re.compile(sys.argv[2],re.I)
for n in names:
    if n not in fn: print('##',n,'NOT FOUND'); continue
    f,l,b=fn[n]; print('##',n,'final at',f,':',l,'lines',b.count('\n'))
    for i,line in enumerate(b.split('\n')):
        if pattern.search(line): print('   ',l+i,line.strip()[:200])
