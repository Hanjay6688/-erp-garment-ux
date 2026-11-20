"""Install the candidate in the actual owning transaction before the Global seal."""
import json
import os
from pathlib import Path
import re
from .migration import apply, read_sources
from .source import PRODUCT, TREE, check, sha

def evidence():
    return Path(os.environ['GITHUB_WORKSPACE'])/'close11-evidence'

def write(name,data):
    path=evidence()/name
    with path.open('x',encoding='utf-8') as stream:
        json.dump(data,stream,indent=2,sort_keys=True,default=str);stream.write('\n')

def diagnostic(step,e):
    def scrub(ex):
        msg=str(ex).splitlines()[0]
        # Only emit technical metadata or bounded generated-object names. Never SQL parameters or rows.
        return (re.sub(r'[^A-Za-z0-9_ .:(),-]',' ',msg)[:200]
                if msg.startswith(('CANDIDATE_','UNHANDLED_','BODY_READBACK','SQL_FUNCTION','INSTALLED_','SEVEN_','ALERT_','SOURCE_','CLOSE11_','WORKTREE_'))
                else None)
    path=evidence()/'first-failure.json'
    if path.exists():return
    chain=[]
    while e and len(chain)<5:
        diag=getattr(e,'diag',None)
        line={'type':type(e).__name__,'sqlstate':getattr(e,'sqlstate',None),'where':scrub(e)}
        if diag:
            for key in ('schema_name','table_name','column_name','datatype_name','constraint_name'):
                value=getattr(diag,key,None)
                if value and re.fullmatch(r'[a-zA-Z0-9_.]{1,100}',value):line[key]=value
            msg=getattr(diag,'message_primary','') or ''
            if re.fullmatch(r'(?:permission denied for|must be owner of|relation|function|schema|column|role|constraint|type|table|view) [a-zA-Z0-9_ .,"()]+',msg):
                line['message']=msg[:200]
        chain.append(line);e=e.__cause__ or e.__context__
    write('first-failure.json',dict(phase=step,causes=chain,production_go=False))

def pin(data):
    return sha(json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':'),default=str).encode())

def bind(provider,work):
    repair=provider._repair_readers_preseal
    predecessor=provider._repair_predecessor_image
    passes=0; old_cat=new_cat=report=None
    src=read_sources(work/'s06-product',work/'close11-product')

    def install(cur):
        nonlocal passes,old_cat,new_cat,report
        result=repair(cur);passes+=1
        check(passes in (1,2),'CLOSE11_INSTALL_COUNT')
        if passes==1:return result
        try:
            old_cat=provider.capture(cur)
            with provider.as_role(cur,'supabase_admin'),provider.metadata_context(cur):
                report=apply(cur,src)
                # Use the retained installer's exact candidate-independent postimages for S06.
                from importlib.util import spec_from_file_location,module_from_spec
                path=work/'s06-product/scripts/cp7_s06_reminder_forward.py'
                spec=spec_from_file_location('close11_qualified_s06',path);s06=module_from_spec(spec);spec.loader.exec_module(s06)
                bodies=s06.expected_bodies(); actual=s06.catalogue(cur,bodies)
                check(all(actual[k][0]==v[1] for k,v in bodies.items()),'CLOSE11_S06_INSTALLED_POSTIMAGES')
                report['s06_postimages']={k:sha(actual[k][0].encode()) for k in bodies}
            new_cat=provider.capture(cur)
            check(old_cat.keys()==new_cat.keys() and len(new_cat)==25,'CLOSE11_FULL25')
            ops={}; fnames={name.split('(')[0] for name in report['functions']}
            # Every changed function is an updated source object or an existing object
            # with a candidate-declared EXECUTE grant. Global readers/guards stay identical.
            changes=[(k,dict(old_cat['functions']).get(k),v) for k,v in new_cat['functions'] if dict(old_cat['functions']).get(k)!=v]
            for name,old,row in changes:
                if old is None or old[0]!=row[0]:
                    check(name.split('(')[0] in fnames,'CANDIDATE_UNDECLARED_FUNCTION '+name)
            for group in new_cat:
                a=dict(old_cat[group]);b=dict(new_cat[group])
                removed=set(a)-b.keys();added=set(b)-a.keys();updated={k for k in a.keys()&b.keys() if a[k]!=b[k]}
                if added or removed or updated:ops[group]={'added':len(added),'removed':len(removed),'updated':len(updated)}
            check(not any(k in ops for k in ('roles','memberships','languages','extensions','casts','operators','event_triggers','default_privileges')),'CLOSE11_GLOBAL_AUTHORITY_DRIFT')
            report.update(product=PRODUCT,tree=TREE,full25_predecessor_sha256=pin(old_cat),full25_installed_sha256=pin(new_cat),changes=ops)
            write('preseal.json',report)
        except Exception as exc:
            diagnostic('candidate before Global seal',exc);raise
        return result

    def project(before,after):
        if passes==2:
            check(after==new_cat,'CLOSE11_PRESEAL_CATALOGUE_DRIFT')
            after=old_cat
        return predecessor(before,after)

    provider._repair_readers_preseal=install
    provider._repair_predecessor_image=project

    def committed(conn,cur,state,lifecycle):
        try:
            check(passes==2 and report is not None and conn.info.dbname=='cp6_rollback','CLOSE11_COMMITTED_ROUTE')
            lifecycle.verify(cur,state)
            actual=provider.capture(cur)
            check(actual==new_cat and len(actual)==25,'CLOSE11_COMMITTED_FULL25')
            public_functions=[k for k,_ in actual['functions'] if k.startswith('public.erp_')]
            raw=state.global_installation['sealed']['actual_parent_root_receipt']['catalogue_fingerprint']
            check(raw and len(public_functions)>=362,'CLOSE11_GLOBAL_PROFILE')
            result={'status':'COMMITTED','database':conn.info.dbname,'product':PRODUCT,'tree':TREE,'runner':os.environ['GITHUB_SHA'],'run':os.environ['GITHUB_RUN_ID'],'public_functions':len(public_functions),'full25_sha256':pin(actual),'catalogue_groups':{k:len(v) for k,v in actual.items()},'sealed_fingerprint':raw,'actual_auditor_cases':0,'production_go':False}
            conn.commit()
            from .checkpoint import capture
            capture(result)
            write('installed.json',result)
            return result
        except Exception as exc:
            diagnostic('read committed catalogue and preserve auditor environment',exc);raise
    return committed
