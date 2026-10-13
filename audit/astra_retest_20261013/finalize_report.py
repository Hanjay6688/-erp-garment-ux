"""Fill final counts only when every preregistered regression report and job is present."""
from pathlib import Path
import json

R=Path(__file__).resolve().parent
d=json.loads((R/'REGRESSION_RESULTS.json').read_text())
receipt=json.loads((R/'FINAL_CI_RECEIPT.json').read_text())
s=d['summary'];jobs={j['name']:j for j in receipt['regression_jobs']}
assert s['reports']==21 and len(jobs)==21
assert set(jobs)=={r['suite'] for r in d['reports']}
assert all(j['status']=='completed' and j['conclusion']=='success' for j in jobs.values())
assert s['counts']=={'PASS':s['case_executions']}
table=['| Suite / job | Kasus PASS | Pemulihan / advisor |','|---|---:|---|']
for r in d['reports']:
    j=jobs[r['suite']]
    count=str(r['case_executions']) if r['case_executions'] else '9 fase rehearsal; bukan kasus bisnis'
    table.append(f"| [{r['suite']}]({j['html_url']}) | {count} | Lulus / lulus |")
paragraph=f"Seluruh **21/21 suite selesai pada percobaan pertama**: **{s['case_executions']} eksekusi kasus PASS**, mencakup **{s['unique_case_ids']} ID kasus unik**, ditambah sembilan fase rehearsal. Kasus yang sama dalam komposisi berbeda tidak diklaim sebagai kasus unik tambahan. Semua gate pemulihan/advisor yang dideklarasikan lulus. Tidak ada retry pergantian hari pada regresi bisnis ini. Nama suite lama tidak dipakai sebagai hitungan: transport berisi 15 kasus, staged 14, plan 43, attention 286, dan F03 P12 91. [REGRESSION_LABEL_MAP.json](REGRESSION_LABEL_MAP.json) menjelaskan dua label lama dalam manifest awal.\n\n"+'\n'.join(table)
p=R/'REPORT.md';text=p.read_text()
text=text.replace('**DRAF BERJALAN — menunggu seluruh regresi yang sudah didaftarkan; bukan laporan terkunci.**','**LAPORAN TERKUNCI — retest temuan dan delta; keputusan HOLD, `production_go:false`.**')
old='Ada 21 suite yang didaftarkan sebelum eksekusi; status akhir dan hitungan per kasus akan diisi setelah seluruh run selesai. Nama suite lama seperti `transport11` tidak dipakai sebagai hitungan; Original saat ini memuat 15 kasus transport dan 14 staged.'
assert old in text;text=text.replace(old,paragraph)
text=text.replace('Arsip checkpoint berisi Original dan kedua log gagal pertama; paket bukti final dan hash penguncian menyusul setelah regresi selesai.','[FINAL_ORIGINALS.tar.xz](FINAL_ORIGINALS.tar.xz) menyimpan seluruh Original JSON per job tanpa pemotongan, dua log gagal pertama, log diagnosis CP6 lama, SARIF, screenshot mandiri, dan indeks unduhan. [ORIGINALS_MANIFEST.json](ORIGINALS_MANIFEST.json) memberi ukuran/hash tiap berkas dan menjelaskan arsip raw besar yang tetap tersedia di CI. [LOCK.json](LOCK.json) mengikat laporan, handoff, receipt dan arsip final. Semua anggota arsip sudah diekstrak dalam memori dan hash-nya dicocokkan kembali.')
text=text.replace('Keputusan sementara: **HOLD**','Keputusan retest: **HOLD**')
assert 'DRAF' not in text and 'akan diisi' not in text
p.write_text(text)
p=R/'WRITER_HANDOFF.md';text=p.read_text()
text=text.replace('**DRAF BERJALAN; tunggu penguncian laporan sebelum menjadikan ini hasil final.**','**FINAL — laporan dan bukti terkunci; tidak ada job retest yang masih berjalan.**')
text=text.replace('Regresi 21 suite masih berjalan.',f"Regresi 21/21 suite selesai: {s['case_executions']} eksekusi PASS / {s['unique_case_ids']} ID unik, ditambah sembilan fase rehearsal. Shell 1.726 tes dan enam browser lulus; dua CodeQL nol temuan. Ini tidak menggantikan penerimaan PR44.")
text=text.replace('ada pada paket laporan final saat terkunci.','tersimpan pada [REPORT.md](REPORT.md), [REGRESSION_RESULTS.json](REGRESSION_RESULTS.json), [FINAL_CI_RECEIPT.json](FINAL_CI_RECEIPT.json), [FINAL_ORIGINALS.tar.xz](FINAL_ORIGINALS.tar.xz), dan [LOCK.json](LOCK.json).')
assert 'DRAF' not in text and 'masih berjalan' not in text.replace('tidak ada job retest yang masih berjalan','')
p.write_text(text)
print(json.dumps({'final_reports_written':True,'regression':s}))
