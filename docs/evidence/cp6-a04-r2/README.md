# Bukti AUD-A04-R2: koleksi saldo awal yang hilang tidak lagi dibaca sebagai kosong

Temuan asal: audit independen ChatGPT 23 September 2026 (`ERP_CP6_Audit_Independen_20260923`, §5).

## Perubahan

- `src/initialProduction.ts`: koleksi sumber produksi yang tidak ada (`undefined`) ditolak dengan pesan "Daftar saldo produksi tidak terbaca lengkap." Hanya `[]` eksplisit yang berarti nol.
- `src/ConnectedInitialImportPage.tsx`: `cash_advances`, `advance_payrolls`, `prepayments`, `prepayment_cash_accounts`, dan `production_sources` wajib ada. Key yang hilang ditolak, tidak diganti `[]`.
- `src/ConnectedWipStatusPage.tsx`: tulisan "Tidak ada WIP aktif." hanya muncul bila total diketahui (respons valid dan tidak basi). Selain itu tampil "WIP belum dapat dipastikan."
- Tidak diubah: penanganan data basi yang sudah ada. `beginRead` menandai ruang kerja basi sampai pembacaan berhasil, sehingga KPI tampil "—" dan penulisan terkunci. Data terakhir tetap ditampilkan bersama pemberitahuan recovery, sesuai desain yang sudah ada.
- Backend AP (`supabase/migrations/20260922135615_erp_v2_6_20ap_cp6_connected_import_materials.sql`) selalu mengirim keenam koleksi, dibungkus `coalesce(...,'[]')`, untuk batch status apa pun. Keharusan baru ini tidak mematahkan backend saat ini.
- Fixture tes yang memodelkan payload tidak lengkap dilengkapi dengan koleksi kosong eksplisit (`tests/fixtures/productionRecovery.ts`, `src/accessProductionControl.test.ts`, dua wrapper dan satu fixture di `src/ConnectedInitialImportPage.dom.test.tsx`). Maksud setiap tes tidak berubah.

## Hasil

| File | Isi | Total / lulus / gagal |
| --- | --- | --- |
| `gpt_probe_on_2257431_before_fix.json` | Probe asli ChatGPT pada source sebelum perbaikan (= a58c057 untuk produk) | 12 / 5 / 7, sama dengan audit |
| `gpt_probe_on_fix_unmodified.json` | Probe asli tanpa perubahan, pada source sesudah perbaikan | 12 / 8 / 4 |
| `gpt_probe_on_fix_adapted_capture.json` | Probe dengan hanya pencatatan observasi dibungkus `try/catch`; semua assertion sama | 12 / 12 / 0 |
| `new_tests_on_pre_fix_source.json` | Tes repo baru/terubah dijalankan pada source produk sebelum perbaikan | 54 / 45 / 9 (9 kontrak baru gagal seperti seharusnya) |
| `full_suite_before_fix.json` | Seluruh vitest (tanpa browser) sebelum perbaikan | 442 / 442 / 0 |
| `full_suite_after_fix.json` | Seluruh vitest (tanpa browser) sesudah perbaikan | 454 / 454 / 0 |

Empat kegagalan pada probe asli sesudah perbaikan disebabkan desain probe. Probe memanggil parser sekali untuk mencatat observasi, di luar `expect(...).toThrow()`. Parser sekarang menolak payload tidak lengkap sesuai kontrak, sehingga pemanggilan pencatat itu melempar error sebelum assertion berjalan. Pesan error yang tercatat ("… tidak terbaca lengkap.") adalah perilaku yang diminta kontrak. `gpt_probe_adapted.test.tsx.txt` berisi salinan yang diadaptasi. Diff-nya hanya tiga baris pencatatan; SHA256 probe asli: `be47260f8873b4e1bb9d30737db306c99111764f8dce5705ccb548f4bcbb4946`.

Pemeriksaan lain sesudah perbaikan: `tsc -b` exit 0, `check:source`, `check:access`, `check:css`, `check:cp5`, `check:cp6`, `check:backend`, dan `check-production-recovery.mjs` lulus.

## Batas bukti

- Parser asli dan komponen React asli di jsdom, dengan RPC dan identitas tiruan. **Bukan** bukti browser, HTTP, Auth, atau database.
- Tidak membuktikan backend normal pernah mengirim payload tidak lengkap. Ini penguatan boundary frontend terhadap versi respons yang tertinggal, payload terpotong, atau regresi serializer.
- Halaman impor menampilkan pesan umum dari `normalizeClientError` untuk error parser ("Layanan UAT belum dapat dihubungi…"). Perilaku ini sudah ada sebelumnya dan tidak diubah; dicatat sebagai perbaikan UX kecil untuk nanti.
- Browser nyata untuk halaman ini (gate browser successor) belum dijalankan: **NOT_RUN**.
