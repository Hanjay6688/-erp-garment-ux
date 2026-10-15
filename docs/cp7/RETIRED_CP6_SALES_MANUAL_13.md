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

## Keputusan owner (13 Okt 2026, D13-9c)

**Disetujui bersyarat.** Pensiun berlaku sesudah auditor memastikan cakupan penggantinya lengkap. Kutipan lengkap ada
di `OWNER_DECISIONS_20261008.md` (D13-9). Owner mencatat: "sebagian pemeriksaan helper baru diuji lewat DOM simulasi;
cakupannya belum seluruhnya dibuktikan di browser sungguhan."

## Fakta tambahan untuk auditor

- Layar penjualan tersambung (P11, `src/SalesDraftPanel.tsx`) punya helper yang **berbeda** dari layar simulasi:
  "Isi dengan lusin + PCS" per baris. Isinya lusin bulat plus sisa 0–11 PCS, dan qty baris baru berubah sesudah tombol
  "Terapkan lusin baris N" ditekan.
- Bagi rata 1 lusin ke beberapa ukuran (4/4/4) dan penolakan 1,1 lusin hanya ada di layar simulasi `SalesPages`. Layar
  simulasi tidak tampil di mode tersambung.
- Sampai kandidat putaran 1 (`ae0214ad`), helper lusin P11 hanya diuji di jsdom (`src/SalesDraftPanel.dom.test.tsx`).
  Laporan Fable v1.1 menyatakan cakupan pengganti **TIDAK LENGKAP** karena itu.

## Putaran 2 (owner D13-12): kasus browser sungguhan P11 desktop dan HP

Kedua kasus pengganti yang sudah terdaftar, `P11_DRAFT_BROWSER_DESKTOP` dan `P11_DRAFT_BROWSER_MOBILE_RECOVERY`
(`scripts/cp7_p11_drafts_browser.mjs`, fungsi `dozenHelper`), sekarang menekan helper lusin di browser sungguhan. Produk
tidak diubah. Langkahnya:

1. Baris 1 berisi qty manual 13, baris 2 berisi qty 2, harga 10,01, potongan 0,02 dan catatannya. Bagian "Isi dengan
   lusin + PCS" baris 1 dibuka.
2. Isian yang tidak sah membuat tombol "Terapkan lusin baris 1" nonaktif, dan qty tetap 13. Isian itu: kosong, 1,1
   lusin, 1.1 lusin, sisa 12 PCS, dan 0 + 0.
3. Lusin 2 dan sisa 1 diisi. Sebelum tombol ditekan, qty tetap 13.
4. Tombol ditekan: qty menjadi 25, baris 2 tidak berubah, dan total menjadi Rp520. Di HP tidak ada geser horizontal.
   Tangkapan layar disimpan: `P11_DOZEN_HELPER_{DESKTOP,MOBILE}.png`.
5. Lusin 1 dan sisa 1 diterapkan: qty kembali 13 lewat helper (sebelumnya 25), dan total kembali Rp280.
6. Draft disimpan. Dibaca ulang dari server: qty barang `[2, 13]`, stok tersedia `[17, 28]`. Saat draft dibuka untuk
   diedit, qty baris itu terbaca 13 dari server.
7. Sisa alur kasus tidak berubah: edit menjadi 5, simpan, sahkan. Kasus HP juga tetap menguji balasan CREATE yang
   hilang.

Status pensiun tetap menunggu pernyataan auditor LENGKAP / TIDAK LENGKAP (D13-9c, D13-12).

## Koreksi 15 Okt 2026 (penulis; teks di atas tidak diubah)

Kalimat "Di mode aplikasi tersambung, menu 'Penjualan & Invoice' membuka `ConnectedSalesPage`" dan "Layar simulasi
tidak tampil di mode tersambung" **hanya benar untuk mode `DISPOSABLE_TEST`**. Syarat di `src/App.tsx` baris 637 adalah
`runtime.mode==='DISPOSABLE_TEST'`. Di mode `UAT_AUTH_SIMULATION` (login dan data Enteng), yang juga dihitung
tersambung oleh `isConnectedRuntime`, menu penjualan masih membuka layar simulasi `SalesPages` dengan data contoh,
termasuk helper lusin 4/4/4 yang lama. Alasan pensiun kedua kasus tetap: keduanya menguji layar simulasi, bukan
transaksi tersambung. Pengaktifan layar penjualan tersambung di Enteng belum direncanakan di dokumen mana pun; dicatat
untuk audit akhir CP1–7 (`audit-candidate/cp1-7-final-integration-20261015/SCREEN_MAP.md` butir 1–2).
