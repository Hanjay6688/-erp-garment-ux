"""Keep guide IDs and statements intact; explicit dispositions, not test-count voting."""
from pathlib import Path
import collections, hashlib, json, re

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'audit/astra_cp17'
guide=ROOT/'docs/AUDIT_PANDUAN_PRO_MAX.md'
text=guide.read_text()
clauses=re.findall(r'^- \*\*(INV-[A-Z]+\d+)\*\* (.+)$',text,re.M)
assert len(clauses)==len({k for k,v in clauses})
cross=json.loads((OUT/'REQUIREMENT_CROSSWALK.json').read_text())
index=json.loads((OUT/'CASE_EVIDENCE_INDEX.json').read_text())
families={
 'U':('finance payroll procurement sales units','Jurnal/angka SKN22 dan native transaction; FIN01/FIN02 tidak boleh disembunyikan oleh balance=0.'),
 'S':('procurement supply conversion accessory opening','Material/WIP/FG, transfer, opening dan conversion; STK01 adalah pengecualian historis yang nyata.'),
 'H':('payroll recost_close laundry conversion sales','Komposisi biaya/recost ditelusuri; HPP01 membuat basis aktif stale dan dampak laporan hilir belum diukur.'),
 'P':('finance payroll sales procurement','Settlement/credit/refund/aging pada native documents; kapasitas bertanggal FIN01/FIN02 bermasalah.'),
 'T':('recost_close ownership_restore identity_policy','WIB, close/current-clock, filed/original. D01 dan disposisi tanggal lama tetap berlaku.'),
 'L':('finance analysis staged auth_recovery','Report/source/immutable publication/permissions; detector nol bukan bukti semua angka benar.'),
 'R':('schedule models supply material_capacity ai','Kernel, native capture, allocator dan command mempunyai kelas bukti berbeda. Konflik PR44 tetap diungkap.'),
 'K':('procurement sales recost_close ownership_restore','Native correction dan lineage; SG-01/SG-02 dan STK01 mencegah klaim seluruh koreksi selesai.'),
 'C':('auth_recovery accessory_race laundry_race staged','UUID, version, true races, transport loss dan restoration per kasus; Q02/Q12/Q15 membatasi klaim universal.'),
 'A':('auth_recovery ownership_restore ui','Current role/Auth, artifact/security gates, owners/ACLs dan advisor; source grant saja bukan enforcement.'),
 'UI':('ui units auth_recovery','Browser native dan shell/DOM dibedakan; perangkat fisik owner tidak diperiksa.'),
 'POL':('identity_policy payroll units laundry','Keputusan owner tidak dibuat oleh auditor; unknown/pending dan superseded oracle tetap terlihat.'),
 'M':('opening ownership_restore','Synthetic opening, P21 dan CP1 bukan real cutover shadow run atau CP2 historical restore.'),
 'N':('attention','Reminder lokal/test transport; pengiriman nyata CP7C tetap HOLD.'),
 'D':('finance ownership_restore recost_close','135 detector diam pada FIN07/CLAIM02/POOL03; belum setiap detector mempunyai injeksi +1/rollback mandiri.')}

# PASS is bounded to reviewed native cases, not a theorem for untested inputs.
passed=set('''INV-U01 INV-U02 INV-U05 INV-U08
INV-S03 INV-S04 INV-S05 INV-S06 INV-S07 INV-H04 INV-H06
INV-P02 INV-P03 INV-T01 INV-T02 INV-T03
INV-L02 INV-L03 INV-L05 INV-L06 INV-L07
INV-R02 INV-R03 INV-R05 INV-R06 INV-R07 INV-R08 INV-R09
INV-K03 INV-K05 INV-C01 INV-C03 INV-C04 INV-C05
INV-A01 INV-A02 INV-A03 INV-A04 INV-A05
INV-UI02 INV-UI03 INV-POL01 INV-POL04 INV-POL05 INV-M02 INV-N01 INV-N02'''.split())
failed={
 'INV-S02':'FAIL: STK01; public CURRENT_RESTATED prefix−10 setelah reopen/re-POST tanggal lama, current0.',
 'INV-P01':'FAIL: FIN01 dan FIN02; utang cutoff menjadi negatif sebelum sumber akrual/klaim tersedia.',
 'INV-L01':'FAIL: representasi historis STK01 dan tanggal kewajiban FIN01/FIN02 tidak cocok dengan kisah bisnis cutoff.',
 'INV-K06':'FAIL: STK01; prefix publik menghitung issue lama dan pengganti sebelum inverse hari ini.'}
gaps={
 'INV-U03':'INCOMPLETE: inverse nominal diuji pada banyak jalur; R1-04/R3-11 current-clock cancellation belum mempunyai saksi lengkap. Jangan memaksakan restatement yang bertentangan D01.',
 'INV-U04':'INCOMPLETE: SKN22 control-account reconciliation cocok, tetapi seluruh dimensi akun/dokumen belum disertifikasi; saldo negatif FIN01/FIN02 bisa tetap balance.',
 'INV-U06':'INCOMPLETE: cents/large-number controls ada; preview CP3 numeric lama belum dibuktikan aman pada seluruh konsumennya, R1-10.',
 'INV-U07':'INCOMPLETE: overpay nominal/refund/advance diuji; chronological capacity FIN01/FIN02 perlu diperbaiki.',
 'INV-S01':'INCOMPLETE: banyak stock reconciliation PASS; source return SG-02 dan kartu historis STK01 membatasi sertifikasi keseluruhan.',
 'INV-H01':'INCOMPLETE: nilai SKN22 cocok; pengaruh HPP01 pada nilai WIP/FG/COGS belum diukur.',
 'INV-H02':'INCOMPLETE: conservation pool dua periode2000/2000 PASS; basis ACTIVE stale HPP01 serta return/rewash SG-02/03 belum tertutup.',
 'INV-H03':'INCOMPLETE: AY/AZ dan D01 current controls ada; tidak memakai itu untuk menutup STK01 atau seluruh pembalikan yang berbeda clock.',
 'INV-H05':'INCOMPLETE: SKN22 dan recost posisi downstream PASS; HPP01 downstream sesudah policy baru belum diukur.',
 'INV-T04':'INCOMPLETE: archived/current snapshots diuji; qty-only backdate R4-03 dan semua sumber yang terlambat diketahui belum tertutup.',
 'INV-L04':'INCOMPLETE: FIN07/FIN02 report tetap BLOCKED oleh8seed lama; tidak ada false READY yang dibuktikan, tetapi bukan bukti semua incomplete basis selalu tertangkap.',
 'INV-R01':'INCOMPLETE: truthful unknown/stale/cap tested; diterimanya batas semantic-corruption AS20-39 tetap dicatat, bukan setiap stale input terdeteksi.',
 'INV-R04':'INCOMPLETE untuk acceptance independen Astra atas optimisasi yang pernah ditulis sendiri; regression PASS dan peer acceptance Fable terdahulu dibawa terpisah.',
 'INV-K01':'INCOMPLETE: posted immutability/refusal terbukti; koreksi pickup SG-01 belum mempunyai alur selesai.',
 'INV-K02':'INCOMPLETE: koreksi tested mengikuti D01, tetapi tidak mengklaim seluruh business reversal/context sudah selesai; STK01 menunjukkan ketidakselarasan public projection.',
 'INV-K04':'INCOMPLETE: source inventory/current command contexts reviewed; belum semantic inspection setiap direct native-column writer.',
 'INV-K07':'INCOMPLETE: append-only negative controls ada; tidak ada bukti savepoint corruption untuk setiap tabel fakta/buku; DELETE bs_resolutions R3-05 belum diputuskan sebagai projection vs contracted history.',
 'INV-C02':'INCOMPLETE: version/token refusal tested; HPP01 membuktikan perubahan eligibility dapat meninggalkan basis ACTIVE stale.',
 'INV-C06':'INCOMPLETE sebagai pernyataan universal: strict cases memuat boundary/session gates; Q02 committed fixtures dan Q15 whole-program clones memakai bukti pemulihan berbeda, tidak disamakan.',
 'INV-UI01':'INCOMPLETE: server/browser reread pada kasus terpilih; belum seluruh saksi FIN/RWK/STK/HPP baru dijalankan melalui layar pengguna.',
 'INV-UI04':'INCOMPLETE: desktop/HP/tablet emulation tersedia; perangkat fisik owner dan seluruh layar belum disertifikasi.',
 'INV-POL02':'INCOMPLETE: unknown-policy refusal diuji, tetapi policy eligibility HPP01 dan preview exclusion R1-07 belum tertutup menyeluruh.',
 'INV-POL03':'INCOMPLETE: source/ownership inventory tersedia; setiap implementasi aturan belum diperiksa semantik baris demi baris.',
 'INV-M01':'INCOMPLETE: fixture opening cocok; dokumen cutover pabrik nyata satu periode belum tersedia/diuji.',
 'INV-M03':'INCOMPLETE: belum real cutover; 135zero pada fixture tidak membuktikan seluruh kesalahan tertangkap.',
 'INV-M04':'INCOMPLETE: G01/pinned baseline/FULL/P21 dibuktikan; tidak menghubungi hosted untuk preflight mutakhir dan tidak membuktikan restore CP2 lama.',
 'INV-M05':'INCOMPLETE untuk seluruh admission clauses; P21 refusal/lifecycle dan cleanup diuji dengan batas yang tertulis di laporan pertama.',
 'INV-D01':'INCOMPLETE: belum setiap detector memiliki control0→+1→0; jangan menganggap append-only refusal sebagai bukti kepekaan detector.',
 'INV-D02':'INCOMPLETE: tidak ada audit ulang positive/negative setiap detector; alarm lama tidak dihapus atau dinonaktifkan.',
 'INV-D03':'INCOMPLETE: detector outputs dan beberapa effective sources diperiksa; belum semantic mapping seluruh135definisi ke setiap writer current.',
 'INV-D04':'INCOMPLETE: FIN07/FIN02/HPP01 menyimpan135before/after, tidak seluruh135untuk setiap kasus seluruh modul; RWK01/STK01 tidak mengklaimnya.'}
assert not passed&set(failed) and not passed&set(gaps)
assert {i for i,_ in clauses}==passed|set(failed)|set(gaps),({i for i,_ in clauses}-(passed|set(failed)|set(gaps)),(passed|set(failed)|set(gaps))-{i for i,_ in clauses})
rows=[]
for id,statement in clauses:
 family=re.match(r'INV-([A-Z]+)',id)[1];keys,note=families[family];keys=keys.split()
 ev=[k for k,v in index.items() if any(re.search(cross['profiles'][p]['case_pattern'],v['case_id'],re.I)for p in keys)]
 disposition=failed.get(id) or gaps.get(id) or 'PASS pada kasus sah/refusal yang dirujuk; bukan seluruh kombinasi tak teruji.'
 rows.append(dict(id=id,statement=statement,status='FAIL'if id in failed else'INCOMPLETE'if id in gaps else'PASS',disposition=disposition,profiles=keys,evidence=ev,boundary=note))
result=dict(guide=str(guide.relative_to(ROOT)),guide_sha256=hashlib.sha256(guide.read_bytes()).hexdigest(),candidate='0b7049d9203bac52b47a4c89f3e0d75646067a8f',counts=dict(collections.Counter(r['status']for r in rows)),rows=rows,production_go=False)
(OUT/'INVARIANT_CROSSWALK_CONTINUATION.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
md=['# Matriks invariant Pro Max — hasil lanjutan CP1–CP7','',
 'ID dan kalimat aturan dipertahankan persis dari panduan kandidat. Status **PASS dibatasi pada jalur yang diuji dan dirujuk**, bukan sertifikat semua input atau setiap function body. Requirement, case status mentah, dan invariant bukan jumlah yang dapat dijumlahkan. Empat klausul FAIL tidak berarti hanya empat akar cacat: lima temuan runtime dan tiga kesenjangan statis dijelaskan terpisah.','',
 'Seluruh bukti EV dapat dibuka melalui CASE_EVIDENCE_INDEX.json; JSON crosswalk menyimpan daftar lengkap. Pemetaan profil membantu navigasi, tidak otomatis mengubah status suatu kasus menjadi status invariant.','',
 '| ID | Aturan | Status | Bukti dan batas |','|---|---|---|---|']
for r in rows:
 content=r['disposition']+' '+r['boundary']+' Profil: '+', '.join(r['profiles'])+'. EV: '+', '.join(r['evidence'][:3])+'.'
 md.append('| '+' | '.join(x.replace('|','/').replace('\n',' ')for x in(r['id'],r['statement'],r['status'],content))+' |')
md+=['','Jumlah: '+json.dumps(result['counts'])+'. Sertifikasi audit/fitur menyeluruh tetap ditahan. CP2 restore dan gerbang produksi bukan diganti dengan PASS invariant yang lain.','']
(OUT/'INVARIANT_MATRIX_CONTINUATION.md').write_text('\n'.join(md))
print(json.dumps(dict(invariants=len(rows),counts=result['counts'])))
