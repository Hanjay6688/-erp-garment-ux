# Handoff uji ulang perbaikan CP1–CP7 r1 — untuk Sol

Owner menyalin **seluruh isi kotak di bawah** ke sesi Sol. Kandidatnya sama untuk Fable, Astra dan Sol. Rincian:
`README.md` dan `FINDINGS_TRACKER.md` di folder ini.

````text
Kamu Sol, auditor independen. Ini UJI ULANG perbaikan penulis atas temuanmu di audit penuh CP1–CP7
(audit/sol_cp1_7/AUDIT_REPORT.md, FINDINGS.json, WRITER_HANDOFF.md, 10bfe397, cabang
audit/sol-cp1-7-0b7049d9-20261014). Repo Hanjay6688/-erp-garment-ux. Fable dan Astra menguji ulang kandidat yang sama
secara terpisah.

KANDIDAT
- Commit e8ce4b89318b8320058855f420e5c8dc1495a55e, tree 7e3348be91a17cac6f7120c550b1b5d50f203bc4, cabang writer claude/new-session-deapao. Basis auditmu: 0b7049d9 (tree ce6aed0a).
- supabase/ tidak berubah sejak 0b7049d9 (buktikan: git diff --name-only 0b7049d9 e8ce4b89318b8320058855f420e5c8dc1495a55e -- supabase kosong).
  Perubahan produk ada di scripts/cp7-src/ (lapisan CP7 + delta Native yang dideklarasikan) dan src/.
- Bukti penulis: docs/cp7/audit-candidate/cp1-7-fix-r1-20261015/README.md (per temuan), FINDINGS_TRACKER.md
  (bagian G dan H), CI_RECEIPT.json (semua workflow dan job pada kandidat), docs/cp7/cp17/CP17_FIXES.json (48 kasus yang
  dideklarasikan sebelum dijalankan; workflow "CP7 CP17 Fixes").

BAGIAN YANG BERUBAH SESUDAH KANDIDAT 55d72775 (owner 15 Okt: "minta auditor memverifikasi bagian yang berubah")
Keputusan owner D14-5 dan D14-8..D14-11 tercatat persis di docs/cp7/OWNER_DECISIONS_20261008.md. Bila kamu sudah
mulai menguji 55d72775, hasil itu tetap berlaku untuk bagian yang tidak berubah (git diff 55d72775 e8ce4b89 -- src scripts
menunjukkan seluruh perubahan). Uji bagian di bawah dengan oracle-mu sendiri:
Utama (dari temuanmu atau yang menyentuh temuanmu):
- D14-5 lusin per seri di draf penjualan tersambung (Sol SALES_MANUAL_13): satu pilih menambah semua ukuran SKU itu yang ada stoknya, seri baru mulai 1 lusin dibagi rata; ketik manual 3/5/4 terbaca "1 lusin"; SKU satu ukuran: 1 lusin = 12 di ukuran itu (seperti UX demo). src/SalesDraftPanel.tsx, src/sales/seriesDozens.ts; browser CP17_BROWSER_D14_5_SERIES_DOZENS_DESKTOP dan _MOBILE (Auth dan PostgREST nyata, fixture stok 3 ukuran dan 1 ukuran).
- Dua perbaikan alat uji saat kualifikasi (bukan produk): scripts/cp7_catalog_state.py membaca entri D14-8 (pasangan sama + owner harus cocok; run F03 38668243786 gagal sebelum itu) dan scripts/cp6_av_runtime.py refuse_post_use mengulang hanya penolakan PACKAGE_REQUIRES_CLOSED_DRAINED_DATABASE seperti change() (run AV 38670698254 gagal sebelum itu). Periksa bahwa tidak ada yang dilonggarkan.
- D14-8 pembanding skema public (A2): urutan stabil (kolasi "C"), semua anggota dan duplikat, definisi, owner dan hak akses dibandingkan; query lama disimpan untuk bukti. A2_COMPARATOR_D14_8.md, scripts/cp6_auditor_runner.py (PUBLIC_STATE), bukti sebelum/sesudah scripts/cp6_auditor_public_state_test.py (langkah sendiri di workflow CP17). Akar dua kegagalan A2 lama tetap OPEN (D13-10).
Juga periksa bila sempat:
- D14-9 FABLE-012: pencabutan EXECUTE 82 penulis erp ditunda ke CP7C sebagai pekerjaan keamanan terbuka; gerbang exposure_gate (scripts/cp7_access_inventory.py) menolak CP7_FABLE012_REVOKE_BEFORE_EXPOSING_ERP bila erp akan terjangkau Data API (dinyatakan, extra search path, atau penimpaan tersimpan di peran authenticator) sebelum pencabutan. FABLE012_D14_9_GATE.md; kasus CP17_FABLE012_EXPOSURE_GATE_REVOKE_FIRST.
- D14-10 batal/betulkan kain kembali (SG-02): satu transaksi — jurnal kain kembali dibalik lewat erp.reverse_journal Native, gerakan REVERSAL per gerakan kembali, hitung ulang biaya bahan (+ antrean HPP bila ada barang jadi), fakta kembali dikosongkan, pembetulan langsung diposting lagi; riwayat asli tetap; pemakaian sesudahnya disebut dan menghalangi. SG02_FABRIC_RETURN.md bagian D14-10, scripts/cp7-src/cutting-correction/return.sql, src/CuttingFabricReturnReversalPanel.tsx; kasus CP17_SG02_CANCEL_*, CP17_SG02_CORRECT_RETURN_ONE_TRANSACTION, browser CP17_BROWSER_SG02_FABRIC_RETURN_CORRECT_DESKTOP. Batas: dicatat pada saat disimpan (seperti pembalik Native), hari-hari di antaranya tetap menunjukkan angka lama.
- D14-11 upah rework untuk bagian yang selesai walau kasus BS OPEN/PARTIAL (RWK01): baris pekerjaan rework dengan order COMPLETED dan biaya terposting bisa masuk Nota; yang belum selesai ditahan; dibayar sekali, tidak muncul lagi saat kasus ditutup. RWK01_D14_11.md, scripts/cp7_rework_eligibility_bundle.py; kasus CP17_RWK01_OPEN_CASE_FINISHED_PART_PAID_ONCE.

YANG DIUJI ULANG (temuanmu → klaim penulis)
- SOL-001 bank saldo 0 bisa bayar supplier → D14-3: kas/bank tidak boleh minus pada tanggal mana pun, satu penjaga
  per rekening untuk semua pengeluaran, termasuk pembayaran bertanggal mundur dan dua pembayaran bersamaan.
  Kasus CP17_CASH_* (6), CP17_RACE_TWO_PAYMENTS_ONE_BANK, CP17_HTTP_CASH_EMPTY_BANK_REFUSED. Fixture yang membayar
  memakai modal owner lewat jurnal Native (scripts/cp7_cash_funding.py); kasus bank kosong tetap kosong.
- SOL-002 artefak BE 4/16 → folder keluaran tidak lagi dipindah saat impor AV; gerbang unggah memeriksa himpunan ID,
  status dan hasil akhir (scripts/cp6_av_probe.py, scripts/cp6_be_probe.py). Workflow "CP6 BE T1 Family Probe".
- SOL-003 + OPEN-AZ-FIRST → diagnosis PostgreSQL disimpan di berkas terpisah 0600 di sebelah laporan (juga proses
  lain di database saat gagal: jenis dan status saja). Catatan jujur: di CI berkas itu ikut artifact run (repo ini publik, jadi artifact
  run bisa diunduh akun GitHub mana pun; isinya data uji sekali pakai, bukan data produksi). Penyebab paling mungkin kegagalan pertama di AZ: autovacuum masuk ke database yang sudah
  ditutup dan blok pertama AZ menolak; log run pertamamu tidak menyebut blok mana, jadi ini belum terbukti. Pemasang
  owner sekarang menunggu proses lain keluar sebelum tiap berkas dan hanya mengulang penolakan
  PACKAGE_REQUIRES_CLOSED_DRAINED_DATABASE (transaksi berkas itu sudah batal); teks pengaman tidak berubah.
  scripts/cp6_readiness_owner_install.py, scripts/cp6_readiness_owner_drain_test.py (6 kasus; jalan di workflow CP17).
  Workflow readiness milik penulis terikat cabang cp6/release-readiness dan menolak cabang ini; jalankan pemasangan
  owner 58 berkas lewat workflow milikmu seperti sebelumnya, sebaiknya beberapa kali.
Juga periksa regresi di sekitar perubahan kas: upah, vendor laundry, kasbon (D14-6), dan pembalikan.

ATURAN PUTARAN
- Tanpa saling intip (Pro Max §2.2, §16.7): jangan membaca laporan, cabang, run, artifact atau komentar auditor lain
  dari putaran uji ulang ini sampai laporanmu dikunci dengan commit. Laporan yang sudah terkunci sebelum putaran ini
  (ketiga audit penuh atas 0b7049d9 dan addendumnya) boleh dibaca.
- Label asal-bukti per klaim (§2.9). Baca status per kasus dari log atau artifact, bukan warna job (§2.10). Rerun
  paling banyak sekali dan hanya bila job mati sebelum kasus berjalan (§1.9).
- Dispatch workflow writer hanya dengan ref claude/new-session-deapao dan catat head_sha yang terpakai; bila head
  sudah bergeser, buktikan tree produk sama sebelum memakai hasilnya (§1.7, §2.8, §16.1).
- Jangan percaya klaim penulis begitu saja: susun oracle sendiri dari kontrak dan keputusan owner (D14-2..D14-11).
  Keputusan owner yang sudah disahkan tidak dibuka ulang; pertanyaan yang sudah dijawab tidak ditulis ulang sebagai
  terbuka (§2.12).
- Tidak boleh dimutasi: main, deployment Cloudflare, Supabase hosted Enteng (siimvrusnzxexizpyoib), legacy ERP-Garment
  (vlxdhpkjeevubjxexnfo, read-only), production. Jangan meminta password, token atau kunci di chat.
- Panduan: docs/AUDIT_PANDUAN_PRO_MAX.md (SHA-256 5752e96df751de5ebe4b86d3f572cffa1bbe94eb42bf8e283fa6e04f9f593639,
  sama dengan saat audit penuh). Bila ada beda, berkas di repo yang berlaku.

LAPORAN
- Cabang audit baru, usul: audit/sol-cp1-7-retest-e8ce4b89-20261015, berkas audit/sol_cp1_7_retest/RETEST_REPORT.md
  dan FINDINGS.json. Per temuan: DITUTUP / MASIH TERBUKA / BARU, dengan bukti.
- Ringkasan untuk owner dalam bahasa sehari-hari, pendek. Owner bukan programmer.
````
