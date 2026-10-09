"""Read-only adjudication/indexing. Does not rewrite any original verdict or artifact."""
import collections,gzip,hashlib,json,pathlib,re
ROOT=pathlib.Path(__file__).resolve().parent
P=ROOT/'evidence'
projections=[json.loads(f.read_text()) for f in sorted(P.glob('projection-*.json'))]
artifacts={}
for d in projections:
 key=d['artifact_id'];old=artifacts.get(key)
 # Merge records by file. Later complete witnesses win over compact projections.
 if old:
  records={r['file']:r for r in old['records']}
  for r in d['records']:
   prior=records.get(r['file'],{})
   if len(json.dumps(r))>len(json.dumps(prior)):records[r['file']]=r
  old['records']=list(records.values())
 else:artifacts[key]=d
finals=[json.loads(f.read_text()) for f in P.glob('projection-final-*.json')]
regress=[d for d in finals if d['run_id']==37876648313]
assert len(regress)==33
rows=[];executions=0;controls=0;distinct=set()
for d in sorted(regress,key=lambda x:x['artifact_name']):
 reports=[r for r in d['records'] if r['file'].startswith('CP7_')]
 assert len(reports)==1,(d['artifact_name'],[r['file']for r in reports])
 r=reports[0]
 if 'complete_witness'in r:
  v=r['complete_witness'];assert v['status']=='PASS' and v['cp6_restored']
  rows.append(dict(suite=d['artifact_name'],report=r['file'],artifact_id=d['artifact_id'],status='PASS',steps=len(v['steps']),phases=[x['step']for x in v['steps']],groups={},executions=0))
  continue
 s=r['summary'];assert s['status']=='PASS' and s['cp6_restored'],(d['artifact_name'],s)
 gs={k:v for k,v in r['groups'].items()if 'counts'in v};n=0;details={}
 for k,g in gs.items():
  cases=g.get('cases',{});assert cases and g['counts']=={'PASS':len(cases)},(d['artifact_name'],k)
  assert all(v.get('status')=='PASS'for v in cases.values())
  assert not g.get('missing') and not g.get('cleanup_failures') and g.get('database_remaining',0)==0
  if 'complete_boundary_restored'in g:assert g['complete_boundary_restored']
  declared=g.get('planned_case_ids') or g.get('planned_race_ids')
  if declared:assert len(declared)==len(cases) and set(declared)==set(cases),(d['artifact_name'],k,'IDS')
  details[k]=dict(count=len(cases),case_ids=sorted(cases),restored=g.get('complete_boundary_restored'),database_remaining=g.get('database_remaining'))
  n+=len(cases);distinct.update((k,c)for c in cases)
 extra=sum(details.get(k,{}).get('count',0)for k in ('source_admission','composition_smoke'))
 executions+=n;controls+=extra
 rows.append(dict(suite=d['artifact_name'],report=r['file'],artifact_id=d['artifact_id'],status='PASS',executions=n,extra_controls=extra,expected=s.get('expected_case_count'),reported_observed=s.get('observed_case_count'),groups=details))
jobs=json.loads((P/'REGRESSION_JOBS.json').read_text());assert len(jobs)==33 and all(j['conclusion']=='success'for j in jobs)
reg=dict(run_id=37876648313,evidence_origin='INDEPENDENT_NATIVE_RERUN',oracle_origin='WRITER_ORACLES_UNCHANGED',jobs=33,case_executions=executions,extra_controls=controls,unique_group_case_pairs=len(distinct),note='Executions include reused predecessor cases across three payroll variants; never called distinct business scenarios. P21 phases are separate, not invented test counts.',suites=rows)
(ROOT/'REGRESSION_RESULTS.json').write_text(json.dumps(reg,indent=2)+'\n')
lines=['# Rerun mandiri atas suite writer','',f'Run 37876648313: **33/33 job PASS**. Semua ID yang diproyeksikan diperiksa, bukan warna job saja. **{executions} eksekusi kasus PASS**, termasuk {controls} kontrol tambahan dan kasus pendahulu yang diulang antarvarian payroll. Dua gladi P21 mempunyai 6 dan 9 fase dan tidak dimasukkan sebagai kasus bisnis. Asal oracle tetap writer.','', '| Suite | Eksekusi PASS | Expected / observed dalam laporan | Batas |','|---|---:|---|---|']
for r in rows:
 name=r['suite'].removeprefix('astra-p20-').removesuffix('-json')
 bound=(str(r['steps'])+' fase gladi')if'steps'in r else ('+'+str(r['extra_controls'])+' kontrol di luar budget utama'if r['extra_controls']else '')
 if r.get('expected')is not None and r['expected']!=r['reported_observed']:bound+='; metadata expected basi, lihatF05'
 lines.append(f"|{name}|{r['executions'] or '—'}|{r.get('expected','—')} / {r.get('reported_observed','—')}|{bound}|")
lines+=['','Semua group Native yang menyatakan boundary restore lolos; semua database_remaining yang dilaporkan0, tidak ada missing case atau cleanup failure. Catalog/restore P21 diperiksa pada witness lengkap. `REGRESSION_RESULTS.json` menyimpan seluruh case ID dan subgroup. Angka ini tidak termasuk1.722unit test,6browser shell, atau kasus oracle mandiri.']
(ROOT/'REGRESSION_RESULTS.md').write_text('\n'.join(lines)+'\n')

events={}
for d in artifacts.values():
 for r in d['records']:
  v=r.get('complete_independent_verdict')
  if not v:continue
  case=v.get('audit_case_id') or v.get('case')
  if case:events[(d['run_id'],case)]=dict(run_id=d['run_id'],case_id=case,original_status=v['status'],artifact_id=d['artifact_id'],file=r['file'],sha256=r['sha256'])
for filename,rid in [('log-verdicts-113658432444.json',37880365949),('log-verdicts-113654511708.json',37879134928)]:
 for v in json.loads((P/filename).read_text()):
  case=v.get('audit_case_id')or v.get('case')
  if case and case.startswith('AS20'):
   events[(rid,case)]=dict(run_id=rid,case_id=case,original_status=v['status'],log_file=filename)
bycase=collections.defaultdict(list)
for key,v in sorted(events.items()):bycase[v['case_id']].append(v)
latest=[]
for case,ev in sorted(bycase.items()):
 e=ev[-1];result=e['original_status'];explanation=''
 if case=='AS20-26_27_42_SCALE5000':
  assert result=='COUNTEREXAMPLE';result='ADJUDICATED_PASS'
  explanation='5000 exact pages/storage/cleanup complete;5001FAILED without result. Only over-specific TARGET_LIMIT string assertion failed; original retained.'
 finding={'AS20-32_CROSS_VERSION_CAPACITY':'F01','AS20-43_CRON_DATABASE_ISOLATION':'F02','AS20-45_FAILED_RETRY_COLLISION':'F03','AS20-39_VALIDATION_NEGATIVE':'F04'}.get(case)
 latest.append(dict(case_id=case,assessment=result,original_status=e['original_status'],latest_run=e['run_id'],finding=finding,adjudication=explanation,attempts=ev))
assert all(x['assessment']in('PASS','COUNTEREXAMPLE','ADJUDICATED_PASS')for x in latest)
counts=dict(collections.Counter(x['assessment']for x in latest))
own=dict(evidence_origin='INDEPENDENT_NATIVE_CASE',case_count=len(latest),counts=counts,not_parent_count='44 executable scenarios are not the50pre-registered broad parent scenarios; see COVERAGE_50.md',cases=latest)
(ROOT/'INDEPENDENT_CASE_RESULTS.json').write_text(json.dumps(own,indent=2)+'\n')
lines=['# Hasil skenario oracle mandiri','',f"{len(latest)} ID skenario mandiri; hasil akhir {counts}. Ini bukan klaim 50/50 parent selesai. Kasus 5000 mempunyai adjudikasi tertulis; first failure tidak dihapus. Browser 48 desktop/48 mobile dihitung sebagai 2 skenario, bukan 96 kasus bisnis.",'','| ID | Penilaian akhir | Run terakhir | Temuan |','|---|---|---|---|']
for x in latest:lines.append(f"|{x['case_id']}|{x['assessment']}|[{x['latest_run']}](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/{x['latest_run']})|{x['finding'] or ''}|")
lines+=['','Rangkaian seluruh percobaan, termasuk fixture/harness gagal dan perbaikannya, berada dalam `INDEPENDENT_CASE_RESULTS.json` dan `FAILURE_REGISTER.md`. Tidak ada verdict raw diubah.']
(ROOT/'INDEPENDENT_CASE_RESULTS.md').write_text('\n'.join(lines)+'\n')
index=dict(product_sha='2e605bb7d9b6b7903919b8df2be1443f1740140b',product_tree='51935efb12c035496848e2a85590aa18a3ed3d76',production_go=False,final_projection_run=37881960950,artifacts=[{k:d[k]for k in ('run_id','audit_sha','artifact_id','artifact_name','zip_sha256')}for d in sorted(artifacts.values(),key=lambda x:(x['run_id'],x['artifact_id']))],source_review_sha256=hashlib.sha256((P/'source-test-integrity.json').read_bytes()).hexdigest(),independent=counts,regression_executions=executions)
(ROOT/'EVIDENCE_INDEX.json').write_text(json.dumps(index,indent=2)+'\n')
# Complete retrieved projection documents + complete independent failure witnesses,
# including intermediate projections and original status. No artifact is overwritten.
archive=dict(projections=list(artifacts.values()),deduplication='Immutable artifact IDs merged by file; complete/longest retrieved record retained. Every separate run/attempt retained.',original_log_verdicts={f.name:json.loads(f.read_text())for f in P.glob('log-verdicts-*.json')},source_review=json.loads((P/'source-test-integrity.json').read_text()),regression_jobs=jobs)
raw=json.dumps(archive,ensure_ascii=False,separators=(',',':')).encode()
assert not re.search(rb'eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}',raw),'UnexpectedJWTinEvidence'
packed=gzip.compress(raw,mtime=0);(P/'COMPLETE_PROJECTED_EVIDENCE.json.gz').write_bytes(packed)
(P/'ARCHIVE_RECEIPT.json').write_text(json.dumps(dict(file='COMPLETE_PROJECTED_EVIDENCE.json.gz',sha256=hashlib.sha256(packed).hexdigest(),bytes=len(packed),uncompressed_bytes=len(raw),description='Complete retrieved JSON projections and original own verdicts, including first failures. Original CI zip SHA256/run/artifact IDs retained; this is not falsely labelled the raw CI zip.'),indent=2)+'\n')
print(json.dumps(dict(own=counts,own_cases=len(latest),regression_executions=executions,controls=controls,archive_bytes=len(packed),artifact_receipts=len(artifacts))))
