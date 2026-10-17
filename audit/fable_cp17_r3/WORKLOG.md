# Fable r3 work log (kandidat b53b5acd, tree 32f54240)

## CP2 — tinjauan sumber (INDEPENDENT_SOURCE_REVIEW)

| Bagian | Hasil |
|---|---|
| D16-1 / oracle 1 aktivasi | `src/screenActivation.ts`: 47 menu; Enteng dan mode uji sama-sama CONNECTED 46 + Dashboard NOTICE; tidak ada HIDDEN/SAMPLE/BOUNDARY |
| D16-1 / oracle 4 layar baru | `audit/audit.sql`, `erp-settings/settings.sql`, `sales/customer-history.sql`, `warehouse-summary/summary.sql`: fasad baca-saja. `manual-reminders/facade.sql`: di atas tabel Native pengingat milik pengguna. `hpp-pool/pool.sql`: hanya memanggil penulis Native `validate/activate/cancel_attendance_hpp_pool_v1` di bawah `erp._cp3_lock_business_period`. Tidak ada `insert/update/delete` langsung ke tabel `erp` di enam berkas baru |
| D16-1 / oracle 2 build Enteng | Host browser produk (`cp6_auditor_browser_host.mjs`): `AUDITOR_UI_MODE=ENTENG` membangun build `UAT_AUTH_SIMULATION` dengan origin proyek Enteng dan kunci placeholder; route browser membelokkan origin itu ke API loopback, origin lain diblokir; workflow CP17 penulis juga memetakan host Enteng ke 127.0.0.1. UI tidak memakai realtime/websocket |
| R3-09 / D16-2..4 pilihan tarif | Tarif baru dibayar lewat baris revisi di `po_work_component_snapshots` (indeks unik ditambah `committed_at`, delta Native dideklarasikan). Saya periksa semua pemakaian tabel itu di paket rilis CP6 (20ac, 20ah, 20ai, 20ap, 20bb, 20bd, 20be): dibaca per `id`, `exists`, `count>0` untuk "sudah ada", atau baris terbaru dengan `order by committed_at desc` (kasus BS) — tidak ada penjumlahan per PO × komponen yang akan dobel. Fungsi skema dasar di luar pohon tidak bisa saya periksa |
| R3-02 buka ulang PO | FG_USED = keluar dikurangi pembaliknya sendiri, minimal 0. Kasus tepi: pembalik atas barang masuk dihitung pemakaian → lebih ketat, bukan lebih longgar |
| R3-01 nomor PO | `lpad(n, greatest(3,len(n)))`: tidak macet sesudah 999 |
| D16-5 tab Tutup Buku | `finance/period.sql`: riwayat 50 perubahan `closed_through` dari `erp.audit_logs` (kolom terbatas) |
| FABLE-018 | `cp6_bd_browser.mjs`: `allInnerTexts()` tanpa menunggu; oracle kasus tidak diubah |

## CP3 — dispatch (17 Okt; kepala penulis 64339905, pohon produk = b53b5acd)
Fable (cabang r3, head 00b9bfaa): 39052813501 cash_basis lama tanpa perubahan; 39052820257 r2_cash_both tanpa perubahan;
39052826601 sensus `fable_r3_screens.mjs` build DISPOSABLE. Sensus build ENTENG 39052833191 **dibatalkan saya** saat
"Start disposable database" (sebelum kasus) karena workflow Fable belum memetakan host Enteng ke loopback; langkah itu
ditambahkan (head 94084607) lalu dikirim ulang. Penulis: CP17 Fixes, prefreeze UI, F03 cash, misc correction, payment
correction, P12 payroll, cutting correction, P13 period, sales chain, UI phone width (39052840551 … 39052901934).
