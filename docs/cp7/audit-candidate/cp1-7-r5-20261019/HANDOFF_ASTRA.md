# Uji ulang r5 CP1–CP7 — untuk Astra

Owner menyalin **seluruh isi kotak di bawah** ke sesi Astra. Kandidatnya sama untuk Fable, Astra dan Sol.
Rincian: `README.md` di folder ini.

````text
Kamu Astra, auditor independen. Ini UJI ULANG PUTARAN r5 untuk ERP Garment, repo Hanjay6688/-erp-garment-ux, cabang
writer claude/new-session-deapao. Kamu sudah menguji ulang kandidat r4 663f6fae (audit/astra_cp17_r4/, cabang audit/astra-cp1-7-r4-663f6fae-20261019,
kunci 40238e36; vonis LULUS_UJI_ULANG_DENGAN_BATAS_BUKTI: ASTRA-R3-01, sisa ASTRA-R2-01, ASTRA-R3-02, ASTRA-R3-03
ditutup; tidak ada temuan produk baru; 565 kasus PASS). Penulis memperbaiki temuan putaran r4 di r5 dan mengerjakan kecepatan analisis
langsung dengan angka keuangan atas keputusan owner D17-2. Fable, Astra dan Sol menguji ulang kandidat yang sama secara
terpisah.
KANDIDAT
- Commit 17fa25075ba77f0853c3c16f504288ace03eec35, tree 65f778479093d869a3354c0b9f19b4d9a541d98a. Basis r4: 663f6faefcbb9c70f0f99bbc7e78164e03521329
  (tree 023f3554432f80f994439f5d0b8cc164846a2041). Commit sesudah kandidat di cabang writer hanya dokumen; buktikan:
  git diff --name-only 17fa25075ba77f0853c3c16f504288ace03eec35 origin/claude/new-session-deapao. Catat tree produk sebelum dan sesudah auditmu (Pro Max §2.8).
- src/ dan supabase/ tidak berubah sejak 663f6fae (git diff --name-only 663f6faefcbb9c70f0f99bbc7e78164e03521329 17fa25075ba77f0853c3c16f504288ace03eec35 -- src supabase kosong). Perubahan
  produk hanya di scripts/ (lapisan CP7 dan alat uji) dan satu jalur pemicu di .github/workflows/claude-cp17-fixes.yml:
  git diff --stat 663f6faefcbb9c70f0f99bbc7e78164e03521329 17fa25075ba77f0853c3c16f504288ace03eec35 -- src scripts tests .github.
- Bukti penulis: docs/cp7/audit-candidate/cp1-7-r5-20261019/CI_RECEIPT.json (semua run dan job pada kandidat; ringkasan di
  README.md bagian Kandidat); docs/cp7/cp17/CP17_FIXES.json (345 kasus CP17 dideklarasikan sebelum dijalankan: 165 Native,
  39 race, 27 HTTP Auth nyata, 57 browser, dan 57 kasus browser yang sama di build mode Enteng; workflow "CP7 CP17 Fixes").
  Run, job dan kasus disebut terpisah.
- Paket: docs/cp7/audit-candidate/cp1-7-r5-20261019/ (README.md per akar R5-01..R5-02, CROSS_AUDIT.md audit silang penulis
  atas ketiga laporan r4). Isinya titik awal penulis, bukan bukti lulus.

KEPUTUSAN OWNER BARU (kutipan persis di docs/cp7/OWNER_DECISIONS_20261008.md, D17-2): "Auditor dl ya, inget lu punya tugas
ini di next turn ya" — auditor dulu, lalu penulis mengerjakan kecepatan analisis langsung dengan angka keuangan. Batas 8
detik, pemeriksaan sumber/otoritas/hash/kelengkapan dan keputusan 7 Okt (pekerjaan berat boleh di latar belakang sebagai
pengecualian yang dicatat; target 3 detik tidak ditandai tercapai kalau belum) tetap berlaku. Keputusan yang sudah
disahkan tidak dibuka ulang; uji dengan oracle-mu sendiri.

YANG DIUJI ULANG (temuanmu → klaim penulis; uji dengan kasusmu sendiri, angka dan hasil yang kamu harapkan tidak diganti)
- Tidak ada temuanmu yang terbuka dari r4. r5 tidak mengubah src/ dan supabase/; yang berubah dua delta Native di
  lapisan CP7 (lihat JUGA PERIKSA).

JUGA PERIKSA (bukan temuanmu, dan regresi di sekitarnya)
- SOL-R4-001 (S1, Nota FG_REPAIR yang sah memunculkan dua alarm CRITICAL payroll_work_wrong_contractor) → R5-01:
  erp.run_v263a_payroll_integrity_checks() kini mencari borongan baris FG_REPAIR di erp.fg_unsourced_repair_wages_v1
  (coalesce produksi, rework, upah perbaikan barang jadi); cek lain di fungsi itu tidak berubah. Delta Native yang
  dideklarasikan, dipasang dan dicabut lewat originals F03 seperti delta lain: scripts/cp7_payroll_checks_bundle.py.
- KNOWN-P19-DIRECT-LATENCY (owner D17-2) → R5-02: di sebelas pembaca STABLE (laporan pemilik, run_v268 dan
  pra-cakupannya, run_v267, buku HPP non-PO dan PO, nilai HPP siklus penjualan, akun kredit saldo awal, cek uang muka
  awal, cek kain pocket, buku periode pocket) setiap erp.account_id('<KUNCI>') berkunci tetap menjadi
  (select erp.account_id('<KUNCI>')): dihitung sekali per query, bukan sekali per baris. Pemasangan menolak kecuali ke-17
  kunci adalah pemetaan inti yang terisi (penjaga Native menolak hapus/ganti nama pemetaan inti) dan jumlah panggilan
  per pembaca persis seperti yang dideklarasikan. scripts/cp7_report_accounts_bundle.py; hasil dan yang belum tercapai:
  docs/cp7/p19/P19_R5_02_REPORT_READERS.md (100 target dengan angka keuangan, kualifikasi r4 lawan kualifikasi r5 pada
  runner yang sebanding: server 4,56 → 2,25 detik, browser 4,57–5,92 → 2,89–3,33 detik; 3 detik tidak ditandai tercapai).
- R5-02 mengubah teks pembaca yang dipakai laporan pemilik, kesiapan periode dan cek keuangan. Coba patahkan klaim
  "jawaban sama": pemetaan akun yang diganti ke akun lain sebelum dan sesudah query, pemetaan inti yang dihapus atau
  diganti nama, pembaca yang dipanggil tanpa baris, pembaca yang dipanggil di banyak baris dalam satu query. Kasus
  CP17_R5_02_REPORT_READERS_SAME_ANSWER (pembaca terpasang dan pembaca tanpa perubahan berdampingan) dan
  CP17_R5_02_REPORT_READERS_REVIEWED.
- R5-01: cek lain di erp.run_v263a_payroll_integrity_checks() tetap sama (teks sebelum dan sesudah hanya beda di
  join dan coalesce yang dideklarasikan); Nota REVERSED tetap tidak dihitung.
- Bahwa penjaga lama tidak dilonggarkan: kas per tanggal ekonomi dan buku (D14-3, D15-1), bayar upah tidak mendahului akrual
  (D14-2), lantai cutover (D15-5), kebijakan HPP, delta Native yang dideklarasikan hanya berlaku di dalam perintahnya.

YANG SUDAH DIKETAHUI PENULIS (uji sendiri; jangan dianggap benar atau salah tanpa bukti)
- Lapisan CP7 belum terpasang di Enteng (CP7C ditahan, D13-9a); build Enteng diuji terhadap salinan sekali pakai.
- FABLE-012 tetap ditunda ke CP7C (D14-9). Patch backup Sol disiapkan untuk CP7C, tidak dipasang.
- Analisis langsung: 100 target dengan angka keuangan 2,89–3,33 detik di browser pada runner kualifikasi (dekat, belum
  stabil di bawah 3 detik); 300 target tetap di atas 3 detik (dengan angka keuangan: 1 dan 30 hari selesai sekitar 10
  detik, 100 hari berhenti di batas 8 detik dengan pesan; job latar dengan angka keuangan selesai). Sisa panggilan
  erp.account_id (2.476 pada 100 target) ada di buku HPP per produk: empat per panggilan buku, 588 panggilan buku.

ATURAN
- Tanpa saling intip (Pro Max §2.2, §16.7): jangan membaca laporan, cabang, run, artifact atau komentar auditor lain dari
  putaran ini sampai laporanmu dikunci dengan commit. Laporan yang sudah terkunci sebelum putaran ini (ketiga laporan r4)
  boleh dibaca; audit silang penulis ada di CROSS_AUDIT.md.
- Label asal-bukti per klaim (§2.9). Baca status per kasus dari log atau artifact, bukan warna job (§2.10). Rerun paling
  banyak sekali dan hanya bila job mati sebelum kasus berjalan (§1.9).
- Dispatch workflow writer hanya dengan ref claude/new-session-deapao dan catat head_sha yang terpakai; bila head sudah
  bergeser, buktikan tree produk sama sebelum memakai hasilnya (§1.7, §2.8, §16.1).
- Jangan percaya klaim penulis begitu saja: susun oracle sendiri dari kontrak dan keputusan owner (D14-2..D17-2).
  Pertanyaan yang sudah dijawab owner tidak ditulis ulang sebagai terbuka (§2.12).
- Tidak boleh dimutasi: main, deployment Cloudflare, Supabase hosted Enteng (siimvrusnzxexizpyoib), legacy ERP-Garment
  (vlxdhpkjeevubjxexnfo, read-only), production. Jangan meminta password, token atau kunci di chat.
- Panduan: docs/AUDIT_PANDUAN_PRO_MAX.md (SHA-256 5752e96df751de5ebe4b86d3f572cffa1bbe94eb42bf8e283fa6e04f9f593639,
  sama dengan putaran sebelumnya). Bila ada beda, berkas di repo yang berlaku.

LAPORAN
- Satu cabang audit baru, usul: audit/astra-cp1-7-r5-17fa2507-<tanggal>, dikunci dengan commit sebelum membaca laporan
  auditor lain di putaran ini:
  1. audit/astra_cp17_r5/RETEST_ASTRA_17fa2507.md — per temuan dan per butir: DITUTUP / MASIH TERBUKA / BARU, dengan bukti;
  2. audit/astra_cp17_r5/FINDINGS.json — temuan baru per akar masalah, tingkat, bukti; daftar yang harus beres sebelum
     pemasangan ke Enteng; daftar "belum saya periksa".
- Ringkasan untuk owner ≤ 10 kalimat, bahasa sehari-hari. Owner bukan programmer.
````
