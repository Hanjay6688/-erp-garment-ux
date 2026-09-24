"""AUDITOR SCENARIO xaudit_4 — REAL HTTP path (PostgREST + JWT) to the candidate's CP6 facades on 9add57e.
Method: start a PostgREST container (same image/env as the disposable stack's supabase_rest_*) pointed at the clone
database cp6_rollback (as the writer's T3 browser job does), mint HS256 JWTs with the stack's PGRST_JWT_SECRET, and call the
facades over HTTP as: anon (role anon), an unmapped authenticated user (random sub), and the seeded operator (OWNER).
Only refusals and read-only calls are made over HTTP (no committed writes). Oracles: M:1322/M:1729 (anon, unmapped,
inactive, view-only fail closed on the real Auth/JWT path), M:281 (viewer read), M:317/M:422/M:4321 (real HTTP/JWT path).
GoTrue login itself is not exercised (JWT minted with the stack secret) — recorded as a limit."""
import base64,hashlib,hmac,json,os,subprocess,time,traceback,urllib.request,urllib.error,uuid
import psycopg
import cp6_aw_probe as awp
api=awp.api
REST='cp6-audit-rest';PORT='54331'
FACADES=[('preflight','erp_accounting_close_preflight_v1'),('close','erp_close_accounting_through_v1'),('laundry_estimate','erp_set_laundry_rate_owner_estimate_v1'),
         ('fg_preview','erp_preview_fg_unsourced_value_v1'),('fg_post','erp_post_fg_unsourced_receipt_v1'),('fg_reverse','erp_reverse_fg_unsourced_receipt_v1'),
         ('accessory_workspace','erp_get_accessory_issue_workspace_v1'),('accessory_save','erp_save_accessory_issue_action_v1'),
         ('pocket_workspace','erp_get_pocket_fabric_workspace_v1'),('import_workspace','erp_get_initial_import_workspace_v1')]
OPERATOR='c8c00000-0000-4000-8000-000000000101'

def sh(*a):return subprocess.run(list(a),check=True,capture_output=True,text=True).stdout
def b64(b):return base64.urlsafe_b64encode(b).rstrip(b'=').decode()
def jwt(secret,claims):
    h=b64(json.dumps({'alg':'HS256','typ':'JWT'}).encode());p=b64(json.dumps(claims).encode())
    sig=b64(hmac.new(secret.encode(),(h+'.'+p).encode(),hashlib.sha256).digest());return h+'.'+p+'.'+sig

def start_rest():
    names=sh('docker','ps','--format','{{.Names}}').split()
    original=next(n for n in names if n.startswith('supabase_rest_'))
    ins=json.loads(sh('docker','inspect',original))[0]
    cfg=dict(x.split('=',1) for x in ins['Config']['Env'] if '=' in x)
    uri=cfg['PGRST_DB_URI'];base,_,tail=uri.rpartition('/');db,q,query=tail.partition('?')
    cfg['PGRST_DB_URI']=base+'/cp6_rollback'+(q+query if q else '')
    cfg.update(PGRST_DB_SCHEMAS='public',PGRST_SERVER_PORT='3000')
    network=next(iter(ins['NetworkSettings']['Networks']))
    env='/tmp/cp6-audit-rest.env';open(env,'w').write(''.join(f'{k}={v}\n' for k,v in sorted(cfg.items())))
    subprocess.run(['docker','rm','-f',REST],capture_output=True)
    sh('docker','run','-d','--name',REST,'--network',network,'--env-file',env,'-p','127.0.0.1:%s:3000'%PORT,ins['Config']['Image'])
    for _ in range(60):
        try:urllib.request.urlopen('http://127.0.0.1:%s/'%PORT,timeout=2);break
        except Exception:time.sleep(1)
    return cfg['PGRST_JWT_SECRET'],cfg.get('PGRST_DB_ANON_ROLE','anon')

def call(token,fn,body):
    req=urllib.request.Request('http://127.0.0.1:%s/rpc/%s'%(PORT,fn),data=json.dumps(body).encode(),method='POST',
        headers={'Content-Type':'application/json','apikey':token,'Authorization':'Bearer '+token,'Accept':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=30) as r:return dict(http=r.status,body=r.read().decode()[:220])
    except urllib.error.HTTPError as e:
        return dict(http=e.code,body=e.read().decode()[:300])
    except Exception as e:return dict(http=None,body=str(e)[:200])

def params(cur,fn):
    api.admin(cur)
    row=cur.execute("select pg_get_function_arguments(p.oid) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.proname=%s limit 1",(fn,)).fetchone()
    return row[0] if row else None

def body_for(args):
    """Build a JSON body from a pg_get_function_arguments string; unknown names get a type-appropriate dummy."""
    out={}
    for part in (args or '').split(','):
        part=part.strip()
        if not part:continue
        name,_,rest=part.partition(' ');typ=rest.split(' DEFAULT')[0].strip().lower()
        if name.startswith('"'):name=name.strip('"')
        v='2026-09-20' if 'date' in typ and 'timestamp' not in typ else str(uuid.uuid4()) if 'uuid' in typ else {} if 'json' in typ else 1.5 if 'numeric' in typ else '2026-09-20T00:00:00Z' if 'timestamp' in typ else 'auditor http probe' if 'text' in typ else None
        out[name]=v
    return out

def http_matrix(cur,today):
    secret,anon_role=start_rest()
    try:
        exp=int(time.time())+3600
        tokens=dict(anon=jwt(secret,dict(role=anon_role,iss='supabase',exp=exp)),
                    unmapped=jwt(secret,dict(sub=str(uuid.uuid4()),role='authenticated',aud='authenticated',iss='supabase',exp=exp)),
                    operator=jwt(secret,dict(sub=OPERATOR,role='authenticated',aud='authenticated',iss='supabase',exp=exp)))
        sigs={fn:params(cur,fn) for _,fn in FACADES}
        results={}
        for who in ('anon','unmapped','operator'):
            for label,fn in FACADES:
                if who=='operator' and label not in ('preflight','accessory_workspace','pocket_workspace','import_workspace'):continue   # read-only positives only
                results[who+':'+label]=call(tokens[who],fn,body_for(sigs[fn]))
        def refused(r):return r['http'] in (401,403) or (r['http'] and r['http']>=400 and ('OWNER or ADMIN' in r['body'] or 'permission denied' in r['body'] or 'PERMISSION_DENIED' in r['body']))
        anon_ok=all(refused(results['anon:'+l]) for l,_ in FACADES)
        unm_ok=all(refused(results['unmapped:'+l]) for l,_ in FACADES)
        op_ok=all(results['operator:'+l]['http']==200 for l in ('preflight','pocket_workspace','import_workspace'))
        checks=dict(anon_all_refused_over_http=anon_ok,unmapped_all_refused_over_http=unm_ok,operator_reads_200=op_ok,identity_switch_effective=results['operator:preflight']['http']==200 and results['unmapped:preflight']['http']!=200)
        return dict(status='PASS' if all(checks.values()) else 'COUNTEREXAMPLE',checks=checks,signatures=sigs,results=results,
                    expected='M:1322/M:1729 over the REAL HTTP/JWT path (PostgREST): anon and unmapped users are refused on all 10 facades with an authorization error; the seeded OWNER reads succeed (200)')
    finally:
        subprocess.run(['docker','rm','-f',REST],capture_output=True)

def cases(cur,today):
    def wrap(fn):
        def run():
            try:return fn(cur,today)
            except Exception as exc:return dict(status='INCOMPLETE',error=str(exc)[:900],traceback=traceback.format_exc()[-1500:])
        return run
    return [('XA4:HTTP_JWT_FACADE_MATRIX',wrap(http_matrix))]
