# Arahan untuk Astra, 22 Okt 2026 (atas permintaan owner)

Owner (persis): "iya arahin dong, dia kayak orang bingung ya, lu boleh bantu uji juga". Arahan ini dari Claude atas nama
permintaan owner; keputusan owner yang tercatat (D13–D17-15) tetap berlaku dan tidak dibuka ulang.

## Kotak untuk owner (salin seluruh isi kotak ke sesi Astra)

````text
Astra, ini arahan owner untuk pekerjaan D17-14. Baca docs/cp7/handoff/ARAHAN_ASTRA_20261022.md di cabang
claude/new-session-deapao, lalu kerjakan urutannya:
1. Satukan semua cabang kerjamu ke SATU cabang integrasi: astra/d17-14-integrasi, dibuat dari
   codex/ow04-payment-binding-20261022, lalu merge (bukan rebase) tiga cabang yang belum masuk:
   codex/ow04-lifecycle-20261021 (1 commit), codex/ow04-payment-correction-20261022 (3 commit),
   codex/ow04-closure-queue-20261022 (1 commit). Jangan hapus cabang lama. Sesudah itu semua kerja hanya di cabang itu.
2. Berhenti menyimpan log mentah besar (.gz, .xz, .jsonl, log lengkap) di repo; repo publik dan sudah 56 MB bukti.
   Yang disimpan di repo: kuitansi ringkas (run/job, jumlah kasus, PASS/FAIL, hash) dan potongan log kegagalan
   pertama. Log lengkap tetap di artifact GitHub Actions. Pastikan tidak ada data produksi di bukti.
3. Tuntaskan OW-04 (retur transaksi lunas) sesuai daftar "selesai" di bagian 3 arahan ini, lalu tandai SELESAI dengan
   bukti. Hal di luar daftar itu ditulis sebagai "batas tersisa", jangan terus menambah lingkup.
4. Lalu OW-05 (koreksi mandor sesudah dijahit), OW-06 (satu transfer supplier ke banyak penerimaan), OW-07/08 (cek HPP
   dan koreksi uang lain), baru OW-09 dst. sesuai docs/cp7/OPEN_WORK_D17_14_20261020.md.
5. Status di OPEN_WORK maksimal dua kalimat bahasa sehari-hari + tautan README butir itu. Laporan ke owner sesuai
   CLAUDE.md: kalimat pertama apa yang beres dan belum, tanpa istilah teknis.
6. Setiap kali satu butir kamu nyatakan selesai, tulis satu baris di docs/cp7/d17-14/SELESAI_UNTUK_DIUJI.md
   (butir, commit, run/job). Claude akan menguji ulang secara terpisah atas izin owner; audit tetap oleh Fable/Sol.
Batas lama tetap berlaku (bagian 3 serah-terima HANDOFF_ASTRA_WRITER_D17_14_20261020.md).
````

## 1. Posisi yang diperiksa Claude (22 Okt, sekitar 06.00 UTC)

- Cabang terbaru `codex/ow04-payment-binding-20261022` (`1e8e1b0d`): 120 commit di atas serah-terima `5fd5d38e`; berisi
  `astra/d17-14-20261020` dan sebagian besar cabang `codex/ow04-*`. Tiga cabang punya commit yang belum masuk: 
  `codex/ow04-lifecycle-20261021` (1), `codex/ow04-payment-correction-20261022` (3, termasuk koreksi positif Native26
  PASS), `codex/ow04-closure-queue-20261022` (1). Total 14 cabang kerja.
- Kandidat audit `55c885d1` dan cabang `claude/new-session-deapao` tidak disentuh; `main` tidak berubah sejak 7 Okt.
  Tidak ada keputusan owner baru yang ditulis atas nama owner.
- Status yang diklaim: OW-01, OW-02, OW-03 SELESAI TERBUKTI; OW-04 BELUM SELESAI; OW-05..OW-16 belum mulai.
- Bukti di `docs/cp7/d17-14/`: 1.092 berkas, ±56 MB (317 `.gz`, 29 `.xz`, 22 `.jsonl`, 76 log) di repo publik.

## 2. Uji ulang terpisah oleh Claude (bukan audit)

| Yang diuji | Hasil |
|---|---|
| Run CI yang dirujuk OW-01..OW-04 | Diperiksa lewat API: WA Forward 39463501158 (`9b323f13`), P19 Transport 39420750772 (`2ad56e14`, percobaan ke-2), F05 Native Frozen 39423331714 (`878e0a9c`), OW04 Native 39564520538 (`e9287cf3`), OW04 HTTP 39570791319 dan browser 39570791212 (`91f71ce7`): semuanya `success` |
| OW-01 cakupan jenis | `collect_kinds` di `scripts/cp7-src/alerts/alerts.sql:521-522` kini memuat semua domain Pengingat: piutang/utang, saldo awal (OPENING_AR/AP), upah (PAYROLL_AP), nota aksesori (ACCESSORY_AP), laundry (LAUNDRY_AP, LAUNDRY_RECEIPT, LAUNDRY_OPENING_UNINVOICED), plus stok |
| Typecheck klien di `1e8e1b0d` | `tsc --noEmit` lulus |
| Seluruh uji klien vitest, `55c885d1` lawan `1e8e1b0d` (salinan lokal yang sama) | `55c885d1`: 1.816 lulus, 50 gagal (38 berkas); `1e8e1b0d`: 2.014 lulus, 50 gagal (38 berkas). Daftar berkas gagal identik (uji browser Playwright dan uji yang butuh database, tidak jalan di vitest lokal): tidak ada kegagalan baru; ±198 uji baru Astra lulus |

Belum diuji Claude: suite Native/race/HTTP/browser di CI dijalankan ulang secara terpisah, dan isi kode OW-04 baris per
baris. Akan dilakukan untuk setiap butir yang tercatat di `SELESAI_UNTUK_DIUJI.md`.

## 3. OW-04 retur transaksi lunas: daftar "selesai"

Dari kata-kata owner (D17-14 butir 4) dan daftar terbuka Astra sendiri:

1. Retur atas invoice lunas bisa dicatat; penggunanya memilih **uang kembali** atau **saldo kredit**, terlihat jelas di layar.
2. Uang kembali: kas/bank keluar tercatat sekali, penjaga kas per tanggal (D14-3, D15-1) tetap berlaku.
3. Saldo kredit: bisa dipakai ke invoice berikutnya; pemakaian bisa dibatalkan (consumer undo) tanpa saldo ganda.
4. Stok dan HPP barang yang kembali benar (termasuk retur saldo awal); jurnal seimbang.
5. Koreksi sesudahnya (positif/negatif, beberapa angkatan) konsisten; riwayat tetap; langkah membalik dokumen terkait
   ditampilkan jelas di layar.
6. Bukti: Native, race, HTTP Auth nyata, browser komputer dan HP; pasang/pulihkan (P21) di salinan uji.
7. Hal lain yang ditemukan di jalan dicatat sebagai "batas tersisa" dengan alasan, bukan memperpanjang OW-04.

## 4. Aturan kerja tambahan

- Satu cabang integrasi, commit kecil, satu checkpoint per setengah hari: satu baris status yang bisa dibaca owner.
- Kegagalan pertama tetap disimpan (ringkas), oracle tidak dilonggarkan, nilai kebijakan tidak dikarang.
- Pertanyaan ke owner hanya untuk nilai kebijakan atau pilihan bisnis yang belum ditetapkan, dalam bentuk ya/tidak.

