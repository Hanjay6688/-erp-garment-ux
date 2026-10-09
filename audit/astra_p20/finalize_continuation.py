"""Add independent continuation receipts without altering original raw verdicts."""
import collections,gzip,hashlib,json,pathlib,re
ROOT=pathlib.Path(__file__).resolve().parent;P=ROOT/'evidence'
documents=[json.loads(f.read_text()) for f in sorted(P.glob('projection-cont-*.json'))]
assert documents,'No retrieved continuation evidence'
artifacts={d['artifact_id']:d for d in documents};events={};summaries=[]
for d in artifacts.values():
    for r in d['records']:
        v=r.get('complete_independent_verdict')
        if v:
            case=v.get('audit_case_id') or v.get('case')
            if case and case.startswith('AS20C-'):
                events[d['run_id'],case]=dict(run_id=d['run_id'],case_id=case,original_status=v['status'],artifact_id=d['artifact_id'],file=r['file'],sha256=r['sha256'])
        if r['file'].startswith('ASTRA_P20_INDEPENDENT_CONT_'):
            s=r['summary'];assert s.get('restore')==dict(boundary=True,public=True,functions=True),(d['run_id'],s)
            for g in r.get('groups',{}).values():
                assert not g.get('missing') and not g.get('cleanup_failures') and g.get('database_remaining',0)==0,(d['run_id'],g)
                if 'complete_boundary_restored' in g:assert g['complete_boundary_restored']
            summaries.append(dict(run_id=d['run_id'],audit_sha=d['audit_sha'],report=r['file'],summary=s,groups=r.get('groups',{})))
bycase=collections.defaultdict(list)
for (_,case),e in sorted(events.items()):bycase[case].append(e)
expected=set(re.findall(r'AS20C-[0-9]+-[A-Z0-9-]+',(ROOT/'CONTINUATION_PLAN.md').read_text()))
assert set(bycase)==expected,(sorted(expected-set(bycase)),sorted(set(bycase)-expected))
latest=[]
for case,ev in sorted(bycase.items()):
    e=ev[-1];assessment=e['original_status'];why=''
    assert assessment=='PASS',(case,e)
    if case=='AS20C-22-TIE':
        assessment='ADJUDICATED_PASS'
        why='First assertion compared the entire allocation including deliberately reordered matching input echo. Targeted runtime proves rows, edges, quantities, refs and verdict unchanged; only that echoed array order differs. Full first/reordered responses retained. Earlier deadline and unknown timing controls pass.'
    if case=='AS20C-18-ROSTER':
        assessment='ADJUDICATED_PASS'
        why='Auditor first expected manual-reimbursement LABOR_COST; accepted CP3 attendance approval accrues into unassigned WIP. Targeted runtime retains38.82 amount/payable and all worker identity, existing6000 work and replay checks; full first mismatch preserved.'
    latest.append(dict(case_id=case,assessment=assessment,original_status=e['original_status'],latest_run=e['run_id'],finding=None,adjudication=why,attempts=ev))
counts=dict(collections.Counter(x['assessment'] for x in latest))
out=dict(product_sha='2e605bb7d9b6b7903919b8df2be1443f1740140b',evidence_origin='INDEPENDENT_NATIVE_AND_BROWSER_CASES',oracle_origin='ASTRA_CONTRACT_AND_NUMERICAL_ORACLES',case_count=len(latest),counts=counts,production_go=False,cases=latest,run_reports=summaries)
(ROOT/'CONTINUATION_RESULTS.json').write_text(json.dumps(out,indent=2)+'\n')
lines=['# Hasil kelanjutan audit mandiri','',f"{len(latest)} ID tambahan: {counts}. Percobaan ulang tidak dihitung sebagai kasus baru. Semua hasil berasal dari kandidat2e605bb7 yang sama; ini bukan retest revisi produk.",'','| ID | Penilaian | Run terakhir |','|---|---|---|']
for x in latest:lines.append(f"|{x['case_id']}|{x['assessment']}|[{x['latest_run']}](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/{x['latest_run']})|")
lines+=['','Setiap report mencatat pemulihan boundary/public/functions=true; setiap database_remaining yang tersedia=0. Semua first failure tetap dalam JSON/arsip dan FAILURE_REGISTER.md. TIE ditutup oleh adjudikasi runtime yang dijelaskan lengkap dalam JSON. Hasil ini tidak menutup F01–F05 dan tidak memberikan penerimaan bebas konflik untuk PR44.']
(ROOT/'CONTINUATION_RESULTS.md').write_text('\n'.join(lines)+'\n')
own=json.loads((ROOT/'INDEPENDENT_CASE_RESULTS.json').read_text());original=[x for x in own['cases'] if not x['case_id'].startswith('AS20C-')]
assert len(original)==44
own.update(evidence_origin='INDEPENDENT_NATIVE_AND_BROWSER_CASES',case_count=len(original)+len(latest),cases=sorted(original+latest,key=lambda x:x['case_id']),not_parent_count='Executable scenario IDs are not the50pre-registered broad parent scenarios; see COVERAGE_50.md')
own['counts']=dict(collections.Counter(x['assessment'] for x in own['cases']))
(ROOT/'INDEPENDENT_CASE_RESULTS.json').write_text(json.dumps(own,indent=2)+'\n')
lines=['# Hasil skenario oracle mandiri','',f"{own['case_count']} ID skenario mandiri; hasil akhir {own['counts']}. Ini bukan klaim50/50parent selesai. Semua first failure dan adjudikasi tetap terlihat. Navigasi48desktop/48mobile dihitung2skenario; dua perjalanan browser tulis dihitung2skenario tambahan.",'','| ID | Penilaian akhir | Run terakhir | Temuan |','|---|---|---|---|']
for x in own['cases']:lines.append(f"|{x['case_id']}|{x['assessment']}|[{x['latest_run']}](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/{x['latest_run']})|{x['finding'] or ''}|")
lines+=['','Rangkaian setiap percobaan ada pada INDEPENDENT_CASE_RESULTS.json, CONTINUATION_RESULTS.json dan FAILURE_REGISTER.md; tidak ada verdict raw diubah.']
(ROOT/'INDEPENDENT_CASE_RESULTS.md').write_text('\n'.join(lines)+'\n')
archive=dict(projections=list(artifacts.values()),original_continuation_logs={f.name:json.loads(f.read_text()) for f in P.glob('CONT_*_LOG_VERDICTS.json')},assessment=out)
raw=json.dumps(archive,ensure_ascii=False,separators=(',',':')).encode()
assert not re.search(rb'eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}',raw),'Unexpected JWT'
packed=gzip.compress(raw,mtime=0);filename='CONTINUATION_PROJECTED_EVIDENCE.json.gz';(P/filename).write_bytes(packed)
receipt=dict(file=filename,sha256=hashlib.sha256(packed).hexdigest(),bytes=len(packed),uncompressed_bytes=len(raw),description='Complete continuation verdicts, first failures and priority input-echo diagnostic; original CI zip IDs and SHA256 retained. Original audit archive remains unchanged.')
(P/'CONTINUATION_ARCHIVE_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
index=json.loads((ROOT/'EVIDENCE_INDEX.json').read_text());known={x['artifact_id']:x for x in index['artifacts']}
for d in artifacts.values():known[d['artifact_id']]={k:d[k] for k in ('run_id','audit_sha','artifact_id','artifact_name','zip_sha256')}
index.update(artifacts=sorted(known.values(),key=lambda x:(x['run_id'],x['artifact_id'])),independent=own['counts'],continuation=counts,continuation_archive=receipt,continuation_projection_runs=json.loads((P/'CONTINUATION_PROJECTION_RUNS.json').read_text()))
(ROOT/'EVIDENCE_INDEX.json').write_text(json.dumps(index,indent=2)+'\n')
print(json.dumps(dict(added=len(latest),continuation=counts,total=own['case_count'],overall=own['counts'],archive_bytes=len(packed),runs=len(summaries))))
