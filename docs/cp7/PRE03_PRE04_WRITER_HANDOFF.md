# PRE-03 dan PRE-04 — handoff writer (Claude) untuk Fable

Dasar: job desc Fable 6 Okt 2026 (`out/JOBDESC_WRITER_PRE03_PRE04_20261006.md`, cabang audit a1e8a93). Lingkupnya hanya dua item ini. Cabang `claude/new-session-deapao` sudah di-fast-forward ke `cp7/integration` 8f326d87 sebelum perbaikan, jadi produk yang diuji adalah CP7 terbaru GPT.

## SHA perbaikan

- **SHA perbaikan final: `d82fa583`.** Isinya hanya uji, di atas 8f326d87. Kedua suite sudah lulus di SHA ini (lihat tabel run).
- `REWORK_SKU_PARTIAL_COMPLETE_REVERSE` hanya ada di skenario auditor; job browser T3 tidak memuat kasus itu. Di job T3, kasus BE yang ada hanya `REDYE_SKU_UNKNOWN_THEN_PRICE_MOBILE`.
- Commit yang membentuknya:
  - `92f30e42`: PRE-03 dan langkah cari PRE-04.
  - `d311ba8a`: hanya dokumen P19.
  - `d82fa583`: langkah pembatalan rework PRE-04.

## Berkas yang diubah

| Jenis | Berkas | Perubahan |
|---|---|---|
| Uji | `scripts/cp6_be_browser.mjs` | PRE-04: pencarian BS lewat form `RecordTools`; pembatalan hasil rework lewat langkah periksa CP7 |
| Uji | `scripts/cp6_au_browser_ui.mjs` | PRE-03: kunci merek WIP dibuktikan sesuai perilaku CP7 |
| Produk | — | Tidak ada |

## Alasan per perubahan

### PRE-04

1. **Pencarian BS.**
   - **Penyebab:** selector `.cbsr-search` dihapus di 5e4af78f. Pencarian pindah ke form bersama `RecordTools` (`aria-label="Cari, browse, urutkan dan filter BS dan claim"`). Tombol "Cari" di form itu hanya memindahkan fokus (`type="button"`), sedangkan pencarian dijalankan oleh "Cari kasus" (`type="submit"`).
   - **Ubahan uji:** mengisi `getByLabel('Cari BS atau claim')` di dalam form itu, lalu menekan "Cari kasus".
   - **Pengecekan selector lain:** semua selector lain di alur rework/redye sudah dicocokkan dengan sumber CP7. Satu-satunya selector yang hilang hanya `.cbsr-search`.
2. **Pembatalan hasil rework.**
   - **Kapan terlihat:** langkah ini baru tercapai sesudah perbaikan nomor 1, di run 37446319529 pada 92f30e42. `REWORK_SKU_PARTIAL_COMPLETE_REVERSE` lolos membuat order, partial, dan selesai, lalu berhenti di sini. Kegagalan pertama itu tetap tercatat.
   - **Penyebab:** di 51c96475, kolom "Alasan reversal Owner/Admin" dan tombol "Reverse" CP6 diganti dengan langkah periksa.
   - **Ubahan uji:**
     - mengisi "Alasan pembatalan hasil rework";
     - menekan "Periksa pembatalan hasil";
     - memastikan panel "Pemeriksaan pembatalan hasil rework" menyebut nomor order dan "Batalkan hasil 2 Good dan 2 BS" (pengecekan tambahan);
     - menekan "Sahkan pembatalan hasil".
3. **Yang tetap.** Semua pengecekan bisnis tetap sama:
   - partial tanpa FG;
   - selesai sekali (2 Good, 2 BS, satu konversi);
   - SKU target;
   - rework: qty 0 dan konversi REVERSED;
   - redye: tarif 50 dan biaya 200.

### PRE-03

- **Penyebab: perilaku produk berubah.**
  - Di 5eb4ad20 (CP7, 1 Okt), halaman impor melepas fakta saldo lama begitu ada perubahan pemulihan, termasuk saat envelope transaksi sendiri disimpan. Caranya: `observeProductionRecovery` memanggil `setWorkspace(null)`. Akibatnya panel "Saldo fisik produksi awal" tidak dirender (`if (!selected) return null`), sejak tombol sahkan diklik sampai reconcile dan reload selesai.
  - Uji DOM GPT pada commit yang sama juga mengganti `expect(button('Sahkan hasil WIP awal').disabled)` menjadi `not.toContain('Sisa 5 pcs')`.
  - Jadi field "Merek hasil WIP" tidak pernah tampil-dan-terkunci di CP7, dan `toBeDisabled()` tidak bisa lulus tanpa mengubah produk.
- **Cara membuktikan kunci yang sama seperti CP6:**
  - Locator `getByRole('textbox',{name:'Merek hasil WIP',disabled:false})` dan `getByRole('button',{name:'Sahkan hasil WIP awal',disabled:false})` dipakai untuk mencari field merek yang bisa diedit dan tombol sahkan yang aktif.
  - Sebelum klik, keduanya wajib menemukan tepat 1. Ini kontrol positif, supaya hasil 0 sesudahnya bukan locator yang salah.
  - Sesudah balasan hilang, keduanya wajib 0. Sesudah reload juga wajib 0, dengan "Reconcile transaksi" aktif.
  - Replay wajib mengirim envelope yang identik, termasuk merek. Pengecekan ini sudah ada sebelumnya.
- **Yang tidak berubah:**
  - replay UUID/payload yang sama dan data ERP tidak berubah saat retry;
  - stok, HPP, dan produk per merek;
  - pembalikan bertaut untuk kedua fixture.
- **Catatan untuk Fable:**
  - `toBeDisabled()` diganti, tidak dipindah, karena tidak ada titik di CP7 saat field itu tampil dalam keadaan terkunci.
  - Pengganti ini tidak melonggarkan sifat kunci. Field yang tampil dan aktif tetap gagal di uji, sedangkan field yang terkunci atau dilepas lulus.
  - Yang dilepas hanya syarat "field harus tampil", dan itu sengaja dihapus oleh desain CP7.
  - Bila Fable menuntut field merek tetap tampil dan terkunci selama rekonsiliasi, itu perubahan produk pada desain pelepasan GPT. Perubahan itu tidak dilakukan writer tanpa keputusan.

## Run dan hasil per kasus

Kegagalan asli Fable tetap tercatat:
- job browser T3: run 37431675640, job 112163746060 di 095b33b0;
- skenario auditor: run 37432485240, job 112166361971 di 875443d0.

| SHA | Suite | Run / job | Hasil |
|---|---|---|---|
| 92f30e42 | Job browser T3 | 37446316844 / 112211909204 | Alur AT PASS 10/10. `BE_BROWSER:REDYE_SKU_UNKNOWN_THEN_PRICE_MOBILE` PASS. Paket browser lain 27 PASS / 4 INCOMPLETE (di luar lingkup, lihat bawah). |
| 92f30e42 | Skenario auditor after (`cp6_be_modes.py` + `cp6_be_browser.mjs`) | 37446319529 / 112211924351 | 16/17. Kasus: 0/0; race 9/9; HTTP 2/2; browser 5/6. `REWORK_SKU_PARTIAL_COMPLETE_REVERSE` INCOMPLETE di langkah pembatalan; diperbaiki di d82fa583. |
| **d82fa583** | Job browser T3 | 37447893656 / 112217039805 | **Alur AT PASS 10/10** (`T3_PREP_BROWSER` PASS, `console_errors=0`, `candidate_verified_after_flow=T3_PACKAGE_THROUGH_BF`). **`BE_BROWSER:REDYE_SKU_UNKNOWN_THEN_PRICE_MOBILE` PASS.** Paket browser lain 27 PASS / 4 INCOMPLETE (di luar lingkup, sama dengan sebelumnya). |
| **d82fa583** | Skenario auditor after | 37447896631 / 112217047294 | **17/17 PASS**, status `RUN_COMPLETE`, job sukses. Kasus: 0/0; race 9/9; HTTP 2/2; browser 6/6, termasuk `REWORK_SKU_PARTIAL_COMPLETE_REVERSE` dan `REDYE_SKU_UNKNOWN_THEN_PRICE_MOBILE`. |

Detail alur AT di 92f30e42, semua PASS:
- REAL_LOGIN_PAGE, ANONYMOUS_REFUSED, REAL_PASSWORD_BROWSER_LOGIN;
- AMBIGUOUS_REFUSED_0, LOST_REPLY_RELOAD_EXACT_REPLAY, EXACT_BRAND_STOCK_HPP_0, LINKED_INVERSE_0;
- AMBIGUOUS_REFUSED_1, EXACT_BRAND_STOCK_HPP_1, LINKED_INVERSE_1.

Hasilnya: `console_errors=0` dan `candidate_verified_after_flow=T3_PACKAGE_THROUGH_BF`.

## Yang tidak diubah

- Tidak ada perubahan pada:
  - produk: `src/`, writer Native, SQL;
  - `supabase/`;
  - ACL, timeout, dan budget kasus;
  - `main` dan hosted.
- Tidak ada assertion bisnis yang dihapus, dan tidak ada hasil gagal yang dilabel ulang.
- **Di luar lingkup, tidak disentuh:**
  - Di job browser T3, `READINESS_BROWSER:{DESKTOP,MOBILE}_NATIVE_POLICY_STATES_FINANCE_NOTE` gagal karena ada dua `role=alert`.
  - `BF_BROWSER:SALES_MANUAL_13_{DESKTOP,MOBILE}` gagal karena input `.biz-size-entry` berjumlah 0.
  - Keduanya item PRE lain yang dipegang GPT.
  - Selector basi `.cbsr-search` yang sama juga masih ada di `scripts/cp6_final_gap_ui.mjs:92`.
- **Run yang dibatalkan:** run push P08 (37446319535) dan P18 (37446319692) di 92f30e42 dibatalkan writer. Keduanya terpicu oleh fast-forward ke head GPT dan bukan bagian permintaan ini; tujuannya agar runner fokus ke dua suite di atas.
