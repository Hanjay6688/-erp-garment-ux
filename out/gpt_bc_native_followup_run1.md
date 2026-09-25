# GPT BC — run mandiri 1 (disposable)

**Identitas:** [run 36182512996](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36182512996), job 108228022712, workflow GPT CP6 BC Independent Follow-up, commit pemicu `ed741dfdf0ec8933ccb7c2cbbce5943fe70fc09e`; tool_head `62d05c43b981dc031bca260e8b4809aadcd9a01c`, product_ref `40d6906358af451711d04574d184d500ab4fa944`, phase `after` memasang BC. Oracle `34c744864e548aa1b06300321a40ccf227158dab97375220cf63cbcfc9cdf82c`, Python `35f9aaf22de529a1ac436001d38ddfc3a18111c33e36a9d79687bc0c7586d8c2`, browser `0fa516b3cd0a3cc165393b25c06bd947b456fbed7a39318aeb9f5f49d25f39a2` sha256. Input hash terverifikasi di langkah 28.

## Per kasus

- `GBC-1:NEW_CUSTODY_KEY_SAME_PHYSICAL_CLAIM` **INCOMPLETE / NEEDS_SOURCE_IDENTITY_POLICY**. Setelah import dan valuasi 3 PCS key pertama, stok siap 3 dan perubahan jurnal MATERIAL_INVENTORY +6, OTHER_INCOME −6. Import key kedua dengan catatan yang mengklaim barang fisik sama diterima; setelah inspeksi+valuasi key kedua stok siap **6** dan jurnal bertambah +6/−6 lagi. Kontrol positif penerimaan fisik baru yang terpisah menaikkan stok menjadi **9**. Tidak ada error import kedua; lot kedua 1. Karena sumber hanya punya key yang diberikan pemanggil, catatan bebas tidak membuktikan dua key mewakili barang yang sama secara fisik. Hasil ini menunjukkan batas kontrol; **bukan** counterexample produk yang final dan **bukan** PASS ACC-C12. `full_boundary_restored=true`, `public_schema_unchanged=true`, advisory locks/sesi bocor 0.
- `GBC-2:POSTGRES_UUID_OLD_MANDOR_PAGE_READ` **INCOMPLETE alat**: browser host gagal sebelum kasus berjalan, `ERR_MODULE_NOT_FOUND: Cannot find package '@playwright/test'`; workflow audit lupa `npm ci` di checkout alat. Tidak ada verdict produk ataupun kontrol v4 dari run ini.
- `GBC-3` belum didispatch.

Job failure karena GBC-1 sengaja INCOMPLETE menahan acceptance dan host browser gagal. `primary_unchanged=true`, `clone_remaining=0`, Auth tetap [0,0,0,0]. Run merah tetap merah; rerun baru diperlukan setelah alat diperbaiki.

**Status gate:** ACC-C12 PARTIAL/UNVERIFIED (M:3935, M:5290); F3/ACC-D09 UNVERIFIED (M:5304); C6-04, C6-07, C6-10 HOLD; C6-08 UNVERIFIED; CP6 HOLD, `audit_complete=false`, `production_go=false`.

**LANGKAH BERIKUTNYA:** tambahkan `npm ci` dan Playwright Chromium di workflow audit saja, pin hash skenario sama, dispatch ulang satu workflow BC; periksa GBC-2 dan cleanup. Pertahankan GBC-1 INCOMPLETE sampai owner menentukan identitas sumber fisik atau tersedia provenance yang dapat dibuktikan. Selanjutnya GBC-3 filter lintas tab. Tidak ada kode produk diubah.
