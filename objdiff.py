import re,os,sys,json
fwd_dir='supabase/release/cp6-t3'; rb_dir='supabase/release/cp6-t3-rollbacks'
cre=re.compile(r'create\s+(?:or\s+replace\s+)?(?:unlogged\s+)?(function|procedure|table|view|materialized\s+view|trigger|type|index|unique\s+index|sequence|policy|domain|schema)\s+(?:if\s+not\s+exists\s+)?(?:concurrently\s+)?([a-zA-Z0-9_."]+)',re.I)
dro=re.compile(r'drop\s+(function|procedure|table|view|materialized\s+view|trigger|type|index|sequence|policy|domain)\s+(?:if\s+exists\s+)?([a-zA-Z0-9_."]+)',re.I)
alt=re.compile(r'alter\s+table\s+(?:only\s+)?(?:if\s+exists\s+)?([a-zA-Z0-9_."]+)\s+(add|drop)\s+(?:column|constraint)?\s*(?:if\s+(?:not\s+)?exists\s+)?([a-zA-Z0-9_"]+)',re.I)
def strip_comments(t):
    t=re.sub(r'--[^\n]*','',t)
    return t
def objs(path):
    t=strip_comments(open(path,encoding='utf-8',errors='replace').read())
    c={(k.lower().replace('unique ',''),n.strip('"').lower()) for k,n in cre.findall(t)}
    d={(k.lower(),n.strip('"').lower()) for k,n in dro.findall(t)}
    a=[(tb.lower(),op.lower(),col.lower()) for tb,op,col in alt.findall(t)]
    return c,d,a,t
out=[]
for f in sorted(os.listdir(fwd_dir)):
    if not f.endswith('.sql'): continue
    rb=f.replace('.sql','.rollback.sql')
    fc,fd,fa,ft=objs(os.path.join(fwd_dir,f))
    rc,rd,ra,rt=objs(os.path.join(rb_dir,rb))
    fcn={n for k,n in fc if k in('function','procedure')}; fct={n for k,n in fc if k=='table'}; fcv={n for k,n in fc if 'view' in k}; fctr={n for k,n in fc if k=='trigger'}; fci={n for k,n in fc if 'index' in k}
    rdn={n for k,n in rd if k in('function','procedure')}; rdt={n for k,n in rd if k=='table'}; rdv={n for k,n in rd if 'view' in k}; rdtr={n for k,n in rd if k=='trigger'}
    rcn={n for k,n in rc if k in('function','procedure')}
    # forward-created functions not dropped and not re-created in rollback
    notrev=sorted(fcn-rdn-rcn)
    tabs_notdrop=sorted(fct-rdt)
    views_notdrop=sorted(fcv-rdv-{n for k,n in rc if 'view' in k})
    print(f[:40], 'FWD fn',len(fcn),'tbl',len(fct),'view',len(fcv),'trg',len(fctr),'idx',len(fci),'| RB drop fn',len(rdn),'tbl',len(rdt),'view',len(rdv),'trg',len(rdtr),'recreate fn',len(rcn))
    if notrev: print('   fwd fn not reversed by rollback:',notrev[:15], '...' if len(notrev)>15 else '')
    if tabs_notdrop: print('   fwd tables not dropped:',tabs_notdrop[:15])
    if views_notdrop: print('   fwd views not dropped/recreated:',views_notdrop[:10])
    fadd={(tb,col) for tb,op,col in fa if op=='add'}; rdrop={(tb,col) for tb,op,col in ra if op=='drop'}
    if fadd-rdrop: print('   fwd alter add not dropped:',sorted(fadd-rdrop)[:10])
    # schema_migrations marker
    fm=re.findall(r"schema_migrations[^;]{0,300}?'(v?2\.6\.20[a-z]{2}[^']*)'",ft)
    rm=re.findall(r"schema_migrations[^;]{0,300}?'(v?2\.6\.20[a-z]{2}[^']*)'",rt)
    print('   markers fwd',sorted(set(fm))[:4],'rb',sorted(set(rm))[:4])
