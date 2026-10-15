# Handoff uji ulang perbaikan CP1–CP7 r1 — untuk Astra

Owner menyalin **seluruh isi kotak di bawah** ke sesi Astra. Kandidatnya sama untuk Fable, Astra dan Sol. Rincian:
`README.md` dan `FINDINGS_TRACKER.md` di folder ini.

````text
Kamu Astra, auditor independen. Ini UJI ULANG perbaikan penulis atas temuanmu di audit penuh CP1–CP7
(audit/astra_cp17/AUDIT_ASTRA_CP17_0b7049d9.md f70361d5, lanjutan d5dcf4e3, addendum silang followup-681dd7a9/
d4a83b42, cabang audit/astra-cp1-7-0b7049d9-20261014). Repo Hanjay6688/-erp-garment-ux. Fable dan Sol menguji ulang
kandidat yang sama secara terpisah.

KANDIDAT
- Commit f1a1ae6926ed563b960f476125c5e2273e750157, tree 982831d6e788b2a3a9404f25a4617230e0b98f0b, cabang writer claude/new-session-deapao. Basis auditmu: 0b7049d9 (tree ce6aed0a).
- supabase/ tidak berubah sejak 0b7049d9 (buktikan: git diff --name-only 0b7049d9 f1a1ae6926ed563b960f476125c5e2273e750157 -- supabase kosong).
  Perubahan produk ada di scripts/cp7-src/ (lapisan CP7 + delta Native yang dideklarasikan) dan src/.
- Bukti penulis: docs/cp7/audit-candidate/cp1-7-fix-r1-20261015/README.md (per temuan), FINDINGS_TRACKER.md
  (bagian G dan H), CI_RECEIPT.json (semua workflow dan job pada kandidat), docs/cp7/cp17/CP17_FIXES.json (48 kasus yang
  dideklarasikan sebelum dijalankan; workflow "CP7 CP17 Fixes").

BAGIAN YANG BERUBAH SESUDAH KANDIDAT 55d72775 (owner 15 Okt: "minta auditor memverifikasi bagian yang berubah")
Keputusan owner D14-5 dan D14-8..D14-11 tercatat persis di docs/cp7/OWNER_DECISIONS_20261008.md. Bila kamu sudah
mulai menguji 55d72775, hasil itu tetap berlaku untuk bagian yang tidak berubah (git diff 55d72775 f1a1ae69 -- src scripts
menunjukkan seluruh perubahan). Uji bagian di bawah dengan oracle-mu sendiri:
Utama (dari temuanmu atau yang menyentuh temuanmu):
- D14-10 batal/betulkan kain kembali (SG-02): satu transaksi — jurnal kain kembali dibalik lewat erp.reverse_journal Native, gerakan REVERSAL per gerakan kembali, hitung ulang biaya bahan (+ antrean HPP bila ada barang jadi), fakta kembali dikosongkan, pembetulan langsung diposting lagi; riwayat asli tetap; pemakaian sesudahnya disebut dan menghalangi. SG02_FABRIC_RETURN.md bagian D14-10, scripts/cp7-src/cutting-correction/return.sql, src/CuttingFabricReturnReversalPanel.tsx; kasus CP17_SG02_CANCEL_*, CP17_SG02_CORRECT_RETURN_ONE_TRANSACTION, browser CP17_BROWSER_SG02_FABRIC_RETURN_CORRECT_DESKTOP. Batas: dicatat pada saat disimpan (seperti pembalik Native), hari-hari di antaranya tetap menunjukkan angka lama.
- D14-11 upah rework untuk bagian yang selesai walau kasus BS OPEN/PARTIAL (RWK01): baris pekerjaan rework dengan order COMPLETED dan biaya terposting bisa masuk Nota; yang belum selesai ditahan; dibayar sekali, tidak muncul lagi saat kasus ditutup. RWK01_D14_11.md, scripts/cp7_rework_eligibility_bundle.py; kasus CP17_RWK01_OPEN_CASE_FINISHED_PART_PAID_ONCE.
- D14-9 FABLE-012: pencabutan EXECUTE 82 penulis erp ditunda ke CP7C sebagai pekerjaan keamanan terbuka; gerbang exposure_gate (scripts/cp7_access_inventory.py) menolak CP7_FABLE012_REVOKE_BEFORE_EXPOSING_ERP bila erp akan terjangkau Data API (dinyatakan, extra search path, atau penimpaan tersimpan di peran authenticator) sebelum pencabutan. FABLE012_D14_9_GATE.md; kasus CP17_FABLE012_EXPOSURE_GATE_REVOKE_FIRST.
- D14-5 lusin per seri di draf penjualan tersambung (Sol SALES_MANUAL_13): satu pilih menambah semua ukuran SKU itu yang ada stoknya, seri baru mulai 1 lusin dibagi rata; ketik manual 3/5/4 terbaca "1 lusin"; SKU satu ukuran: 1 lusin = 12 di ukuran itu (seperti UX demo). src/SalesDraftPanel.tsx, src/sales/seriesDozens.ts; browser CP17_BROWSER_D14_5_SERIES_DOZENS_DESKTOP dan _MOBILE (Auth dan PostgREST nyata, fixture stok 3 ukuran dan 1 ukuran).
Juga periksa bila sempat:
- Dua perbaikan alat uji saat kualifikasi (bukan produk): scripts/cp7_catalog_state.py membaca entri D14-8 (pasangan sama + owner harus cocok; run F03 38668243786 gagal sebelum itu) dan scripts/cp6_av_runtime.py refuse_post_use mengulang hanya penolakan PACKAGE_REQUIRES_CLOSED_DRAINED_DATABASE seperti change() (run AV 38670698254 gagal sebelum itu). Ketiga: tests/cp7/families/f05-timeline.test.ts memberi batas 180 detik hanya untuk proses pembanding sekali pakai (fungsi pendahulu yang dibandingkan bersifat kuadratik; fungsi produk 0,3 detik; run Shell S0 38673762153 gagal sebelum itu), seperti P19 di ce455269. Periksa bahwa tidak ada yang dilonggarkan.
- D14-8 pembanding skema public (A2): urutan stabil (kolasi "C"), semua anggota dan duplikat, definisi, owner dan hak akses dibandingkan; query lama disimpan untuk bukti. A2_COMPARATOR_D14_8.md, scripts/cp6_auditor_runner.py (PUBLIC_STATE), bukti sebelum/sesudah scripts/cp6_auditor_public_state_test.py (langkah sendiri di workflow CP17). Akar dua kegagalan A2 lama tetap OPEN (D13-10).

YANG DIUJI ULANG (temuanmu → klaim penulis)
- FIN01 (S0) bayar upah sebelum akrual → ditolak (D14-2) di perintah CP7 dan pemicu Native PAID; detektor data lama.
  Kasus CP17_FIN01_*, CP17_DETECTOR_LISTS_LEGACY_ROWS, CP17_HTTP_PAYROLL_EARLY_REFUSED.
- FIN02 (S0) klaim laundry sebelum utang vendor → ditolak. Kasus CP17_FIN02_*.
- STK01 (S0) kartu stok −10 sesudah REOPEN lalu POST ulang → tidak minus. CP17_STK01_REOPEN_REPOST_CARD_NOT_NEGATIVE.
- RWK01 upah rework hilang bila semua SCRAP → masuk Nota sekali; OPEN/PARTIAL: lihat D14-11 di atas.
- HPP01 pool ACTIVE basi → perubahan peserta ditolak; batal → pool pengganti. CP17_HPP01_*.
- SG-01 batal Bagi Potongan sebelum dijahit (SG01_PICKUP_REVERSAL.md), SG-02 kain kembali ke gudang (D14-4),
  SG-03 cuci ulang produk sama tanpa tagihan vendor (D06, tanpa jalur tagihan baru).
- RBAC/akses langsung (bersama FABLE-012) → bukti 82 penulis erp tidak terjangkau dari Data API; pencabutan EXECUTE
  ditunda ke CP7C dengan gerbang (D14-9, di atas).
- CP1_CP2_CROSSCHECK → bukti CP1/CP2 dibawa ke pohon dengan hash (docs/evidence/cp1-cp2/); restore CP2 di image asli
  tetap bagian CP7C (ditahan).
- Konkurensi FABLE-007 yang tidak kamu sertifikasi → CP17_RACE_OVERLAPPING_PAYROLL_ONE_WINS (penjaga Native
  erp.guard_payroll_period_overlap di skema dasar, dikunci per mandor).
Juga periksa sambungan antartahap yang tersentuh: kas per tanggal (D14-3) di semua pengeluaran, kasbon (D14-6),
lusin per seri di draf penjualan (D14-5, di atas), dan bahwa delta Native SG-01 hanya berlaku di
dalam perintahnya.

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
- Cabang audit baru, usul: audit/astra-cp1-7-retest-f1a1ae69-20261015, berkas
  audit/astra_cp17_retest/RETEST_ASTRA_f1a1ae69.md. Per temuan: DITUTUP / MASIH TERBUKA / BARU, dengan bukti.
- Ringkasan untuk owner dalam bahasa sehari-hari, pendek. Owner bukan programmer.
````
