# Uji ulang r4 CP1–CP7 — untuk Astra

Owner menyalin **seluruh isi kotak di bawah** ke sesi Astra. Kandidatnya sama untuk Fable, Astra dan Sol.
Rincian: `README.md` di folder ini.

````text
Kamu Astra, auditor independen. Ini UJI ULANG PUTARAN r4 untuk ERP Garment, repo Hanjay6688/-erp-garment-ux, cabang
writer claude/new-session-deapao. Kamu sudah menguji ulang kandidat r3 b53b5acd (audit/astra_cp17_r3/, cabang audit/astra-cp1-7-r3-b53b5acd-20261018,
kunci 741ffdf3; vonis TAHAN: ASTRA-R3-01 dan sisa ASTRA-R2-01 tingkat S1, ASTRA-R3-02 dan ASTRA-R3-03 tingkat S2). Penulis memperbaiki temuan putaran r3 di r4 dan mengerjakan kecepatan analisis
langsung atas keputusan owner D17-1. Fable, Astra dan Sol menguji ulang kandidat yang sama secara terpisah.
KANDIDAT
- Commit 663f6faefcbb9c70f0f99bbc7e78164e03521329, tree 023f3554432f80f994439f5d0b8cc164846a2041. Basis r3: b53b5acdf260b03ebac3474e9ae837fcef6f6eb1
  (tree 32f54240a60e01ab8b1ffad7267d285a669be520). Commit sesudah kandidat di cabang writer hanya dokumen; buktikan:
  git diff --name-only 663f6faefcbb9c70f0f99bbc7e78164e03521329 origin/claude/new-session-deapao. Catat tree produk sebelum dan sesudah auditmu (Pro Max §2.8).
- supabase/ tidak berubah sejak b53b5acd (git diff --name-only b53b5acdf260b03ebac3474e9ae837fcef6f6eb1 663f6faefcbb9c70f0f99bbc7e78164e03521329 -- supabase kosong). Perubahan produk ada
  di scripts/ (lapisan CP7, alat uji) dan src/; daftar lengkap: git diff --stat b53b5acdf260b03ebac3474e9ae837fcef6f6eb1 663f6faefcbb9c70f0f99bbc7e78164e03521329 -- src scripts tests .github.
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
- ASTRA-R3-01 (S1, pembungkus publik CP4 pool HPP menulis di periode tertutup dan sesudah hak kelola dicabut) → R4-01:
  25 fungsi publik lama yang tidak dipakai aplikasi menolak sesi Data API sebagai pernyataan pertama (42501
  CP7_PUBLIC_ROUTE_CLOSED); sensus fungsi publik peran browser (authenticated dan anon) gagal sampai fungsi baru ditinjau.
  scripts/cp7_public_routes_bundle.py. Dua kasus HTTP-mu apa adanya: CP17_HTTP_R4_01_POOL_PUBLIC_CLOSED_PERIOD_ASTRA,
  CP17_HTTP_R4_01_POOL_PUBLIC_REVOKED_MANAGE_ASTRA; kontrol CP17_HTTP_R4_01_EVERY_CLOSED_ROUTE_REFUSED_APP_ROUTES_OPEN,
  CP17_R4_01_DATA_API_REFUSED_DATABASE_SESSION_UNCHANGED, CP17_R4_01_EVERY_PUBLIC_ROUTE_REVIEWED.
- ASTRA-R2-01 sisa (S1, buka ulang PO terhalang sesudah penyesuaian barang jadi +2 dan pembaliknya) → R4-02:
  po-reopen.sql tidak lagi menghitung pembalik pemasukan sebagai pemakaian. Kasusmu apa adanya:
  CP17_R4_02_REOPEN_POSITIVE_ADJUSTMENT_INVERSE_ASTRA; kontrol pemakaian aktif tidak tersembunyi, buka ulang lalu selesai
  lagi sama, dua tab (CP17_R4_02_*, CP17_RACE_R4_02_*).
- ASTRA-R3-02 (S2, Audit Trail melewati id lebih kecil yang commit belakangan) → R4-03: tanda isi daftar di snapshot dan
  kursor; halaman berikut dengan tanda berbeda mengatakan changed/newer dan layar meminta Muat ulang. Jadwal tiga sesimu
  apa adanya: CP17_RACE_R4_03_AUDIT_LOWER_ID_LATE_COMMIT_ASTRA; kontrol CP17_RACE_R4_03_*, CP17_R4_03_AUDIT_LISTING_MARK_REFUSALS.
- ASTRA-R3-03 (S2, angka WIP tersambung pucat) → R4-04: kartu terang memberi warna teksnya sendiri; sensus keterbacaan
  menolak teks di bawah 2:1 di semua menu, desktop dan HP, dan angka WIP di bawah 4,5:1:
  CP17_BROWSER_R4_04_CONNECTED_TEXT_READABLE_{DESKTOP,MOBILE} (+ _ENTENG). Sensus itu juga menemukan panel pool HPP,
  tombol RecordTools BS dan layar Master Data tersambung; ikut diperbaiki.

JUGA PERIKSA (bukan temuanmu, dan regresi di sekitarnya)
- R4-05 (butir Sol KNOWN-P19-DIRECT-LATENCY, owner D17-1) seperti di README.md.
- R4-05 mengubah penjaga erp.require_internal() yang dipanggil hampir setiap penulis Native. Coba patahkan klaim "jawaban
  sama": baris konteks perintah dari transaksi ini, transaksi lain, backend lain, aktor lain; pemanggil OWNER, STAFF,
  peran bukan internal, tanpa pengguna, service role; penolakan halus di dalam pemeriksaan konteks (misalnya
  CP7_SALES_WRITE_DENIED). verify() di scripts/cp7_internal_guard_bundle.py dan kasus CP17_R4_05_*.
- R4-Q1 (ditemukan penulis saat kualifikasi): uji pg_cron K4/K6 dan fixture browser K4 membaca catatan run pg_cron
  sesudah setiap akhir run tertulis, bukan begitu hasilnya terlihat (scripts/cp7_schedule.py wait_recorded). Periksa
  bahwa syarat lulusnya tidak berubah.
- Bahwa penjaga lama tidak dilonggarkan: kas per tanggal ekonomi dan buku (D14-3, D15-1), bayar upah tidak mendahului akrual
  (D14-2), lantai cutover (D15-5), kebijakan HPP, delta Native yang dideklarasikan hanya berlaku di dalam perintahnya.

YANG SUDAH DIKETAHUI PENULIS (uji sendiri; jangan dianggap benar atau salah tanpa bukti)
- Lapisan CP7 belum terpasang di Enteng (CP7C ditahan, D13-9a); build Enteng diuji terhadap salinan sekali pakai.
- FABLE-012 tetap ditunda ke CP7C (D14-9). Patch backup Sol disiapkan untuk CP7C, tidak dipasang.
- Analisis langsung: 300 target belum 3 detik; 100 target dengan angka keuangan belum stabil di bawah 3 detik (tergantung
  runner). Dengan angka keuangan biaya laporan pemilik Native tumbuh dengan buku besar dan dibaca dua kali per analisis
  langsung; pemeriksaan ulang saat kirim sengaja dipertahankan.

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
- Satu cabang audit baru, usul: audit/astra-cp1-7-r4-663f6fae-<tanggal>, dikunci dengan commit sebelum membaca laporan
  auditor lain di putaran ini:
  1. audit/astra_cp17_r4/RETEST_ASTRA_663f6fae.md — per temuan dan per butir: DITUTUP / MASIH TERBUKA / BARU, dengan bukti;
  2. audit/astra_cp17_r4/FINDINGS.json — temuan baru per akar masalah, tingkat, bukti; daftar yang harus beres sebelum
     pemasangan ke Enteng; daftar "belum saya periksa".
- Ringkasan untuk owner ≤ 10 kalimat, bahasa sehari-hari. Owner bukan programmer.
````
