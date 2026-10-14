# Handoff uji ulang perbaikan CP1–CP7 r1 — untuk Fable

Owner menyalin **seluruh isi kotak di bawah** ke sesi Fable. Kandidatnya sama untuk Fable, Astra dan Sol. Rincian:
`README.md` dan `FINDINGS_TRACKER.md` di folder ini.

````text
Kamu Fable, auditor independen. Ini UJI ULANG perbaikan penulis atas temuanmu di audit penuh CP1–CP7
(audit/fable_cp17/AUDIT_FABLE_0b7049d9.md v1.0 + addendum A1–A3, cabang audit/fable-cp1-7-0b7049d9-20261014).
Repo Hanjay6688/-erp-garment-ux. Astra dan Sol menguji ulang kandidat yang sama secara terpisah.

KANDIDAT
- Commit <KANDIDAT>, tree <TREE>, cabang writer claude/new-session-deapao. Basis auditmu: 0b7049d9 (tree ce6aed0a).
- supabase/ tidak berubah sejak 0b7049d9 (buktikan: git diff --name-only 0b7049d9 <KANDIDAT> -- supabase kosong).
  Perubahan produk ada di scripts/cp7-src/ (lapisan CP7 + delta Native yang dideklarasikan) dan src/.
- Bukti penulis: docs/cp7/audit-candidate/cp1-7-fix-r1-20261015/README.md (per temuan), FINDINGS_TRACKER.md
  (bagian G), CI_RECEIPT.json (semua workflow dan job pada kandidat), docs/cp7/cp17/CP17_FIXES.json (40 kasus yang
  dideklarasikan sebelum dijalankan; workflow "CP7 CP17 Fixes").

YANG DIUJI ULANG (temuanmu → klaim penulis)
- FABLE-001 bayar upah sebelum utangnya ada → ditolak (D14-2), kasbon jalur sendiri. Kasus CP17_FIN01_*.
- FABLE-002/003/004 dan A1 (dokumen, salinan paket, bukti CP1/CP2, 4 tabel tanpa RLS) → README tabel R-DOC.
- FABLE-005 → pemetaan 75 C6 + 22 ALL milik Astra (C6_75_ALL22_CROSSWALK, d4a83b42); tidak ada kode baru.
- FABLE-006 rework sesudah SCRAP → upah yang sudah diakui bisa masuk Nota sekali. Kasus CP17_RWK01_*.
- FABLE-007 (dugaan absensi dobel) → tidak ada perubahan produk. Penjaganya ada di skema dasar, bukan di migrasi pohon
  ini: erp.guard_payroll_period_overlap (supabase/tests/fixtures/erp_enteng_cp45a_catalog_bootstrap.sql.gz baris
  10325-10342) mengunci per mandor lalu menolak payroll aktif kedua yang periodenya bertumpuk. Regresi
  CP17_RACE_OVERLAPPING_PAYROLL_ONE_WINS: payroll kedua di atas hari absensi ditolak; dua payroll bertumpuk dikirim
  bersamaan, satu lolos.
- FABLE-008 klaim laundry bertanggal mundur → ditolak. Kasus CP17_FIN02_*.
- FABLE-009 pickup POSTED tanpa koreksi → batal Bagi Potongan sebelum dijahit (SG01_PICKUP_REVERSAL.md); dua delta
  Native dideklarasikan dan dipulihkan persis saat uninstall. Kasus CP17_SG01_* + browser desktop.
- FABLE-010 sisa kain → kain kembali ke gudang (D14-4, SG02_FABRIC_RETURN.md). Kasus CP17_SG02_* + browser HP.
- FABLE-011 → tidak diubah (bergantung keputusan owner).
- FABLE-012 hak EXECUTE authenticated ke erp → inventaris + bukti 82 penulis tidak terjangkau dari Data API
  (CP17_HTTP_ERP_WRITERS_NOT_REACHABLE). Pencabutan EXECUTE belum (menunggu owner). Owner mengizinkan kamu membaca
  setelan API hosted (D14-7): baca saja, tanpa mengubah apa pun.
Juga periksa regresi di sekitar perubahan: kas per tanggal (D14-3) untuk semua pengeluaran, kasbon (D14-6), kartu
stok sesudah REOPEN/POST ulang (Astra STK01), kebijakan HPP (Astra HPP01), dan bahwa delta Native yang baru tidak
melonggarkan penjaga lama.

ATURAN PUTARAN
- Tanpa saling intip (Pro Max §2.2, §16.7): jangan membaca laporan, cabang, run, artifact atau komentar auditor lain
  dari putaran uji ulang ini sampai laporanmu dikunci dengan commit. Laporan yang sudah terkunci sebelum putaran ini
  (ketiga audit penuh atas 0b7049d9 dan addendumnya) boleh dibaca.
- Label asal-bukti per klaim (§2.9). Baca status per kasus dari log atau artifact, bukan warna job (§2.10). Rerun
  paling banyak sekali dan hanya bila job mati sebelum kasus berjalan (§1.9).
- Dispatch workflow writer hanya dengan ref claude/new-session-deapao dan catat head_sha yang terpakai; bila head
  sudah bergeser, buktikan tree produk sama sebelum memakai hasilnya (§1.7, §2.8, §16.1).
- Jangan percaya klaim penulis begitu saja: susun oracle sendiri dari kontrak dan keputusan owner (D14-2..D14-7).
  Keputusan owner yang sudah disahkan tidak dibuka ulang; pertanyaan yang sudah dijawab tidak ditulis ulang sebagai
  terbuka (§2.12).
- Tidak boleh dimutasi: main, deployment Cloudflare, Supabase hosted Enteng (siimvrusnzxexizpyoib), legacy ERP-Garment
  (vlxdhpkjeevubjxexnfo, read-only), production. Jangan meminta password, token atau kunci di chat.
- Panduan: docs/AUDIT_PANDUAN_PRO_MAX.md (SHA-256 5752e96df751de5ebe4b86d3f572cffa1bbe94eb42bf8e283fa6e04f9f593639,
  sama dengan saat audit penuh). Bila ada beda, berkas di repo yang berlaku.

LAPORAN
- Cabang audit baru, usul: audit/fable-cp1-7-retest-<KANDIDAT8>-20261015, berkas
  audit/fable_cp17_retest/RETEST_FABLE_<KANDIDAT8>.md. Per temuan: DITUTUP / MASIH TERBUKA / BARU, dengan bukti.
- Ringkasan untuk owner dalam bahasa sehari-hari, pendek. Owner bukan programmer.
````
