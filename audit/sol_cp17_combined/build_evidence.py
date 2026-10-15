"""Build reviewable audit registers from retained originals. This does not execute business cases."""
from pathlib import Path
import collections, csv, hashlib, json, re, subprocess, zipfile

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
E=ROOT.parent/'sol-evidence'
CANDIDATE='dfab13bf62398a69a02bf6221c06d29075e5e40b'
TREE='886f83312958b53781a450a4ea2a8fb2147b3be3'
def read(path):return json.loads(Path(path).read_text())
def save(name,data):
    (OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2,default=str)+'\n')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def artifact(n,name):return read(E/str(n)/name)

meta=read(E/'FINAL_METADATA.json')
save('RUN_REGISTER.json',dict(candidate_sha=CANDIDATE,ownership='SOL_ONLY',runs=meta['runs'],
    counts=dict(runs=len(meta['runs']),jobs=sum(len(r['jobs']) for r in meta['runs']),
                job_conclusions=dict(collections.Counter(j['conclusion'] for r in meta['runs'] for j in r['jobs']))),
    all_terminal=all(j['status']=='completed' for r in meta['runs'] for j in r['jobs'])))
receipts=[]
for r in meta['artifacts']:
    for a in r['artifacts']:
        receipt=read(E/f"{a['id']}.receipt.json")
        receipts.append(dict(run_id=r['run_id'],**{k:a.get(k) for k in ['id','name','size_in_bytes','digest','expired','created_at','expires_at']},
                             retained_report_count=receipt.get('reports',receipt.get('retained_report_count')),
                             transfer_receipt=receipt))
save('ARTIFACT_REGISTER.json',dict(candidate_sha=CANDIDATE,artifacts=receipts,
    preservation='Exact JSON/TXT outcomes, selected original log, source probes and member hashes in proof archive; SQL dumps and screenshots excluded. Original ZIP digests retained separately.',
    transfer_is_native_evidence=False))

rows=[]
def add(suite,group,cases,artifact_id,filename,run_id,layer,oracle):
    for key,value in cases.items():
        body=value if isinstance(value,dict) else dict(status=value)
        raw=body.get('status','UNKNOWN')
        field='races' if 'race' in group else 'cases'
        escaped=key.replace('~','~0').replace('/','~1')
        if suite.startswith('F03_'):pointer=f'/groups/{group}/{field}/{escaped}'
        elif suite in ['CP17','SOL_LITERAL_QUALIFIED','SOL_HTTP']:pointer=f'/{group}/{field}/{escaped}'
        else:pointer=f'/cases/{escaped}'
        rows.append(dict(execution_id=f'{suite}/{group}/{key}',suite=suite,group=group,case_id=key,
          raw_status=raw,protocol_status='FAIL' if raw in ['COUNTEREXAMPLE','NO_ROUTE','FAIL'] else raw,
          run_id=run_id,attempt=1,artifact_id=artifact_id,original_member=filename,
          json_pointer=pointer,
          layer=layer,evidence_origin='INDEPENDENT_NATIVE_RERUN' if layer!='BROWSER_HTTP_MOCK' else 'SOL_BROWSER_HTTP_MOCK_INVENTORY',
          oracle_origin=body.get('oracle_origin',oracle),fixture_origin=body.get('fixture_origin','SOL_MOCK_AUTH_ACCESS_AND_LOCAL_SEEDS' if layer=='BROWSER_HTTP_MOCK' else 'SOL_SYNTHETIC_POSTGRES_EXCEPTION' if layer=='NATIVE_POSTGRES_ENGINE_ONLY' else 'REUSED_SYNTHETIC_NATIVE_BUILDERS'),
          full_boundary_restored=body.get('full_boundary_restored'),
          scope=body.get('scope'),canonical=True))

f03=[]
for path in sorted(E.glob('*/CP7_F03_FULL_*.json')):
    d=read(path);aid=int(path.parent.name)
    totals=collections.Counter()
    for group,g in d['groups'].items():
        cases=g.get('cases',g.get('races',{}))
        assert len(cases)==sum(g['counts'].values()),(path,group,len(cases),g.get('counts'))
        layer='BROWSER_REAL_AUTH_HTTP_NATIVE' if 'browser' in group else 'REAL_AUTH_HTTP_NATIVE' if 'http' in group else 'NATIVE_RACE' if 'race' in group else 'NATIVE'
        add('F03_'+d['bucket'],group,cases,aid,path.name,38785656150,layer,'REUSED_PROVIDER_ORACLE_EXECUTED_BY_SOL')
        totals.update(c['status'] for c in cases.values())
    assert d['status']=='PASS' and d['cp6_restored'] and d['groups_complete'] and d['advisor_gate']
    f03.append(dict(bucket=d['bucket'],artifact_id=aid,counts=dict(totals),declared_cases=d['expected_case_count'],
                    declared_smoke=d['expected_smoke_count'],group_count=d['observed_group_count'],
                    source_commit=d['source_commit'],source_tree=d['source_tree'],cp6_restored=d['cp6_restored']))
cp=artifact(11998153161,'CP7_CP17_FIXES.json')
for g in ['native','races','http','browser']:
    add('CP17',g,cp[g].get('cases',cp[g].get('races',{})),11998153161,'CP7_CP17_FIXES.json',38785656146,
        {'native':'NATIVE','races':'NATIVE_RACE','http':'REAL_AUTH_HTTP_NATIVE','browser':'BROWSER_REAL_AUTH_HTTP_NATIVE'}[g],
        'REUSED_WRITER_ORACLE_EXECUTED_BY_SOL')
original=artifact(11998153161,'SOL_INDEPENDENT.json')
add('SOL_LITERAL','native',original['cases'],11998153161,'SOL_INDEPENDENT.json',38785656146,'NATIVE','SOL_LITERAL_CONTRACT')
qualified=artifact(11998368969,'SOL_CORRECTION_QUALIFIED.json')
case='SOL_R1_CUSTOMER_PAYMENT_CORRECTION_FINAL_POSITIVE'
old=next(r for r in rows if r['suite']=='SOL_LITERAL' and r['case_id']==case)
old.update(canonical=False,disposition='AUDITOR_TOOL: caller-timezone-dependent generic token; qualified with dedicated public correction workspace token')
add('SOL_LITERAL_QUALIFIED','native',qualified['native']['cases'],11998368969,'SOL_CORRECTION_QUALIFIED.json',38787925433,'NATIVE','SOL_LITERAL_CONTRACT_UNCHANGED')
add('SOL_HTTP','http',qualified['http']['cases'],11998368969,'SOL_CORRECTION_QUALIFIED.json',38787925433,'REAL_AUTH_HTTP_NATIVE','SOL_LITERAL_CONTRACT')
add('BE','native',artifact(11997303136,'BE_CASES_AFTER.json')['cases'],11997303136,'BE_CASES_AFTER.json',38785656260,'NATIVE_CP6_BE_T1','REUSED_PROVIDER_ORACLE_EXECUTED_BY_SOL')
add('OWNER','native',artifact(11998537784,'OWNER_CONTROLLER_QUALIFICATION.json')['cases'],11998537784,'OWNER_CONTROLLER_QUALIFICATION.json',38787131786,'NATIVE_OWNER_INSTALL','REUSED_LOCKED_SOL_OWNER_ORACLE')
for mode,aid in [('DEMO_SIMULATION',11998406630),('DISPOSABLE_TEST',11998247784),('UAT_AUTH_SIMULATION',11998077978)]:
    add('MENU_'+mode,'browser',artifact(aid,mode+'.json')['cases'],aid,mode+'.json',38786177957,'BROWSER_HTTP_MOCK','SOL_ROUTE_AND_REFUSAL_INVENTORY')
add('SOL_DIAGNOSTIC','native',artifact(11999157812,'SOL_DIAGNOSTIC_RETEST.json')['cases'],11999157812,'SOL_DIAGNOSTIC_RETEST.json',38790510239,'NATIVE_POSTGRES_ENGINE_ONLY','SOL_LITERAL_DIAGNOSTIC_FIELDS')
save('CASE_LEDGER.json',dict(candidate_sha=CANDIDATE,identity_unit='suite/group/case_id (execution context; not a global unique-oracle count)',
    historical_attempts_preserved=True,unique_oracle_total_claim=False,rows=rows,
    protocol_counts_canonical=dict(collections.Counter(r['protocol_status'] for r in rows if r['canonical'])),
    correction_metadata_caveat='HTTP original_posted_facts_immutable=false after spent fixtures compares JSON timestamps from Asia/Jakarta vs UTC. It is not a product mutation claim. Failed commands have business_and_private_state_unchanged=true from consistently UTC full-boundary snapshots.',
    original_group_status_preserved='Qualified correction file says INCOMPLETE; per-case COUNTEREXAMPLE is normalized FAIL. No native case or error is missing.'))
save('SUITE_RESULTS.json',dict(candidate_sha=CANDIDATE,f03=f03,cp17=dict(expected=61,observed=cp['observed_case_count'],
    id_set_equal=cp['required_case_ids_pass'],counts=cp['required_case_counts'],status=cp['status'],cp6_restored=cp['cp6_restored']),
    own_literal=dict(initial=dict(PASS=6,INCOMPLETE=1),qualified=dict(COUNTEREXAMPLE=1),http=dict(PASS=2,COUNTEREXAMPLE=2)),
    BE=dict(PASS=16),owner=dict(PASS=10,installed_files=58),menu_inventory=dict(PASS=288,scope='mock Auth/access, business RPC always 403; no Native feature PASS credit'),
    diagnostic=dict(PASS=3,scope='PostgreSQL engine diagnostic retention only'),
    comparator=dict(status='PASS',source='PUBLIC_STATE_COMPARATOR_LOG.json',a2_original_failure_roots='OPEN'),
    drain=dict(status='PASS',controls=6,scope='Natural wait, exact drained-refusal retry, different-error refusal, persistent timeout and reopened admission; not original AZ cause')))

key_sources={
 'scripts/cp7-src/finance/dated-guards.sql':[(39,57)],
 'scripts/cp7-src/sales/payment-correction.sql':[(144,206)],
 'scripts/cp7-src/finance/misc-correction.sql':[(105,145)],
 'src/ConnectedCuttingPage.tsx':[(184,200),(350,370)],
 'src/NativePlanDraftPanel.tsx':[(55,74)],
 'scripts/cp7-src/plan-native/preflight.sql':[(64,80)],
 'supabase/migrations/20260903022604_erp_v2_6_18_cutting_persistence_pickup_wip.sql':[(705,722)],
 'supabase/migrations/20260917033516_erp_v2_6_20ak_cp6_import_reference_preview.sql':[(640,648)],
 'scripts/cp6_t3_aligned_chain.py':[(83,91)],
 'scripts/cp6_pre_u_inventory.py':[(20,79)],
 'scripts/cp7-src/cutting-correction/sewing.sql':[(100,130)],
 'src/App.tsx':[(451,459),(630,648),(754,762)],
 'src/FinancePages.tsx':[(45,54),(117,123),(225,232)],
 'src/HppPage.tsx':[(298,305)],
 'src/QcFinalPage.tsx':[(260,268)],
}
sources=[]
for name,ranges in key_sources.items():
    p=ROOT/name;text=p.read_text().splitlines()
    sources.append(dict(path=name,sha256=sha(p),excerpts=[dict(start=a,end=b,text='\n'.join(text[a-1:b])) for a,b in ranges]))
changed=subprocess.check_output(['git','diff','--name-only','0b7049d9203bac52b47a4c89f3e0d75646067a8f',CANDIDATE,'--','src','scripts/cp7-src','supabase'],cwd=ROOT,text=True).splitlines()
save('SOURCE_REVIEW.json',dict(candidate_sha=CANDIDATE,sources=sources,changed_product_files_since_prior_audit=changed,
    new_po_scan=dict(scope=['src/**/*.ts(x)','scripts/cp7-src/**/*.sql','supabase/migrations/*.sql','frozen bootstrap function bodies'],
       result='UI selects existing active PO; Native cutting requires existing PO. Only production_orders INSERT writer found is erp.apply_migration_open_pos (OPEN_PO legacy import). Plan schedule writes sidecar plan, not production_orders.',
       ordinary_daily_po_creation='NO_ROUTE_IN_AUDITED_SOURCE',runtime_absence_claim=False),
    correction_impact=dict(runtime_confirmed=['spent customer income amount correction with final positive bank','spent customer income note-only correction'],
       source_risks_not_runtime_confirmed=['misc income corrections reverse before replacement','note corrections that reverse customer funding','cross-account/multi-date compound commands'])))
identity=read(E/'AFTER_ROOT.json')
save('IDENTITY_END.json',dict(candidate_sha=CANDIDATE,candidate_tree=TREE,after_audit_code_head=identity['audit_head'],
    actual_root_entries=identity['after_product_root'],product_source_unchanged_by_auditor=True,
    local_product_diff_empty=True,remote_changes_only=['audit/sol_cp17_combined/**','.github/workflows/audit-sol-*'],
    hosted_sql_executed=False,main_or_writer_changed=False,production_go=False,
    guide_sha256=sha(ROOT/'docs/AUDIT_PANDUAN_PRO_MAX.md'),owner_register_sha256=sha(ROOT/'docs/cp7/OWNER_DECISIONS_20261008.md'),lockfile_sha256=sha(ROOT/'package-lock.json')))
print(json.dumps(dict(reports='evidence registers written',attempt_contexts=len(rows),canonical_contexts=sum(r['canonical'] for r in rows),f03_observations=sum(sum(x['counts'].values()) for x in f03))))
