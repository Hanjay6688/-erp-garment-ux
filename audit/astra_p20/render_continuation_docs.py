"""Render only after all registered continuation cases have final evidence."""
from pathlib import Path
import json
p=Path(__file__).resolve().parent
c=json.loads((p/'CONTINUATION_RESULTS.json').read_text());all_results=json.loads((p/'INDEPENDENT_CASE_RESULTS.json').read_text())
assert c['case_count']==23 and all(x['assessment'] in ('PASS','ADJUDICATED_PASS') for x in c['cases'])
runs={x['case_id']:x['latest_run'] for x in c['cases']}
updates={
'01':('SEBAGIAN: tambah11endpoint staged/cache/AI/report/reminder: positif dahulu, lalu izin WIP dicabut dan seluruhnya ditolak','AS20C-01-CONSUMERS; hasil tersimpan tidak berubah. Aktor ADMIN aktif dengan4viewpermission; tidak mengklaim seluruh kombinasi actor×action.'),
'04':('MANDIRI pada replay yang dipilih; receipt UUID lintas aktor/aksi tidak membocorkan sukses atau menggandakan stok','AS20C-04-ACTOR; tambahan matriks setiap facade tetap rerun, bukan dibuat sendiri semua.'),
'05':('MANDIRI: receipt commit lalu respons dibuang/reconnect; mobile RETURN respons HTTP benar-benar dibatalkan sesudah server sukses','AS20C-05-LOST dan AS20C-47-WRITE-MOBILE. Reload/reconcile memakai UUID+body identik; satu efek. Receipt memakai simulasi client-discard yang dilabeli.'),
'07':('MANDIRI: batas nominal besar ditambah diskon0.01 dan13.17 pada invoice riil','AS20C-07-DISCOUNT: net21.474.836,47 dan21.999.986,84; AP/cost/jurnal tepat. Bukan semua kombinasi tarif.'),
'08':('MANDIRI: unequal sizes11+7, umum1.37/PCS dan extra2.03 hanya3PCS ukuran kedua','AS20C-08-SIZE:15.07/15.68,total30.75 hingga receipt dan FG; ukuran pertama tidak menerima extra. Enam desimal dan bayar sen tetap lulus sebelumnya.'),
'09':('MANDIRI: tengah malam WIB ditambah koreksi jual setelah economic day ditutup','AS20C-09-CLOSED: tanggal jurnal lama utuh, jurnal koreksi setelah close, FG33/AR102.25. Tidak mengarang larangan semua koreksi backdate.'),
'11':('MANDIRI: two-stage invoice dan retur supplier nyata5×7.31; credit36.55 dipindah ke invoice lain','AS20C-11-RETURN: AP58.48/80.41→95.03/43.86; alokasi tidak menambah stok/kas, dependency guard dan inverse lulus. Bukan semua variasi AP.'),
'13':('MANDIRI: native dan dua perjalanan UI jual13/bayar137.03/retur4, GradeA serta GradeB','AS20C-47-WRITE-DESKTOP/MOBILE; FG32/AR132.16/COGS148.14. Multi-lot diperluas rerun; tidak diklaim baru dibuat sendiri.'),
'15':('MANDIRI: konservasi137ditambah2operator19+17berebut30siap-QC','AS20C-15-RACE: satu winner, replay satu efek; sisa sah diproses hingga100input=70WIP+30FG. Tidak menyembuhkan F01 yang berbeda.'),
'17':('MANDIRI: recost lateinvoice sesudah sale+return dan koreksi closedperiod','AS20C-50-LATE serta09-CLOSED; source/economic/posting date dan biaya diperiksa. Bukan seluruh kombinasi dalam satu skenario.'),
'18':('SEBAGIAN: tambah2pekerja Rina berkode/IDbeda, rate23.17/31.29, full/halfday38.815→38.82','AS20C-18-ROSTER: labor6000tetap,net6038.82; approval WIP/payable38.82 sekali dan replay. Salah akun awal auditor dipisahkan. Netnegatif dan semua repair tetap diperluas rerun.'),
'19':('SEBAGIAN: tambah2payroll berebut4carry×2.50; hanya satu dapat hak','AS20C-19-CARRY:4unit/10sekali, expense+payable tepat,replay tidak duplikat. Earliest automatic accessory-carry selection belum punya oracle baru.'),
'22':('MANDIRI: native need130/supply5/gap125 serta source17dibagi11/6dengan tie-break ID','AS20C-22-NET/TIE: lateETA tidak menghapus gap lebih awal; urutan input tidak mengubah hasil, deadline mendahului ID, unknown masuk review. Tie adalah kernel; bukan posting native semua adapter.'),
'23':('MANDIRI: kalender37+83,otherload61+7,captured11+13+17,3menit/PCS→3PCS','AS20C-23-SPILL: beban melewati kalender menjadiUNKNOWN.71case schedule rerun tetap tambahan; F01 tetap terbuka.'),
'24':('SEBAGIAN: tambah199PCS insufficient,200PCS memenuhi threshold dan Wilson dihitung sendiri','AS20C-24-199 plus205/193sebelumnya. Tepat180hari dan semua fallback same-model tetap rerun, tidak diklaim oracle baru.'),
'25':('MANDIRI: reverse BS membuka kembali grup yang sebelumnya habis; proof lama immutable','AS20C-25-REOPEN: re-dispose saja tidak mengaktifkan proof lama; proof baru sah mengembalikan eligibility. Skala long-history tambahan rerun.'),
'27':('SEBAGIAN:5001ditolak; labelไทย🧵é dipertahankan dan panjang/hash dihitung UTF8','AS20C-27-UTF8: injeksi client root_ids=[] ditolak. Belum membuktikan pabrik global benar-benar tanpa produk; tidak menyamakan kedua kasus.'),
'28':('MANDIRI: reconnect/DONE ditambah2stepworker bersamaan dan heldjob busycontrol','AS20C-28-WORKERS:20unit=20outputunik,hashpages tepat,DONE3kali tidak menulis ulang retained rows.'),
'29':('SEBAGIAN: perubahan master mulai sebelumcapture, commit sesudahcapture;freshness berubah,oldpages identik','AS20C-29-INFLIGHT juga memeriksa delete. Hanya MASTER_DATA; bukan seluruh kategori perubahan. PR44 tetap butuh penerimaan auditor lain.'),
'34':('MANDIRI: dua publikasi expectedrevision1 benar-benar menunggu kunci series lalu berebut seal','AS20C-34-PUBLISH:1DONE/1FAILED,revisions[1,2],SHA256section+report dihitung sendiri; tidak ada campur output.'),
'37':('MANDIRI:7hari±30detik ditambah job yang benar-benarFAILED akibat accesschange','AS20C-37-FAILED:failureevidence dipertahankan,purge1receipt,clean-as-DONE ditolak. Staged mendukungRUNNING/DONE/FAILED; tidak mengarang endpointCANCELLED.'),
'47':('SEBAGIAN:48rute×desktop/mobile ditambah2perjalanan tulis UI dengan oracle uang/stok sendiri','CREATE→POST→PAY→RETURN→paymentinverse→returninverse→saleinverse;GradeA/B,mobile lostHTTPresponse,reload,reconcile,screenshots. Bukan setiapcommand/role diuji sendiri.'),
'50':('MANDIRI pada rangkaian73receipt→41FG→13sale→4return→lateinvoice17+56','AS20C-50-LATE:AP889.83,GRNI0,raw32/FG32,AR132.16;recost ke raw/FG/COGS exact. Koreksi closedperiod merupakan variasi terpisah; bukan semua kombinasi dunia nyata.')}
path=p/'COVERAGE_50.md';s=path.read_text().replace('Hasil nyata terdiri dari44ID kasus oracle mandiri','Hasil nyata terdiri dari67ID kasus oracle mandiri (44awal+23kelanjutan)')
lines=s.splitlines()
for i,line in enumerate(lines):
    if line.startswith('|') and line[1:3] in updates:
        cells=line.split('|');a,b=updates[line[1:3]];lines[i]='|'+cells[1]+'|'+a+'|'+b+'|'
path.write_text('\n'.join(lines)+'\n')

failure='''
## Kelanjutan setelah laporan awal — first failures tetap utuh

- Run37892630236: discount, size dan late fullflow PASS. AS20C-04-ACTOR berhenti karena auditor menulis material_purchases, bukan material_purchase_headers. AUDITOR_FIXTURE; hanya kasus itu dilanjutkan di37893419603danPASS.
- Run37892863976: retentionFAILED danUTF8 PASS. Consumer fixture memakai custom role code yang memang bukan internal role untuk reminder. Run37893519004memakaiSTAFF tetapi baseline legacySTAFF sengaja nonaktif, sehingga positive start ditolak. Keduanya AUDITOR_FIXTURE; tidak ada produk diubah. Run37894257418menggunakanADMINaktif dengan4permission, lalu cabutWIP:11endpoint positif dahulu,seluruh11ditolaksetelahrevoke danretainedunchanged.
- Run37893074616:5racePASS. AS20C-15-RACE telah melewati admission/replay tetapi final drain auditor masih PARTIAL_SELECTIONmeski menghabiskan sisa. Produk benar menolak. Mode final control digantiALL_READY; targeted37893987955PASS. Dua input race19+17danoracle30tetap.
- Run37893419603: actor,returncredit,closedperiodPASS. Roster gagal pada duplicate Python keyword helper, sebelumCREATE. Priority mencapaiA11/B6tetapi assertion membandingkan inputecho yang sengaja dipermutasi. Keduanya first failure disimpan. Targeted37894141652membuktikan baris/edges/quantity/refs/verdict identik; hanya order inputecho berbeda. Earlier deadline/unknowncontrolsPASS. ADJUDICATED_PASS, bukan bug produk.
- Roster37894141652: pekerja/amount38.815→38.82/payroll6038.82benar; akun debit aktualWIP dibandingkan auditor denganLABOR_COST. Kontrak CP3 yang diterima menempatkan approvalattendance diWIP sebelum alokasiSELESAI_DIJAHIT;LABOR_COSTuntukmanualreimbursement berbeda. Salah oracle akun auditor diperbaiki secara terbuka, angka/kewajiban/replaytetap. Targeted final roster{roster}PASS dan identity/replaydituntaskan. ADJUDICATED_PASS, bukan alasan meminta writer mengubah kebijakan.

- Browser37894527264: kedua perjalanan sudah menjalankan7command200danfullinverse. Pembanding terakhir auditor membandingkan dictionaryGLsecara struktural; akun yang baru punya jurnal muncul dengan saldo0.00setelahinverse. RawINCOMPLETEtetap. Adjudicate_browser.pymembandingkansemuaIDakun(default0),kontrol+0.01akunlama/baruterdeteksi,danmemeriksa final41FG,raw32/395.84,semuariwayatreversed,jurnalbalance. Bukti runtimelengkaptelahtersimpan,sehinggatidakadaulangruntime. ADJUDICATED_PASSuntukkedualayar.

Semua raw verdict,trace,runIDdanhashartifact tetap berada dalam CONTINUATION_RESULTS.json serta evidence/CONTINUATION_PROJECTED_EVIDENCE.json.gz. Semua pemulihan boundary/public/functions tercatattrue. Tidak ada kasus lulus diulang sekadar untuk menambah hitungan.
'''.format(roster=runs['AS20C-18-ROSTER'])
path=p/'FAILURE_REGISTER.md';s=path.read_text();marker='\n## Kelanjutan setelah laporan awal';s=s.split(marker)[0]+failure;path.write_text(s)

paragraph="""
## Kelanjutan independen yang selesai

Kelanjutan menambahkan **23 ID: 19 PASS mentah dan 4 ADJUDICATED_PASS**. Total sekarang **67 ID: 58 PASS mentah, 5 ADJUDICATED_PASS, dan 4 COUNTEREXAMPLE**. First failure tetap tersimpan. Ini bukan klaim bahwa 50 parent sudah tertutup seluruhnya. Kandidat produk tetap `2e605bb7`; belum ada revisi produk untuk diretest. **F01–F05 tetap terbuka.**

- **Uang dan stok:** invoice besar dengan diskon; extra jasa hanya untuk ukuran yang menerima; kredit retur supplier Rp36,55 ke invoice lain; koreksi setelah tutup buku; invoice bahan datang setelah penjualan dan retur, lalu rekonsiliasi biaya bahan, FG, dan COGS. Semua menggunakan angka pembanding auditor.
- **Perencanaan:** kebutuhan130 dikurangi supply5 menyisakan125; sisa kapasitas3PCS dan beban di luar kalender menjadi UNKNOWN; batas sampel PL5 pada199/200PCS; bukti grup habis setelah barang dibuka kembali; prioritas berdasarkan deadline dan ID. Uji prioritas adalah uji kernel, bukan klaim semua adapter posting telah diperiksa.
- **Benturan dan pemulihan:** dua penerimaan19+17 berebut30PCS; dua worker analisis; dua publikasi revisi laporan; dua payroll berebut carry4×2,50; receipt yang responsnya dibuang setelah commit. Semuanya lulus pada skenario tersebut. F01 lintas versi rencana adalah kasus berbeda dan tetap blocker.
- **Akses dan retensi:** sebelas endpoint cache, laporan, pengingat, dan AI ditolak setelah izin dicabut. Job yang benar-benar gagal tetap mengikuti batas retensi7hari. Label Unicode dipertahankan dengan panjang dan hash UTF8 yang tepat.
- **Browser nyata:** desktop GradeA dan HP GradeB menjalankan buat invoice13×29,91, posting, bayar137,03, lalu retur4 senilai119,64. Hasilnya FG32, AR132,16, pendapatan269,19, dan COGS148,14. Respons retur diHP diputus setelah server commit; reload/reconcile dengan UUID dan body yang sama tetap menghasilkan satu retur. Pembatalan pembayaran, retur, lalu penjualan mengembalikan41FG dan semua saldo GL awal.

Empat adjudikasi tambahan menjelaskan kesalahan pembanding auditor: urutan input yang dikembalikan, akun WIP untuk accrual attendance sesuai CP3, serta dua perjalanan browser dengan akun baru bersaldo nol setelah pembatalan. Browser tidak diulang: seluruh aksi sudah berjalan dan fakta akhir tersimpan lengkap. Perbandingan mencakup semua ID akun dengan saldo awal nol bagi akun baru; kontrol tambahan0,01 pada akun lama maupun baru terdeteksi. Status mentah INCOMPLETE tetap disimpan dan tidak diganti diam-diam.

Bukti per kasus, percobaan awal, pemulihan, dan tautan run ada di [CONTINUATION_RESULTS.md](CONTINUATION_RESULTS.md). Batas yang masih tersisa—antara lain tepat180hari PL5, pemilihan otomatis carry paling awal, pabrik tanpa produk, seluruh kategori perubahan PR44, serta semua kombinasi UI—tetap terlihat di COVERAGE_50.md. Kekurangan cakupan audit tidak dijadikan tugas memperbaiki produk.
"""
path=p/'REPORT.md';s=path.read_text();s=s.split('\n## Kelanjutan independen yang selesai')[0];s=s.replace('44 ID kasus mandiri menghasilkan 39 PASS mentah, 1 adjudikasi PASS','Pada laporan awal,44 ID kasus mandiri menghasilkan39 PASS mentah,1adjudikasiPASS');path.write_text(s+paragraph)
path=p/'WRITER_HANDOFF.md';s=path.read_text();s=s.split('\n## Tambahan setelah kelanjutan mandiri')[0]
s+="""
## Tambahan setelah kelanjutan mandiri

23 kasus tambahan sudah dituntaskan pada produk yang sama; tidak ada temuan produk baru yang terkonfirmasi dari kelanjutan ini. Lihat CONTINUATION_RESULTS.md dan REPORT.md untuk bukti per kasus. F01–F05 tetap berlaku. Kontrol tambahan yang lulus tidak membuktikan temuan lama sudah diperbaiki.

Writer tidak perlu memperbaiki urutan input yang dikembalikan allocator, akun WIP attendance, akun bersaldo nol setelah pembatalan, atau penolakan akibat setup aktor dan mode QC auditor. Kesalahan tersebut telah dipisahkan, diuji atau direkonsiliasi terhadap fakta runtime dan kontrak, dengan first failure tetap tersimpan. Kode produk tidak diubah.

Bukti positif tambahan untuk memilih regresi revisi: diskon invoice besar; extra jasa per ukuran; invoice bahan datang setelah jual/retur; kredit retur supplier lintas invoice; koreksi setelah tutup buku; payroll pekerja bernama sama; benturan QC, worker, publikasi laporan, dan carry; pencabutan izin pada11endpoint; batas PL5; PL8 setelah grup dibuka kembali; netting, jadwal, dan prioritas; serta perjalanan browser GradeA/B dengan respons hilang dan pembatalan lengkap. Asal oracle mandiri tetap dipisahkan dari1.256eksekusi suite writer.

Saat kandidat revisi diserahkan, retest F01–F05 dan bagian yang mungkin terdampak perubahan. Tidak perlu mengulang seluruh kasus yang aman tanpa alasan. PR44 tetap memerlukan penerimaan auditor bebas konflik. `production_go:false`.
"""
path.write_text(s)
print(json.dumps(dict(documents=4,case_count=all_results['case_count'],counts=all_results['counts'],roster_run=runs['AS20C-18-ROSTER'],browser_runs=[runs['AS20C-47-WRITE-DESKTOP'],runs['AS20C-47-WRITE-MOBILE']])))
