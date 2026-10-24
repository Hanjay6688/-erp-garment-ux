# Peta kualifikasi current — inventaris, bukan penerimaan

Pada kandidat `a17b34cf3402eea8996028345fcf6d715367e684`, repo mempunyai **238 berkas workflow**.
Angka ini bukan 238 suite wajib atau 238 pengujian lulus. Dibandingkan integrasi
resmi `a255e48f`, ada 420 commit dan 956 berkas berubah. Inventaris seluruh diff
mendapat 33 workflow yang cocok dengan filter cabang integrasi/path lokal.
Pemeriksaan 58 deklarasi `SOURCE.json` menemukan 16 deklarasi dengan setidaknya
satu pin berbeda; hasil lengkap ada di `workflow-inventory-a17b34cf.json`.

`scripts/cp7_current_qualification_inventory.py` membaca blob Git dari commit
eksplisit. Tidak mengubah pin, menjalankan DB, memicu CI atau memajukan cabang.
Pencocokan pin tidak menjalankan admission impor/dependensi. Entrypoint yang
belum dapat dipetakan dicatat tersendiri; tidak diberi kredit lulus.

Dokumentasi GitHub.com yang diperiksa 24 Oktober 2026 menyebut batas diff
**3.000 berkas**, bukan 300 pada dokumentasi Enterprise Server lama. Diff956
di bawah batas tersebut. Tetap cocokkan daftar run aktual setelah dispatch;
hasil lokal tidak membuktikan job benar-benar dijalankan. Sumber:
[GitHub — Git diff comparisons](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#git-diff-comparisons).

## Bukti current yang sudah diperiksa

| Workflow | Bukti Original | Lingkup yang benar-benar terbukti |
|---|---|---|
| `cp7-current-installation` | `current-install-28abdeef-used-restore-pass.json` | Inventory wajib, generated types aktual, sembilan langkah backup/restore, enam kontrol negatif |
| `cp7-current-runner` | `current-runner-28abdeef-cron-used-restore-pass.json` | Cron menit asli tanpa tick manual; angka resmi; sembilan langkah restore |
| `cp7-ab-owner-families` | `owner62-28abdeef-pass.json` | 62 ID Native lama pada delapan keluarga A; bukan OW05 Native28/OW05b Native6 |
| `cp7-ab-owner-auth` | `owner-auth8-28abdeef-pass.json` | Delapan kasus Auth nyata OW05/06, dua pengguna, hak sesudah wait/replay |
| `cp7-ab-owner-browser` | `owner-browser19-7b26351f-pass.json` | 13 perjalanan daftar/retur dan enam mandor/transfer; bukan semua semantik lintas halaman OW09 |
| `cp7-ab-bounded-native` | `ab-bounded-28abdeef-native12-pass.json` | Lima kasus angka resmi, enam bounded, satu isolasi UUID/metode |
| `cp7-ab-bounded-browser` | `ab-bounded-browser4-28abdeef-pass.json` | Empat perjalanan bounded desktop/HP dengan Auth nyata |
| `cp7-ow14b-installation` | `ow14b-28abdeef-native4-pass.json` | Empat kasus inventaris minimum lama, identitas/satuan/enam desimal/UNKNOWN |
| `cp7-ab-bounded-restore` | `ab-bounded-28abdeef-used-restore-pass.json` | Sembilan langkah gabungan bounded sebelum successor inventory/types |

Semua baris itu mempunyai CP6/advisor dan lima gate paket PASS serta verifikasi
ZIP/Original byte+SHA. Delapan di head28abdeef; Browser19 di7b26351f. Perubahan
setelahnya menambah qualifier/dokumen, tidak mengganti sumber produk. Bukti tetap
berlabel **REUSED_WRITER_EVIDENCE**, bukan audit independen atau izin produksi.

## Pemetaan historis yang sudah mempunyai penerus

| Entry point historis | Penerus dan batas pemetaan |
|---|---|
| `ab-quote-browser-qualification` dan `ow09-chain-browser-qualification` Browser13 | Browser19 menjalankan 13 ID yang sama. Adapter retur memakai settlement quote current sambil mempertahankan oracle uang/stok/inverse; kegagalan awal tetap tersimpan. |
| `ow05b-browser-qualification` Browser2 | Dua ID panduan asli termasuk Browser19 tanpa perubahan modul perjalanan. |
| `ow06-browser-qualification` Browser2 | Dua ID transfer asli termasuk Browser19 tanpa perubahan modul perjalanan. |
| `finance-bridge-chain-qualification` Native5 | Lima ID asli merupakan lima kasus pertama Native12; bukan klaim factory3600. |
| `production-chain-qualification`, `b-extension-chain-qualification`, `ab-quote-chain-qualification` restore | Current installer menguji sembilan langkah pada seluruh gabungan dan enam kontrol negatif. Ini penerus preflight komposisi/restore, bukan pengganti Native286, perjalanan P21 seluruh uang, atau seluruh kasus B. |
| `cp7_contractor_guidance` Native6 | **Belum mempunyai Original current** dalam sembilan suite di atas. Adapter mandor Native34 baru menambahkan 28+6 ID lama, menunggu hasil server. |

Peta ini tidak menghapus workflow/pin historis. Mengganti trigger atau menyatakan
workflow lama selesai memerlukan pemetaan kasus/expected/observed per lingkup,
bukan hanya kesamaan nama atau katalog22. Workflow root yang tidak memiliki
ancestor SOURCE tetap memerlukan penelusuran admission dan bukti masing-masing.

## Bukti tambahan yang sedang dikerjakan

| Lingkup | Kandidat/run | Status saat catatan ditulis |
|---|---|---|
| Group transfer400+600 sesudah current full restore, empat koreksi dan inverse | `aea44fa9`, run40058216568/job120765815354 | PASS9langkah+6kontrol; seluruh group read/replay/empat koreksi/inverse tepat; CP6/advisor/lima gate PASS |
| Riwayat pembayaran/retur31 dokumen:25+6 dan filter30:25+5, desktop/390px | `a17b34cf`, run40058716148/job120767330087 | INCOMPLETE sebelum kasus: fixture import; Auth/DB/CP6/advisor bersih; firstfailure disimpan, perbaikan menunggu rerun |
| Mandor correction14 +edge3 +rate11 +guidance6 | `c99ca612`, run40059271805 | Baru berjalan; sumber874 lulus, 34 ID lama tanpa oracle baru |

Target berikut: terima Original tiga run itu; selesaikan sisa bukti lintas
halaman OW09; petakan pengganti layar CP6 yang dipensiunkan; jalankan daftar
kualifikasi satu kandidat beserta pembanding CP6 lengkap. **21 kegagalan CP6
dan empat kasus browser baseline tetap ditampilkan sesuai hasil asli**;
tidak ada kredit PASS karena tidak dijalankan. Formal parent tetap5/16,
`production_go=false`, kandidat audit lama tetap beku.
