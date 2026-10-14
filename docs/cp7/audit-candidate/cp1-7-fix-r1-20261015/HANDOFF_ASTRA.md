# Handoff uji ulang perbaikan CP1–CP7 r1 — untuk Astra

Owner menyalin **seluruh isi kotak di bawah** ke sesi Astra. Kandidatnya sama untuk Fable, Astra dan Sol. Rincian:
`README.md` dan `FINDINGS_TRACKER.md` di folder ini.

````text
Kamu Astra, auditor independen. Ini UJI ULANG perbaikan penulis atas temuanmu di audit penuh CP1–CP7
(audit/astra_cp17/AUDIT_ASTRA_CP17_0b7049d9.md f70361d5, lanjutan d5dcf4e3, addendum silang followup-681dd7a9/
d4a83b42, cabang audit/astra-cp1-7-0b7049d9-20261014). Repo Hanjay6688/-erp-garment-ux. Fable dan Sol menguji ulang
kandidat yang sama secara terpisah.

KANDIDAT
- Commit <KANDIDAT>, tree <TREE>, cabang writer claude/new-session-deapao. Basis auditmu: 0b7049d9 (tree ce6aed0a).
- supabase/ tidak berubah sejak 0b7049d9 (buktikan: git diff --name-only 0b7049d9 <KANDIDAT> -- supabase kosong).
  Perubahan produk ada di scripts/cp7-src/ (lapisan CP7 + delta Native yang dideklarasikan) dan src/.
- Bukti penulis: docs/cp7/audit-candidate/cp1-7-fix-r1-20261015/README.md (per temuan), FINDINGS_TRACKER.md
  (bagian G), CI_RECEIPT.json (semua workflow dan job pada kandidat), docs/cp7/cp17/CP17_FIXES.json (40 kasus yang
  dideklarasikan sebelum dijalankan; workflow "CP7 CP17 Fixes").

YANG DIUJI ULANG (temuanmu → klaim penulis)
- FIN01 (S0) bayar upah sebelum akrual → ditolak (D14-2) di perintah CP7 dan pemicu Native PAID; detektor data lama.
  Kasus CP17_FIN01_*, CP17_DETECTOR_LISTS_LEGACY_ROWS, CP17_HTTP_PAYROLL_EARLY_REFUSED.
- FIN02 (S0) klaim laundry sebelum utang vendor → ditolak. Kasus CP17_FIN02_*.
- STK01 (S0) kartu stok −10 sesudah REOPEN lalu POST ulang → tidak minus. CP17_STK01_REOPEN_REPOST_CARD_NOT_NEGATIVE.
- RWK01 upah rework hilang bila semua SCRAP → masuk Nota sekali; OPEN/PARTIAL masih ditahan (pertanyaan owner).
- HPP01 pool ACTIVE basi → perubahan peserta ditolak; batal → pool pengganti. CP17_HPP01_*.
- SG-01 batal Bagi Potongan sebelum dijahit (SG01_PICKUP_REVERSAL.md), SG-02 kain kembali ke gudang (D14-4),
  SG-03 cuci ulang produk sama tanpa tagihan vendor (D06, tanpa jalur tagihan baru).
- RBAC/akses langsung (bersama FABLE-012) → bukti 82 penulis erp tidak terjangkau dari Data API; pencabutan EXECUTE
  belum (menunggu owner).
- CP1_CP2_CROSSCHECK → bukti CP1/CP2 dibawa ke pohon dengan hash (docs/evidence/cp1-cp2/); restore CP2 di image asli
  tetap bagian CP7C (ditahan).
- Konkurensi FABLE-007 yang tidak kamu sertifikasi → CP17_RACE_OVERLAPPING_PAYROLL_ONE_WINS (penjaga Native
  erp.guard_payroll_period_overlap di skema dasar, dikunci per mandor).
Juga periksa sambungan antartahap yang tersentuh: kas per tanggal (D14-3) di semua pengeluaran, kasbon (D14-6),
lusin per seri di draf penjualan (D14-5; belum ada uji browser khusus), dan bahwa delta Native SG-01 hanya berlaku di
dalam perintahnya.

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
- Cabang audit baru, usul: audit/astra-cp1-7-retest-<KANDIDAT8>-20261015, berkas
  audit/astra_cp17_retest/RETEST_ASTRA_<KANDIDAT8>.md. Per temuan: DITUTUP / MASIH TERBUKA / BARU, dengan bukti.
- Ringkasan untuk owner dalam bahasa sehari-hari, pendek. Owner bukan programmer.
````
