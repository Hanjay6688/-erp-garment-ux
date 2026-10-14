# Addendum Astra — pemeriksaan silang final CP1–CP7

**Pemeriksaan lanjutan selesai. Penerimaan penuh kandidat tetap TAHAN.** Tidak ada kandidat produk revisi dari penulis pada pemeriksaan akhir: cabang penulis masih `00b0eb24b2f014d102f0082111d13ee3be429cf2`, produk beku `0b7049d9203bac52b47a4c89f3e0d75646067a8f`, tree `ce6aed0a0af920e8aa80248f3cabcd293688df18`.

Laporan pertama terkunci pada `f70361d551d9dbc9931e330216901a8b702feab5`; laporan lanjutan pada `d5dcf4e3b8c660c3e80c2c47ee5fb5cd764025c4`. Addendum ini menambahkan bukti baru, tidak menimpa laporan, ledger, Original atau hasil merah sebelumnya. Snapshot Fable baru `681dd7a965e1e96267cd64d927faf44f03a92848` mencakup laporan final dan addenda CP1/CP2/akses.

## Apa yang selesai

- Laporan final Fable, ketiga addendum, keputusan D14-1 yang dilaporkan Fable, source verifier CP2, source kasus akses dan dua Original ZIP beserta log lengkap sudah dibaca. Semua 12 temuan Fable memiliki disposisi Astra; penilaian tidak disalin otomatis.
- CP1: hasil hosted Fable cocok 16/16 kategori dengan baseline G-01 repo; query hash cocok. Ini bukti Fable yang dibaca Astra, melengkapi rekonstruksi independen Astra sebelumnya.
- CP2: restore PG16 lokal Fable kini diakui sebagai bukti baru. Verifier benar-benar membandingkan data ERP, identitas objek/kolom, flags RLS dan ledger. Namun field image adalah konstanta, fingerprint hanya nilai expected dari manifest, dan definisi/owner/ACL lengkap belum dibandingkan. Layanan Supabase asli serta round-trip Storage belum diuji. Tidak ada klaim Astra mengambil arsip/kunci atau menjalankan restore itu.
- Akses: **dua kasus baru Astra PASS pada upaya pertama**. Katalog mengonfirmasi grant yang dilaporkan Fable. Enam panggilan close/reopen oleh role kustom finance, owner nonaktif dan subject tak terdaftar ditolak; owner aktif benar-benar bisa reopen sebagai kontrol. Semua perubahan dikembalikan, exact runtime dan cleanup lulus. Ini SQL dengan session authorization nyata, bukan HTTP/hosted.
- Indeks kebutuhan C6+saldo awal lengkap 97 butir:39 ACC + 36 LAU + 22 ALL.40 baris punya tautan kasus bernama;57 tautan profil review. Seluruhnya punya expected/disposisi/alamat bukti; tidak dinaikkan menjadi97 klaim lulus semua klausul.
- Kesalahan administrasi Astra sendiri dicatat terbuka: manifest salah nama pada dua artifact final-gaps, kalimat handoff cutting tertinggal, dan label oracle generik pada envelope runner baru. Pin sebelum eksekusi, Original dan hasil tetap dipertahankan.

## Vonis per tahap setelah bukti tambahan

|Tahap|Disposisi yang berlaku|
|---|---|
|CP1 baseline/history|TERVERIFIKASI DENGAN BATAS HISTORIS. Rekonstruksi Astra dan hasil hosted Fable dipisah; perbedaan ledger fixture yang diketahui tetap dijelaskan.|
|CP2 backup historis|BUKTI RESTORE LOKAL AUDITOR LAIN DITERIMA DENGAN BATAS; PENERIMAAN PENUH BELUM. Kekurangan engine/platform, definisi+owner+ACL dan Storage dijabarkan.|
|CP3/3.5 absensi–HPP–payroll|TAHAN karena FIN01/HPP01. Dugaan payroll duplicate attendance ditolak pada rute yang diuji; dua biaya nyata dalam pool overlap tidak otomatis duplikasi.|
|CP4/4.5 akses/operasi|Bukti runtime tetap berlaku dengan batas FABLE-012. Dua entry point native menolak non-owner; konfigurasi hosted dan seluruh fungsi lain belum disertifikasi oleh probe ini.|
|CP5 produksi/rework/koreksi|TAHAN karena RWK01/STK01 serta gap alur SG01/SG02; SG03 tetap gap kontrak/rute. Program legacy 1 PASS / 3 INCOMPLETE tidak diubah.|
|CP6 penyelesaian/rilis/integrasi|TAHAN untuk penerimaan menyeluruh karena FIN02 dan sambungan HPP/payroll; indeks 97 butir membantu navigasi tetapi tidak menghapus gap. Catatan AC/T3 adalah qualification/dokumentasi, bukan perintah merusak sejarah migrasi.|
|CP7 UI sampai laporan|Gate fase yang sudah lulus tetap dicatat, tetapi penerimaan sistem menyeluruh TAHAN karena lima akar runtime menembus alur CP7. CP7C tetap HOLD.|

**Lima akar runtime belum berubah:** FIN01 tanggal pembayaran payroll, RWK01 hak upah rework sesudah SCRAP, STK01 histori stok sesudah reopen/re-POST, FIN02 tanggal settlement klaim laundry, HPP01 pool aktif stale sesudah policy eligibility baru. Detail dan bukti penerimaan perbaikan berada pada laporan/handoff utama; addendum ini tidak menggandakan akar yang sama menjadi temuan baru.

## Bukti eksekusi baru dan hitungan

Run **38593568808**, job **115954406369**, control **aa25e5ee06e58e218e8318bb0cf8d10e8eeff382**, attempt 1. Dua caseID baru: `CP17-ASTRA-RBAC-01-CATALOG`, `CP17-ASTRA-RBAC-02-ROLE-BOUNDARY`. Hasil mentah 2 PASS, 0 missing, 0 retry. Enam penolakan dan satu kontrol owner adalah langkah dalam satu kasus, bukan tujuh kasus tambahan.

Original artifact 11908777291 SHA256 `fbd29da1bc65c6f2d0c08e530186130eadc3ac361fb28f0cacb301c1636c43ed`; arsip utuh dan log job dapat dirakit dari `ASTRA_RUNTIME_ARCHIVES.json`. Manifest artifact cocok dengan manifest yang sudah dikomit sebelum run. Exact FULL sebelum/sesudah, boundary/public schema restore, per-case nol session/advisory leak, CP6 restoration, advisor gate, primary unchanged dan cleanup selesai. Source/date/actor boundaries lengkap di `RBAC_OBSERVATION.json`.

Gabungan eksekusi kasus tercatat menjadi **2918+2=2920**; ini bukan 2920 PASS. Ledger lama yang mempunyai counterexample, FAIL dan INCOMPLETE tetap terkunci; tidak ditulis ulang. Dua run Fable dibaca sebagai bukti auditor lain dan tidak ditambahkan ke hitungan eksekusi Astra. Tes unit/browser lama tidak diklaim dijalankan ulang pada putaran ini.

## Batas dan tindakan yang masih diperlukan

- Penulis memperbaiki lima akar runtime dan melengkapi alur yang belum tersedia, lalu menyediakan kandidat/hash/diff dan bukti sebelum–sesudah. Audit tidak mengubah kode produk sendiri.
- CP2 memerlukan bukti pemulihan yang melengkapi batas tersebut dari lingkungan pemegang arsip. A2 Fable juga melaporkan sebagian passphrase masuk log sesinya: anggap kunci terpapar dan jangan gunakan ulang untuk backup baru. Astra tidak mengambil atau menerbitkan nilainya.
- FABLE-012 tetap dibatasi fakta katalog dan dua role guard yang diuji. Inventaris expose/grant/caller harus mendahului perubahan hak; tidak ada klaim108 exploit atau bypass HTTP terbukti.
- A2 pembayaran supplier tetap OPEN/non-blocker sesuai D13-10. A6/P11 dan F-OPS-05 yang sudah ditutup tidak dibuka ulang. CP7C/Drive tetap HOLD untuk pekerjaan Astra.

`followup_review_complete:true`, `pending_audit_jobs:0`, `feature_complete:false`, `audit_complete:false`, `production_go:false`. Dua flag terakhir mempertahankan arti gate penerimaan penuh pada paket lama: pekerjaan pemeriksaan ini selesai, penerimaan produk belum terpenuhi.

## Berkas untuk penulis dan pemeriksa

- [HANDOFF_WRITER.md](HANDOFF_WRITER.md): serah-terima terbaru dan urutan tindakan.
- [FABLE_FINAL_DISPOSITIONS.md](FABLE_FINAL_DISPOSITIONS.md): seluruh 12 temuan Fable.
- [CP1_CP2_CROSSCHECK.md](CP1_CP2_CROSSCHECK.md): penerimaan dan batas bukti historis.
- [RBAC_CROSSCHECK.md](RBAC_CROSSCHECK.md): sumber, kontrol, hasil dan batas akses.
- [C6_75_ALL22_CROSSWALK.md](C6_75_ALL22_CROSSWALK.md): indeks 97 butir; JSON memuat alamat Original/run/case/status.
- [AUDIT_METADATA_CORRECTIONS.md](AUDIT_METADATA_CORRECTIONS.md): koreksi Q16/Q17; Q18 dijelaskan di RBAC.
- `ADDENDUM_LOCK.json`, `FABLE_SOURCE_MANIFEST.json`, `FABLE_RUNTIME_ARCHIVES.json`, `ASTRA_RUNTIME_ARCHIVES.json`, `OWN_RUN_RECEIPT.json` dan `verify_followup.py`: pin dan pemeriksaan keutuhan. Jalankan `python audit/astra_cp17/followup-681dd7a9/verify_followup.py` dari checkout cabang audit.
