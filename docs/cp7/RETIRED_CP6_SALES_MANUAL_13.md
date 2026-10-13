# Dua kasus browser CP6 yang dipensiunkan: `BF_BROWSER:SALES_MANUAL_13_{DESKTOP,MOBILE}`

Diminta owner 13 Okt 2026: "Dua kasus CP6 yang disebut dipensiunkan harus punya rujukan keputusan dan cakupan
penggantinya."

## Rujukan keputusan

- **Siapa dan kapan.** Keputusan ini dibuat oleh writer saat kualifikasi pra-pembekuan, 6 Okt 2026. Rujukannya:
  `docs/cp7/PREFREEZE_RUNTIME_MIGRATION_20261006.md` (commit `a3aabd1d`, run 37466200640; pengganti setara
  `56c48b6e`, run 37468012520).
- **Status.** Ini **bukan keputusan owner**, dan auditor belum menutupnya. Dokumen itu sendiri menulis: "Audit Fable
  must independently inspect/rerun `a3aabd1d` … before closing PRE-01/05". Di audit `d0b9e9c2`, Fable mencatat kedua
  kasus sebagai `STALE_TEST_SELECTOR (PRE-05)`, terkait F-UI-02 (`audit/fable_cp7/AUDIT_FABLE_d0b9e9c2.md` baris 90).
- **Cakupan pensiun.** Kedua kasus hanya dikeluarkan dari komposisi CP7. Di suite CP6 yang dibekukan, keduanya tetap
  ada: `scripts/cp6_bf_browser.mjs`.
- **Alasan.** Kedua kasus menguji layar **simulasi** penjualan (helper lusin), bukan transaksi yang tersambung. Di mode
  aplikasi tersambung, menu "Penjualan & Invoice" membuka `ConnectedSalesPage` (P11), sehingga input
  `.biz-size-entry` tidak ada (`src/App.tsx` baris 637). Layar simulasi `SalesPages` hanya tampil di luar mode
  tersambung.

## Cakupan pengganti

| Pemeriksaan kasus lama (`salesManual`) | Pengganti |
|---|---|
| Qty manual 5/4/4 = 13 pcs tetap, total baris "13 pcs · 1 lusin · 1 potong" | `tests/cp7/SalesPages.dozenHelper.dom.test.tsx` (layar simulasi yang sama, tambahan 13 Okt). Di layar tersambung: `P11_DRAFT_BROWSER_DESKTOP` / `P11_DRAFT_BROWSER_MOBILE_RECOVERY` (`scripts/cp7_p11_drafts_browser.mjs`, `manual13_preserved`). |
| Helper kosong tidak mengubah apa pun | `tests/cp7/SalesPages.dozenHelper.dom.test.tsx` (tambahan 13 Okt) |
| Helper 1,1 lusin ditolak (pecahan potong), qty lama tetap | `tests/cp7/SalesPages.dozenHelper.dom.test.tsx` (tambahan 13 Okt). Aturan hitungnya: `src/sales/distributeDozensEvenly.test.ts` ("rejects a fractional piece result…"). |
| Helper 1 lusin = 4/4/4 | `tests/cp7/SalesPages.dozenHelper.dom.test.tsx` (tambahan 13 Okt). Aturan hitungnya: `src/sales/distributeDozensEvenly.test.ts` ("distributes one dozen evenly…"). |

Kedua kasus P11 juga menguji hal yang tidak ada di kasus lama:

- cari pelanggan/barang sungguhan, lalu buat draft lengkap;
- harga, potongan, catatan, termin;
- reservasi, ubah, posting;
- di HP, balasan CREATE yang hilang dicocokkan ulang dengan amplop yang sama.

Uji DOM 13 Okt mengulang keempat pemeriksaan lama di layar yang sama, tetapi di jsdom, bukan di browser sungguhan. Uji
itu tidak menggantikan kasus browser.

## Yang perlu diputuskan

Owner: apakah pensiun kedua kasus ini dari komposisi CP7, dengan pengganti di atas, disahkan (ya/tidak)? Auditor
(Fable) menilai cakupan penggantinya untuk PRE-05.
