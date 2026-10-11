"""Write the reader-facing audit report from reconciled evidence; never infer GO."""
from pathlib import Path
from datetime import datetime, timezone
import json

P = Path(__file__).resolve().parent
s = json.loads((P / 'evidence/RESULT_SUMMARY.json').read_text())
pending = s['pending_regression_reports']
complete = pending == 0
status = 'SELESAI — HOLD' if complete else f'BERJALAN — {pending} laporan regresi belum direkonsiliasi'
reg = s['writer_regression']
writer_count = reg.get('PASS', 0)
smoke = reg.get('smoke_pass', 0)
generated = datetime.now(timezone.utc).isoformat()
text = f'''# Audit independen CP7 — Astra — d0b9e9c2

**Status: {status}. `production_go:false`.**

## Untuk Bos

Audit ini menguji seluruh cakupan CP7 pada kandidat yang dibekukan.
Temuan baru yang sudah terbukti adalah **ASF-F01, S3 pada alat tes**: pergantian tanggal dapat mengizinkan pengulangan kegagalan yang tidak disebabkan tanggal, lalu hasil utamanya menjadi PASS.
Log gagal pertama tetap tersimpan; ini bukan bukti uang atau stok aplikasi salah.
Kasus mandiri menghasilkan **75 PASS dan satu batas detektor lama**; empat kontrol alat menghasilkan dua PASS dan dua COUNTEREXAMPLE untuk satu temuan tersebut.
Regresi dengan oracle writer yang dijalankan Astra sudah mencatat **{writer_count} eksekusi kasus PASS**, {smoke} smoke PASS, serta dua gladi; hasil lengkap dan jumlah ID unik dipisahkan di berkas pendamping.
Shell mencatat **1.724 tes, 201 berkas, dan enam browser PASS**, ditambah build/security dan dua analisis CodeQL tanpa finding.
Perbaikan lama kapasitas v1/v2, isolasi nama cron, tabrakan receipt backup, finalizer, dan cold-lock K4 sudah diuji ulang dan tidak dibebankan kembali kepada writer.
Penerimaan optimasi PR44 tetap perlu auditor yang tidak menulisnya, dan pemasangan tetap memerlukan izin owner pada tahap yang sudah disepakati.

## Identitas dan cakupan

| Atribut | Nilai |
|---|---|
| Kandidat produk | `d0b9e9c2e41a9f0f3a138346887434fd7d3c14f0` |
| Tree produk | `4bd5e1acf55f0b441d9c8f67949ee5b070eb9c41` |
| Acuan dokumen | `5548ff18dedf3a2b77e50e5d2afc0e35fac56e26` |
| Selisih produk → acuan dokumen | Sepuluh berkas, semuanya di `docs/`, diperiksa sendiri |
| Lingkup | CP7 beku `9d57b7f5` beserta seluruh kelanjutan sampai kandidat |
| Di luar kandidat | PR45 UI/demo; audit penuh CP1–CP7 tahap berikutnya; pemasangan hosted |
| Lingkungan | GitHub Actions Ubuntu 24.04, Supabase CLI 2.116.0, image PostgreSQL 17.6.1.165, Python 3.12, Node 22 (Shell teramati 22.23.3), Chromium dari Playwright yang dikunci package-lock kandidat |
| Isolasi | Database sekali pakai di loopback runner; produksi dan database hosted tidak diakses/dimutasi |
| Asal oracle mandiri | Kontrak dan keputusan owner; nilai uang dihitung sendiri dengan Decimal, konservasi, inverse, dan kontrol negatif |
| Asal fixture | Campuran fixture/input Astra dan setup/transport writer yang tidak diubah; rinci per kasus |
| Konflik kepentingan | Astra pernah menulis PR44 timeline; tidak memberikan penerimaan independen untuk bagian itu |
| Pembaruan laporan | {generated} |

`SOURCE_RECEIPT.json`, `evidence/SOURCE_VERIFICATION.json`, dan `evidence/EXECUTION_IDENTITY_CHECK.json` mengikat hasil ke kandidat.
Workflow audit berjalan dari cabang kontrol tersendiri tetapi checkout produk selalu SHA/tree di atas.
Hash semua Original ZIP dibandingkan dengan digest GitHub. Tidak ada perbaikan kode produk dalam audit ini.

## Hasil mandiri, terpisah dari crosscheck

**76 ID produk mandiri**, 79 eksekusi karena tiga ID juga dipakai sebagai kontrol lintas suite: 75 ID PASS dan satu COUNTEREXAMPLE lama.
Jumlah ID bukan jumlah oracle yang sepenuhnya berbeda. Rinciannya ada di [OWN_RESULTS.md](OWN_RESULTS.md).

- Alur sendiri: penerimaan 73 PCS → produksi 41 PCS → jual 13 → bayar 137,03 → retur empat. Hasil: bahan 32 PCS/nilai 395,84; FG 32 PCS/nilai 526,72; penjualan bersih 269,19; HPP terjual 148,14; piutang 132,16; hak payroll 82,82. Jurnal dan laporan cocok dengan hitungan tersendiri.
- Dua alur tulis browser nyata: desktop retur Grade A, mobile retur Grade B. Sesudah retur mobile, FG 28 A + 4 B. Respons diputus sesudah commit dan dipulihkan memakai UUID/payload sama; efek tetap satu. Pembalikan pembayaran, retur, dan penjualan mengembalikan posisi yang diperiksa.
- K4 server mengerjakan 5.000 target tanpa halaman terbuka: 26 halaman lengkap, 133 panggilan, identitas sama sesudah reconnect. Waktu panggilan terlama sekitar 3.259 ms termasuk status/commit; ini bukan waktu UI seluruh proses. Target 5.001 ditolak sebelum menghasilkan run.
- Pembersihan hasil 5.000 target: ukuran payload 126.527.094 → 31.102.811 byte; hemat 95.424.283 byte. Semua halaman dan identity hash tetap. Ukuran alokasi relasi dicatat terpisah: DELETE tidak berarti ruang disk langsung kembali ke OS.
- K6 memakai lima grup fisik nyata, 217 PCS potong dan 207 GOOD. Reverse/backdate membuat bukti lama tidak berlaku; dua giliran server memulihkan bukti lima grup. Fault sementara sesudah dua percobaan insert membatalkan seluruh jendela, lalu penjalan mengecilkan jendela dan pulih; produk tidak diubah.
- K7a “Cek sumber”: enam pembandingan predecessor/kandidat pada baseline dan fakta sendiri, batas 0/1/5.000. JSON sama setelah hanya `captured_at` dikecualikan. Fixture perbandingan ini kecil; bukan klaim berisi 5.000 produk.
- Backup terpakai membandingkan 559 tabel, termasuk tabel proof runner. Lima belas malam dump/restore nyata disimulasikan untuk retensi 14; malam gagal tidak memangkas hasil terdahulu. Empat jadwal pg_cron diuji nyata hanya dalam salinan.
- Smoke UI mencakup 48 rute pada desktop dan 48 pada emulasi HP, ditambah izin keuangan OWNER/worker/anon. Ini tidak berarti semua tombol pada semua peran atau HP fisik sudah diuji.

**Temuan mandiri baru: ASF-F01 (S3, OPEN_TOOLING).** Modul asli `scripts/cp6_auditor_business_day.py` dijalankan di CI dengan hasil kasus sintetis: expected 10.000 sen, observed 10.001 sen, kegagalan dinyatakan tidak terkait tanggal. Ketika disertai flag pergantian hari, helper tetap mengulang dan mengembalikan PASS sintetis upaya kedua sebagai hasil utama. FAIL maupun COUNTEREXAMPLE menunjukkan masalah yang sama. Dua kontrol positif/negatif lulus. First attempt masih ada di hasil bersarang dan callback log.

Reproduksi, sumber, dampak, dan penutupnya ada di [WRITER_HANDOFF.md](WRITER_HANDOFF.md) serta [FINDINGS.json](FINDINGS.json).
Run kontrol: [38159947839](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38159947839).
Ini bukti runtime alat Python asli, bukan transaksi ERP dan bukan klaim keempat mode runtime masing-masing sudah diinjeksi kegagalan tersebut.

## Crosscheck dan regresi yang dijalankan auditor

[REGRESSION_RESULTS.md](REGRESSION_RESULTS.md) memisahkan oracle writer, jumlah eksekusi, smoke, dan fase gladi.
Ada 44 job: 42 laporan kasus dan dua gladi. Status saat penulisan: {reg['reports']}/42 laporan kasus direkonsiliasi; {pending} belum masuk hitungan.
Paket kasusnya dijalankan sendiri pada kandidat yang sama; green dari run writer tidak menjadi bukti penerimaan.

- Assertion Python yang berubah diperiksa dengan AST. Dua penghapusan ekspresi adalah penggantian anggaran 18→22 setelah empat kasus baru dan penggantian nama cron menjadi spesifik database; tidak ditemukan pelonggaran pada dua ekspresi itu. Ini bukan jaminan semua oracle sempurna, sebagaimana ASF-F01 menunjukkan.
- Log lama yang diperpanjang dicocokkan ke CI asli: 22/22 baris kasus sama. Dua log mobile yang berhenti dicocokkan ke CI: masing-masing 29/29 cuplikan sama dengan sumber. Tidak ditemukan pengubahan bukti lama dalam perbandingan ini.
- Dua gladi P21 lulus: enam fase dasar dan sembilan fase penuh. Gladi penuh mencakup COMMITTED use, penolakan rollback sesudah dipakai, restore backup terpakai, dan restore backup pra-pasang. `pg_restore` exit 1 berasal dari 19 error pg_cron yang tercatat dan dijelaskan pada database tujuan terpisah; tidak ada error tak terjelaskan. Data 559 tabel sama; perbedaan serialisasi catalog/ACL diklasifikasikan, bukan disebut byte-identik.
- Pengukuran browser skala memakai oracle writer yang dijalankan Astra: 5.000 target bertahap selesai sekitar 49,6–66,8 detik untuk jendela riwayat 1/30/100 hari. Buka DONE paling lambat 937 ms dan pindah halaman paling lambat 575 ms pada runner ini. Jalur biasa/keuangan bisa melewati sasaran tiga detik atau ditolak pada batas delapan detik. Pengecualian latar owner dan batas produk dicatat; tidak ada klaim SLA produksi.
- Shell conditional assembler benchmark tidak berjalan karena kondisi cabang; tidak diberi kredit. CodeQL tanpa finding tidak menggantikan uji uang, akses, atau logika bisnis.

## Putusan per area

Matriks bukti dan batas tiap area ada di [COVERAGE.md](COVERAGE.md). `LULUS` berarti kasus yang disebut terbukti; bukan janji nol bug di semua kombinasi.
{'Matriks putusan akhir menunggu sisa regresi. Tidak ada status sementara yang dipakai sebagai izin GO.' if not complete else 'Matriks area telah direkonsiliasi dengan seluruh hasil run. Area integritas uji GAGAL pada ASF-F01; penerimaan independen PR44 tidak diberikan karena konflik kepentingan.'}

Perbaikan temuan lama dan pembatasan bukti dijelaskan di [RETEST_AND_LIMITS.md](RETEST_AND_LIMITS.md).
Counterexample `AS20-39_VALIDATION_NEGATIVE` tetap tercatat: auditor sengaja menonaktifkan trigger immutable pada salinan, kemudian empat mutasi semantik tidak tertangkap detektor cleanup. Mutasi biasa ditolak `CP7_RUN_IMMUTABLE`; batas cakupan detektor ini sudah didokumentasikan sebelum putaran. Ini tidak dibuka ulang sebagai bug aplikasi baru.

## Kesalahan alat auditor yang sudah dipulihkan

1. UI awal berhenti sebelum kasus pertama karena `UI_INVENTORY.json` tidak ikut tersalin. Inventaris asli dikembalikan byte-identik; satu run pemulihan menjalankan tiga kasus PASS. Log awal tetap INCOMPLETE.
2. Satu kasus FULL_FLOW terdaftar tetapi terlewat filter runner. Rekonsiliasi ID menemukan kekosongannya; kasus asli dijalankan pertama kali pada kandidat ini di run 38161351529 dan PASS.
3. Metadata umum beberapa workflow mandiri masih memakai label template `WRITER_UNCHANGED`. Manifest sebelum eksekusi dan metadata per kasus menunjukkan oracle Astra. Raw metadata disimpan apa adanya; kesalahan label ini diungkapkan, bukan dipakai untuk mengklaim oracle lain.

## Syarat penutupan dan pemasangan

1. Selesaikan ASF-F01 atau penerimaan risiko tertulis sesuai gerbang panduan; rekomendasi auditor adalah memperbaiki helper dan menguji kembali kontrol yang konkret. Jangan mengubah assertion bisnis atau menimpa log gagal lama.
2. Satukan penerimaan area PR44 dari auditor yang tidak menulisnya. Bukti Sol putaran sebelumnya boleh menjadi crosscheck, bukan otomatis penerimaan putaran ini.
3. Pertahankan urutan owner: audit penuh CP1–CP7 → CP7.5 → CP7C → CP8/GO owner. Laporan ini tidak memberi izin memasang jadwal/backup atau deploy.
4. Sebelum pemasangan yang diizinkan owner, cocokkan konfigurasi nyata, baseline tujuan, identitas empat jadwal per database, peran scheduler, batas delapan detik, retensi, serta tujuan backup. Buktikan restore dari backup operasional pada salinan. Pengaturan nyata yang belum diisi tetap belum siap; keputusan owner lama tidak dibuka ulang.

Batas tersisa: HP fisik/Safari dan tab HP yang benar-benar ditutup, hosted install, tujuan backup operasional, provider AI/WA nyata, serta seluruh audit CP1–CP7 tidak diklaim oleh bukti ini. Pengingat memakai sink lokal dan tidak mengirim pesan.

## Reproduksi dan berkas bukti

`RUN_INDEX.json` berisi delapan run auditor dan commit kontrolnya; workflow `audit-astra-full-*.yml` mencatat perintah/pin lingkungan. Jalankan skrip mandiri pada lingkungan CI disposable yang sama, bukan database hosted.

- [OWN_RESULTS.md](OWN_RESULTS.md): 76 ID mandiri dan artifact ID.
- [REGRESSION_RESULTS.md](REGRESSION_RESULTS.md): hasil regresi oracle writer dan gladi.
- [evidence/RECONCILIATION.json](evidence/RECONCILIATION.json): hitungan per kelompok/ID, restore gate, first attempt dan flag tanggal.
- [evidence/SAVED_ARCHIVES.json](evidence/SAVED_ARCHIVES.json): Original ZIP tersimpan beserta SHA-256; isi mentah tidak diubah.
- [evidence/VISUAL_REVIEW.json](evidence/VISUAL_REVIEW.json): screenshot asli yang diperiksa.

`python audit/astra_full/reconcile_evidence.py` menghitung ulang hasil lokal yang telah diunduh;
`python audit/astra_full/summarize_evidence.py` memverifikasi identitas/anggaran dan membuat tabel.
Keduanya meringkas bukti CI, bukan pengganti menjalankan kasus.
'''
(P / 'REPORT.md').write_text(text)
print(json.dumps({'report_status': status, 'bytes': len(text.encode()), 'production_go': False}))
