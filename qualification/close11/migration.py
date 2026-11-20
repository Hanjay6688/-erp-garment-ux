"""Compile the SQL delta of the two verified trees, preserving installed Global wrappers."""
import difflib
import re
from collections import Counter
from pathlib import Path
from .source import BASE, TREE, check, git, sha

WHOLE = ('scripts/cp7-src/stock-formula/scoped-rules.sql','scripts/cp7-src/payroll/component-entitlement.sql')
LEX = re.compile(r"""--[^\n]*|/\*.*?\*/|(?P<d>\$(?:[A-Za-z_]\w*)?\$).*?(?P=d)|'(?:''|[^'])*'|"(?:""|[^"])*"|;""",re.S)
CREATE = re.compile(r'^create\s+(?:or\s+replace\s+)?function\s+([\w.]+)\s*\(([^()]*)\)',re.I)
DOLLAR = re.compile(r'\bas\s*(\$(?:\w*)\$)',re.I)
RIGHTS = re.compile(r'^(grant\s+(?:select|execute|(?:usage|create) on schema)|revoke\s+(?:all\s+on\s+function|create on schema)|alter\s+function\s+)',re.I)
TYPES = {'timestamptz':'timestamp with time zone','int':'integer','bool':'boolean','decimal':'numeric'}
AGGREGATE='scripts/cp7_bounded_analysis_stage/stage.sql'

def statements(source):
    start=0
    for m in LEX.finditer(source):
        if m[0]==';':
            stmt=source[start:m.end()].strip()
            while stmt.startswith(('--','/*')):
                if stmt.startswith('--'):stmt=stmt.partition('\n')[2].lstrip()
                else:stmt=stmt.partition('*/')[2].lstrip()
            if stmt:yield stmt
            start=m.end()
    tail=source[start:].strip()
    check(not tail or all(not s.strip() or s.lstrip().startswith('--') for s in tail.splitlines()),'UNPARSED_SQL_TAIL')

def declaration(stmt,path):
    m=CREATE.match(stmt)
    if not m:return None
    name=m[1]
    args=[]
    for arg in m[2].split(','):
        if not arg.strip():continue
        pieces=re.split(r'\s+',re.split(r'\s+default\s+|\s*=',arg.strip(),flags=re.I)[0])
        typ=' '.join(pieces[1:]) if len(pieces)>1 and pieces[0].lower() not in ('timestamp','double','character') else ' '.join(pieces)
        args.append(TYPES.get(typ.lower(),typ.lower()))
    if path.endswith('/planning/analysis.sql') and name=='cp7_analysis_native.build':
        name += '_operational'
        stmt=stmt[:m.start(1)]+name+stmt[m.end(1):]
    marker=DOLLAR.search(stmt)
    check(marker is not None,'SQL_FUNCTION_BODY_'+name)
    end=stmt.index(marker[1],marker.end())
    return dict(sig=name+'('+','.join(args)+')',name=name,statement=stmt,
                header=stmt[:marker.start()],body=stmt[marker.end():end],path=path)

def compile_plan(sources):
    functions={};rights=[];standalone=[];structures=[];alerts=[]
    # The bounded stage owns the final wrapper over its two rendering inputs.
    for path,(old,new) in sorted(sources.items(),key=lambda item:(item[0]==AGGREGATE,item[0])):
        if path in WHOLE:
            standalone.append((path,new))
            continue
        a=list(statements(old));b=list(statements(new));prior=set(a)
        oldf={d['sig']:d for s in a if (d:=declaration(s,path))}
        for s in b:
            if s in prior:continue
            d=declaration(s,path)
            if d:
                functions[d['sig']]=(oldf.get(d['sig']),d)
                if path.endswith('/alerts/alerts.sql'):alerts.append(d['sig'])
            elif RIGHTS.match(s):
                rights.append((path,s))
            elif s.lower().startswith('create table '):
                structures.append((path,s))
            elif s.lower().startswith('do '):
                # Reviewed role assignment loops apply to newly declared functions, too.
                rights.append((path,s))
            else:raise ValueError('UNHANDLED_CANDIDATE_DDL '+path+' '+s[:100])
    return functions,rights,standalone,structures,alerts

def read_sources(base,new):
    paths=git(base,'diff','--name-only',BASE,TREE,'--','scripts').decode().splitlines()
    result={}
    for p in paths:
        if not p.endswith('.sql'):continue
        raw=(new/p).read_bytes()
        check(raw==git(base,'show',TREE+':'+p),'WORKTREE_SQL '+p)
        before=b'' if p in WHOLE else git(base,'show',BASE+':'+p)
        result[p]=(before.decode(),raw.decode())
    return result

def merge_body(old,new,live,label):
    if live in (old,new):return new
    # An inherited wrapper may already contain some changes. An edit can be
    # applied only at one unambiguous old span, or recognized by its new span.
    a=old.splitlines(True);b=new.splitlines(True)
    for group in difflib.SequenceMatcher(None,a,b,autojunk=False).get_grouped_opcodes(1):
        pre=''.join(a[group[0][1]:group[-1][2]])
        post=''.join(b[group[0][3]:group[-1][4]])
        if pre and live.count(pre)==1:live=live.replace(pre,post,1)
        elif post and live.count(post)==1:continue
        else:
            changes=[b[j:k] for op,_,_,j,k in group if op!='equal']
            check(all(v and live.count(''.join(v))==1 for v in changes),'CANDIDATE_WRAPPER_CONTEXT '+label)
    return live

def ddl(cur,stmt,phase):
    try:cur.execute(stmt,prepare=False)
    except Exception as exc:raise ValueError(f'{phase} SQLSTATE={getattr(exc,"sqlstate","NONE")} '+str(exc).splitlines()[0][:200]) from exc

def apply(cur,sources):
    funcs,rights,whole,structs,alert_names=compile_plan(sources)
    check(len(alert_names)==7,'SEVEN_CHANGED_ALERTS')
    for _,s in structs:
        if s.lower().startswith('create table cp7_schedule_native.plans('):
            ddl(cur,'alter table cp7_schedule_native.plans add column shared_work_hash text','schedule column')
        elif match:=re.match(r'create table cp7_alert_native\.(alerts|outbox|source_state)\(',s,re.I):
            table=match[1]
            column='alert_kind' if table=='outbox' else 'kind'
            kind=re.search(r'check\(('+column+r" in\((?:'[^']+'|[\s,])+\))\)",s,re.I)
            check(kind is not None,'ALERT_KIND_DEFINITION '+table)
            name=table+'_'+column+'_check'
            target='cp7_alert_native.'+table
            row=cur.execute('select pg_get_constraintdef(oid) from pg_constraint where conrelid=to_regclass(%s) and conname=%s',(target,name)).fetchone()
            values=lambda text:set(re.findall("'([^']+)'",text))
            check(row and values(row[0])|{'RECOST_PENDING'}==values(kind[1]),'ALERT_KIND_PREIMAGE '+table)
            ddl(cur,'alter table '+target+' drop constraint '+name+', add constraint '+name+' check ('+kind[1]+')',table+' kind')
        else:raise ValueError('UNHANDLED_TABLE '+s[:80])
    # String-bodied SQL functions may reference other candidate functions. These
    # are mutually dependent modules. The checks below reparse each complete
    # definition with validation enabled after all declarations and ACLs exist.
    cur.execute('set local check_function_bodies=off')
    for path,s in whole:ddl(cur,s,path)
    expected={}
    for sig,(old,new) in funcs.items():
        row=cur.execute('select pg_get_functiondef(p.oid),p.prosrc,pg_get_userbyid(p.proowner),p.proacl::text from pg_proc p where oid=to_regprocedure(%s)',(sig,)).fetchone()
        check(bool(row)==bool(old) or (row and row[1]==new['body']),'CANDIDATE_FUNCTION_PREDECESSOR '+sig)
        if old and row:
            merged=merge_body(old['body'],new['body'],row[1],sig)
            # Preserve decorated SQL surrounding the body, including owner-specific search paths.
            if old['header']==new['header']:
                stmt=row[0].replace(row[1],merged,1)
                check(row[0].count(row[1])==1,'INSTALLED_BODY '+sig)
            else:
                stmt=re.sub(r'^create (?:or replace )?function','create or replace function',new['statement'],count=1,flags=re.I)
                stmt=stmt.replace(new['body'],merged,1)
        else:
            merged=new['body'];stmt=re.sub(r'^create (?:or replace )?function','create or replace function',new['statement'],count=1,flags=re.I)
        ddl(cur,stmt,'function '+sig)
        expected[sig]=merged
    for path,s in rights:
        if s.lower().startswith('do ') and 'owner' not in s.lower():
            raise ValueError('UNREVIEWED_BLOCK '+path)
        ddl(cur,s,path+' authority')
    # schedule.sql revokes public API access from every internal function after creation.
    for sig in ('cp7_schedule_native.shared_work(jsonb,jsonb)','cp7_schedule_native.for_reader(jsonb,jsonb,text)'):
        ddl(cur,'revoke all on function '+sig+' from public,anon,authenticated,service_role','schedule helper ACL')
    cur.execute('set local check_function_bodies=on')
    for path,s in whole:
        for st in statements(s):
            d=declaration(st,path)
            if d:expected[d['sig']]=d['body']
    installed={}
    for sig,body in expected.items():
        row=cur.execute('select p.prosrc,pg_get_functiondef(p.oid),pg_get_userbyid(p.proowner) from pg_proc p where p.oid=to_regprocedure(%s)',(sig,)).fetchone()
        check(row and row[0]==body,'BODY_READBACK '+sig)
        # Replacing an identical definition under the owning installer also runs the language validator.
        ddl(cur,row[1],'validate '+sig)
        installed[sig]={'body_sha256':sha(row[0].encode()),'owner':row[2]}
    return {'functions':installed,'alert_definitions':alert_names,'structural_files':[p for p,_ in structs]+[p for p,_ in whole],'rights_statements':len(rights)}
