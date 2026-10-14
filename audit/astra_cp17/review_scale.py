"""Review declared scale IDs and every staged vector; no rerun or status rewrite."""
from pathlib import Path
import json,collections,hashlib
p=Path(__file__).resolve().parent
root=p.parents[1]
o=p/'continuation/38558465155/11895379201/original'
d=json.loads((o/'CP7_P19_SCALE.json').read_text())
decl_path=root/'docs/cp7/p19/P19_SCALE.json'
decl=json.loads(decl_path.read_text())
assert d['cp6_restored'] and d['advisor_gate']and d['observed_case_count']==5
# Producer hashes declaration_bytes, not the Python case file.
assert d['predeclared_case_sha256']==hashlib.sha256(decl_path.read_bytes()).hexdigest()
for group,ids in decl['required_case_ids'].items():assert set(d[group]['cases'])==set(ids)
rows=[];staged=[]
for case,v in d['browser']['cases'].items():
 assert v['status']=='PASS' and len(v['measurements'])==12 and v['sql_ladder']['status']=='PASS'
 assert v['sql_ladder']['phase_profile_complete'] and v['sql_ladder']['Native_business_unchanged_by_measurement']
 for m in v['measurements']:
  rows.append(dict(case=case,size=v['size'],**m))
  if m['control']=='STAGED':
   s=m['staged'];assert s['job_state']=='DONE' and s['targets_total']==v['size']and s['pages_read']==s['page_count']and s['units_done']==s['unit_count']
   assert len(m['page_loads'])==s['page_count']-1 and all(x['trusted_click']and x['within_target']for x in m['page_loads'])
   assert m['completed_open']['trusted_click']and m['completed_open']['within_target']
   staged.append(dict(size=v['size'],history_days=m['history_days'],fresh_ms=m['click_to_complete_ms'],ack_ms=m['click_to_first_status_ms'],progress_ms=s['click_to_staged_progress_ms'],completed_open_ms=m['completed_open']['elapsed_ms'],page_count=s['page_count'],page_load_min_ms=min([x['elapsed_ms']for x in m['page_loads']],default=None),page_load_max_ms=max([x['elapsed_ms']for x in m['page_loads']],default=None)))
result=dict(run_id=38558465155,job_id=115833361095,artifact_id=11895379201,artifact_sha256=hashlib.sha256((o.parent/'original.zip').read_bytes()).hexdigest(),expected_case_count=5,case_statuses={k:v['status']for group in('native','browser')for k,v in d[group]['cases'].items()},click_measurement_count=len(rows),browser_verdict_counts=dict(collections.Counter(r['verdict']['kind']for r in rows)),staged_vectors=staged,cp6_restored=d['cp6_restored'],advisor_gate=d['advisor_gate'],owner_latency_acceptance=False,factory_capacity_or_SLA=False,production_go=False,measurements=rows)
(p/'SCALE_OBSERVATION.json').write_text(json.dumps(result,indent=2)+'\n')
md=['# Hasil ukur skala Astra pada kandidat beku','',
 'Run 38558465155 / job 115833361095 / artifact 11895379201. Lima kasus wajib PASS: satu Native, empat browser desktop Auth nyata. Ada 48 klik pengukuran di dalam empat kasus browser, bukan tambahan 48 kasus bisnis. Sebanyak 25 klik menghasilkan data lengkap, 23 menolak jujur sesuai cap. Restore/advisor true; batas RPC 8 detik dan halaman 8.000.000 byte tidak dinaikkan.','',
 '| Target | Riwayat hari | Hitung baru → hasil pertama (detik) | Buka DONE (detik) | Halaman lengkap |','|---:|---:|---:|---:|---:|']
for r in staged:md.append(f"| {r['size']} | {r['history_days']} | {r['fresh_ms']/1000:.3f} | {r['completed_open_ms']/1000:.3f} | {r['page_count']} |")
md+=['',
 'Seluruh 12 vektor staged COMPLETE_RESULT, termasuk 5.000 target × 1/30/100 hari dengan 26/26 halaman. Semua klik halaman lanjutan dan buka DONE memenuhi target 3 detik yang diuji. Hitung baru 5.000 target memerlukan 84,955–104,767 detik; ini tidak disebut hasil lengkap 3 detik.','',
 'Jalur capture/background biasa pada 1.000 target menolak di 8 detik; 5.000 target menolak batas sumber 1.000 produk. Capture dengan laporan keuangan menolak 8 detik pada 11 dari 12 vektor; 100 target × 100 hari menyelesaikan 7,355 detik. Penolakan jelas bukan bukti kapasitas menghitung semua ukuran lewat jalur tersebut.','',
 'Hasil satu runner Chromium/loopback dan fixture sintetis. Bukan SLA/kapasitas pabrik, bukan penerimaan latensi owner, bukan speedup A/B. Header/page identity, seluruh target dan kontrol sumber diperiksa suite; Original lengkap dan log pertama diarsipkan. Pengamatan ini tidak menghapus temuan keuangan/stok pada laporan utama.','']
(p/'SCALE_REVIEW.md').write_text('\n'.join(md))
print(json.dumps({k:v for k,v in result.items()if k not in('measurements','staged_vectors')},indent=2))
