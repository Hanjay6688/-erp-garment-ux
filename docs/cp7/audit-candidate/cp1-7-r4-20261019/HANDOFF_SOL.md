# Uji ulang r4 CP1–CP7 — untuk Sol

Owner menyalin **seluruh isi kotak di bawah** ke sesi Sol. Kandidatnya sama untuk Fable, Astra dan Sol.
Rincian: `README.md` di folder ini.

````text
Kamu Sol, auditor independen. Ini UJI ULANG PUTARAN r4 untuk ERP Garment, repo Hanjay6688/-erp-garment-ux, cabang
writer claude/new-session-deapao. Kamu sudah menguji ulang kandidat r3 b53b5acd (audit/sol_cp17_r3/, cabang audit/sol-cp1-7-r3-b53b5acd-20261017, segel
ff6374ad; tidak ada temuan produk baru dari pengujian buta; tiga butir terbuka yang sudah diketahui untuk penulis:
KNOWN-POOL-PUBLIC-ENTRYPOINTS, KNOWN-BACKUP-REPLACEMENT-WRITE, KNOWN-P19-DIRECT-LATENCY). Penulis memperbaiki temuan putaran r3 di r4 dan mengerjakan kecepatan analisis
langsung atas keputusan owner D17-1. Fable, Astra dan Sol menguji ulang kandidat yang sama secara terpisah.
KANDIDAT
- Commit 769f2cc3e37225ddefaac3e6b4cf6afc1040037d, tree d88081dcb611b0c6369cb2d775df24494df0284d. Basis r3: b53b5acdf260b03ebac3474e9ae837fcef6f6eb1
  (tree 32f54240a60e01ab8b1ffad7267d285a669be520). Commit sesudah kandidat di cabang writer hanya dokumen; buktikan:
  git diff --name-only 769f2cc3e37225ddefaac3e6b4cf6afc1040037d origin/claude/new-session-deapao. Catat tree produk sebelum dan sesudah auditmu (Pro Max §2.8).
- supabase/ tidak berubah sejak b53b5acd (git diff --name-only b53b5acdf260b03ebac3474e9ae837fcef6f6eb1 769f2cc3e37225ddefaac3e6b4cf6afc1040037d -- supabase kosong). Perubahan produk ada
  di scripts/ (lapisan CP7, alat uji) dan src/; daftar lengkap: git diff --stat b53b5acdf260b03ebac3474e9ae837fcef6f6eb1 769f2cc3e37225ddefaac3e6b4cf6afc1040037d -- src scripts tests .github.
- Bukti penulis: docs/cp7/audit-candidate/cp1-7-r4-20261019/CI_RECEIPT.json (semua run dan job pada kandidat; ringkasan di
  README.md bagian Kandidat); docs/cp7/cp17/CP17_FIXES.json (341 kasus CP17 dideklarasikan sebelum dijalankan: 161 Native,
  39 race, 27 HTTP Auth nyata, 57 browser, dan 57 kasus browser yang sama di build mode Enteng; workflow "CP7 CP17 Fixes").
  Run, job dan kasus disebut terpisah.
- Paket: docs/cp7/audit-candidate/cp1-7-r4-20261019/ (README.md per akar R4-01..R4-05, CROSS_AUDIT.md audit silang penulis
  atas ketiga laporan r3). Isinya titik awal penulis, bukan bukti lulus.

KEPUTUSAN OWNER BARU (kutipan persis di docs/cp7/OWNER_DECISIONS_20261008.md, D17-1): "A beresin aja, mau gw tinggal tidur
soalnya" — kecepatan analisis langsung dikerjakan di r4 sebelum paket uji ulang. Batas 8 detik, pemeriksaan
sumber/otoritas/hash/kelengkapan dan keputusan 7 Okt (pekerjaan berat boleh di latar belakang sebagai pengecualian yang
dicatat; target 3 detik tidak ditandai tercapai kalau belum) tetap berlaku. Keputusan yang sudah disahkan tidak dibuka
ulang; uji dengan oracle-mu sendiri.

YANG DIUJI ULANG (temuanmu → klaim penulis; uji dengan kasusmu sendiri, angka dan hasil yang kamu harapkan tidak diganti)
- KNOWN-POOL-PUBLIC-ENTRYPOINTS → R4-01 (akar yang sama dengan ASTRA-R3-01): 25 fungsi publik lama menolak sesi Data API
  (42501 CP7_PUBLIC_ROUTE_CLOSED); sesi database tidak berubah; sensus fungsi publik peran browser. Kasus:
  CP17_HTTP_R4_01_*, CP17_R4_01_*.
- KNOWN-BACKUP-REPLACEMENT-WRITE → sah, tetapi tidak dipasang: owner D13-9a menahan semua pekerjaan backup sampai CP7C.
  Patch dan pemeriksaan lokal penulis: docs/cp7/cp17/r4-sol/ (CP7C_BACKUP_DISPOSABLE_SCRATCH.patch; 12/12 kasus off-site
  lulus dengan patch, kasus baru gagal tanpa patch). Tidak ada di kandidat; diuji di CI saat CP7C.
- KNOWN-P19-DIRECT-LATENCY → R4-05 (owner D17-1): diagnosis hitungan waktu per fungsi (run 39157467151) menunjukkan
  erp.require_internal() dipanggil sekitar 32.000 kali per analisis dengan angka keuangan (3,9 dari 6,3 detik). Penjaga kini
  menjawab kasus tanpa baris konteks perintah dengan satu pemeriksaan; dengan baris apa pun urutan lama berjalan utuh
  (scripts/cp7_internal_guard_bundle.py; CP17_R4_05_INTERNAL_GUARD_SAME_ANSWER, ..._DISPATCH_REVIEWED). Layar menulis
  "Sedang dihitung sejak jam …" seketika. Hasil dan yang belum tercapai: docs/cp7/p19/P19_R4_05_DIRECT_LATENCY.md
  (100 target dengan angka keuangan 2,30–2,60 detik; 300 target tetap di atas 3 detik). Ulangi pengukuranmu sendiri.

JUGA PERIKSA (bukan temuanmu, dan regresi di sekitarnya)
- R4-02..R4-04 (temuan Astra) seperti di README.md.
- R4-05 mengubah penjaga erp.require_internal() yang dipanggil hampir setiap penulis Native. Coba patahkan klaim "jawaban
  sama": baris konteks perintah dari transaksi ini, transaksi lain, backend lain, aktor lain; pemanggil OWNER, STAFF,
  peran bukan internal, tanpa pengguna, service role; penolakan halus di dalam pemeriksaan konteks (misalnya
  CP7_SALES_WRITE_DENIED). verify() di scripts/cp7_internal_guard_bundle.py dan kasus CP17_R4_05_*.
- Bahwa penjaga lama tidak dilonggarkan: kas per tanggal ekonomi dan buku (D14-3, D15-1), bayar upah tidak mendahului akrual
  (D14-2), lantai cutover (D15-5), kebijakan HPP, delta Native yang dideklarasikan hanya berlaku di dalam perintahnya.

YANG SUDAH DIKETAHUI PENULIS (uji sendiri; jangan dianggap benar atau salah tanpa bukti)
- Lapisan CP7 belum terpasang di Enteng (CP7C ditahan, D13-9a); build Enteng diuji terhadap salinan sekali pakai.
- FABLE-012 tetap ditunda ke CP7C (D14-9). Patch backup Sol disiapkan untuk CP7C, tidak dipasang.
- Analisis langsung: 300 target belum 3 detik; dengan angka keuangan biaya laporan pemilik Native tumbuh dengan buku besar
  dan dibaca dua kali per analisis langsung; pemeriksaan ulang saat kirim sengaja dipertahankan.

ATURAN
- Tanpa saling intip (Pro Max §2.2, §16.7): jangan membaca laporan, cabang, run, artifact atau komentar auditor lain dari
  putaran ini sampai laporanmu dikunci dengan commit. Laporan yang sudah terkunci sebelum putaran ini (ketiga laporan r3)
  boleh dibaca; audit silang penulis ada di CROSS_AUDIT.md.
- Label asal-bukti per klaim (§2.9). Baca status per kasus dari log atau artifact, bukan warna job (§2.10). Rerun paling
  banyak sekali dan hanya bila job mati sebelum kasus berjalan (§1.9).
- Dispatch workflow writer hanya dengan ref claude/new-session-deapao dan catat head_sha yang terpakai; bila head sudah
  bergeser, buktikan tree produk sama sebelum memakai hasilnya (§1.7, §2.8, §16.1).
- Jangan percaya klaim penulis begitu saja: susun oracle sendiri dari kontrak dan keputusan owner (D14-2..D17-1).
  Pertanyaan yang sudah dijawab owner tidak ditulis ulang sebagai terbuka (§2.12).
- Tidak boleh dimutasi: main, deployment Cloudflare, Supabase hosted Enteng (siimvrusnzxexizpyoib), legacy ERP-Garment
  (vlxdhpkjeevubjxexnfo, read-only), production. Jangan meminta password, token atau kunci di chat.
- Panduan: docs/AUDIT_PANDUAN_PRO_MAX.md (SHA-256 5752e96df751de5ebe4b86d3f572cffa1bbe94eb42bf8e283fa6e04f9f593639,
  sama dengan putaran sebelumnya). Bila ada beda, berkas di repo yang berlaku.

LAPORAN
- Satu cabang audit baru, usul: audit/sol-cp1-7-r4-769f2cc3-<tanggal>, dikunci dengan commit sebelum membaca laporan
  auditor lain di putaran ini:
  1. audit/sol_cp17_r4/RETEST_SOL_769f2cc3.md — per temuan dan per butir: DITUTUP / MASIH TERBUKA / BARU, dengan bukti;
  2. audit/sol_cp17_r4/FINDINGS.json — temuan baru per akar masalah, tingkat, bukti; daftar yang harus beres sebelum
     pemasangan ke Enteng; daftar "belum saya periksa".
- Ringkasan untuk owner ≤ 10 kalimat, bahasa sehari-hari. Owner bukan programmer.
````
