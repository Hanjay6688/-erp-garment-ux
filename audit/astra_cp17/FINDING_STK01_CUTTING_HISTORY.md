# ASTRA-CP17-STK-01 — Posting ulang potongan menggandakan prefix kartu stok historis

**TERBUKTI: respons publik kartu stok bertanggal salah; prioritas S0 sesuai §8 untuk angka stok yang diterima tanpa penolakan.** Batasnya penting: saldo stok sekarang tetap benar, dan mesin biaya memakai effective history berbeda. Tidak diklaim seluruh HPP/neraca salah atau seluruh detector diam.

Kandidat `0b7049d9203bac52b47a4c89f3e0d75646067a8f`, FULL composition. Petunjuk Fable R3-08; desain/eksekusi Astra sesudah exposure yang diizinkan. Run `38567853922`, job `115865040095`, control `7912acb719e80365a40776f8df0e8a020377990d`; artifact `11895499774`, SHA256 `861863d06a71c20bf59d9ce3e5226f8bb003b4c09d09d4ab1b01708d816ab22e`. Kasus `CP17-ASTRA-R3-03-CUTTING-REPOST-CHRONOLOGY` COUNTEREXAMPLE, restoration/public/session gates bersih.

## Saksi yang lengkap sampai posting ulang

| Tahap | Saldo cutoff 13 Okt 08:00 WIB dari kartu | Saldo sekarang |
|---|---:|---:|
| Beli 10 tanggal 11 Okt; POST potong 10 tanggal 12 Okt | 0 | 0 |
| REOPEN lewat CP7 pada 14 Okt | 0 | 10 |
| SAVE_DRAFT lalu POST lagi 10 dengan cut_at asli 12 Okt | **−10** | 0 |

Semua efek berasal dari writer sah, bukan INSERT mutasi auditor. Posting ulang berhasil (`material_issue_posted:true`, total 10 PCS). `public.erp_cp7_get_material_ledger_v1` menampilkan empat baris lengkap, `history_basis=CURRENT_RESTATED_NOT_AS_KNOWN`:

- pembelian +10 pada 11 Oktober;
- issue lama −10 pada 12 Oktober;
- issue pengganti −10 juga pada 12 Oktober, **running_qty −10**;
- inverse +10 pada 14 Oktober, running_qty kembali 0.

Valuation baris issue pengganti diberi `state=KNOWN`. Dua header jurnal CUTTING_MATERIAL_ISSUE bertanggal 12 Oktober (lama REVERSED, baru POSTED); header JOURNAL_REVERSAL bertanggal 14 Oktober. Saksi ini menyimpan header, bukan seluruh baris GL; tidak menyimpulkan nominal salah saji neraca dari header saja.

Original: `ASTRA_CP17_R3_CUTTING_REPOST_FIRST.json` dan `CP17_OWN_CASES_FABLE_SEAMS.json`. Angka before/reopened/after dan reader publik penuh tersimpan. Tes penulis `CP7_CUTTING_REOPEN_EXACT_STOCK_GL_DRAFT` hanya sampai SAVE_DRAFT; hasil PASS tes itu tidak mencakup re-POST yang kini terbukti bermasalah.

## Penyebab dan aturan waktu yang tidak boleh tertukar

Native inverse mempertahankan cut_at asli dan menulis inverse pada waktu sekarang. Ini memang batas yang diterima dalam `docs/cp7/CUTTING_REOPEN_HANDOFF.json`: tidak menjanjikan restatement ekonomi historis. Temuan ini **tidak** meminta pembalik dipaksa memakai tanggal lama.

Masalah yang terukur ada pada sambungan dengan posting pengganti dan proyeksi kartu: `scripts/cp7-src/materials/read.sql` menjumlah semua mutasi menurut physical_at, termasuk pasangan source/inverse yang sudah tidak efektif. Mesin biaya dan `period_integrity_blockers_v1` dalam rilis BF justru mengecualikan pasangan reversal pada effective history. Karena itu kartu yang mengaku CURRENT_RESTATED bisa menampilkan prefix −10 sementara effective history mengandung satu issue aktif. Membaca guard cost engine saja tidak membantah respons publik yang direkam.

Kontrol detector keuangan/material sebelum-saat-sesudah dan browser untuk saksi baru ini **belum dijalankan**. Tidak mengklaim false READY, kerusakan data permanen, atau saldo pabrik saat ini negatif. Prioritas S0 ditetapkan pada angka historis publik yang salah dengan command sukses; luas dampak di reader lain masih perlu ditelusuri.

## Perbaikan dan penerimaan

Penulis perlu menyelaraskan arti effective/restated history antara reader publik, writer pengganti, mesin biaya dan laporan bertanggal sambil mempertahankan audit trail append-only serta aturan current-clock yang telah diterima. Pilihan implementasinya harus jelas: baris historis boleh tetap terlihat, tetapi pasangan yang dinetralisasi jangan dihitung seolah dua konsumsi fisik aktif pada saldo restated. Jangan sekadar menolak semua re-POST dan menyebut alur koreksi lengkap.

Uji kembali saksi yang sama sampai re-POST dan baca ulang kartu/server. Tambahkan perubahan jumlah, tanggal sama/berbeda, repeat correction, periode tertutup, sisa stok cukup/tidak cukup, pickup downstream, replay dan refusal atomik. Rekonsiliasi saldo fisik, effective cost, jurnal lengkap dan laporan cutoff. Browser desktop/HP harus menunjukkan satu dampak yang berlaku dan riwayat yang jelas. Bukti detector wajib dipisahkan dari bukti penolakan writer. Perubahan maju saja; migrasi lama tidak diedit.
