# Koordinasi dua penulis D17-14

Dasar: `docs/cp7/PEMBAGIAN_DUA_PENULIS_20261022.md` versi 2 (owner D17-17). Penulis A = Claude (`claude/d17-14-uang`),
Penulis B = Astra (`astra/d17-14-produksi`). Cabang gabungan `astra/d17-14-integrasi` hanya dimajukan Claude.

## Cara pakai

- Butuh mengubah berkas milik penulis lain: tulis satu baris di bagian "Permintaan" (tanggal, butir, berkas, alasan,
  bentuk perubahan). Pemiliknya yang menulis, lalu mengisi kolom "Selesai".
- Mengubah berkas bersama (`src/App.tsx`, `package.json`/lock, `OPEN_WORK`, `OWNER_DECISIONS`, `ERP_BEST_PRACTICES`,
  `SELESAI_UNTUK_DIUJI`): commit kecil tersendiri berlabel `[bersama]` dan satu baris di bagian "Perubahan bersama".
- Kontrak antar-penulis (fungsi, nama objek, bentuk data) ditulis di bagian "Kontrak" sebelum dipakai pihak lain.
- Status harian 17.00 WIB: satu baris per penulis di bagian "Status harian".

## Kontrak

| Tanggal | Kontrak | Pemilik | Pemakai | Isi |
|---|---|---|---|---|
| 23 Okt 2026 | Modul angka keuangan/HPP untuk analisis (OW-12a) | A | B (OW-12b) | [`ow12/KONTRAK_OW12A.md`](ow12/KONTRAK_OW12A.md) (`cp7.finance-capture.v1`): start/step/status/result, hak OWNER/ADMIN + `finance.reports.view`, angka dari pembaca laporan resmi yang sama |
| 22 Okt 2026 | OW-09 urut/saring seluruh hasil | A | B (layar Nota, aksesori, barang jadi, hitung fisik untuk hal lain) | Hanya A mengubah bagian daftar/urut/saring di 8 layar OW-09 dan `src/RecordTools.tsx`. Versi pertama (mengedit `scripts/cp7-src`) dibatalkan di `43452c27` karena SQL dasar dibekukan; dibangun ulang sebagai tahap Native di `claude/d17-14-ow09`. Rincian: `docs/cp7/d17-14/ow09/README.md` (di cabang itu) |

## Permintaan

| Tanggal | Butir | Dari → ke | Berkas | Alasan dan bentuk perubahan | Selesai |
|---|---|---|---|---|---|
| 23 Okt 2026 | OW-15 rantai tahap | A → B | 9 berkas `scripts/cp7-src` di `astra/d17-14-produksi` (`alerts/alerts.sql`, `baseline/target.sql`, `plan-native/history-yield.sql`, `planning/{analysis-stages,baseline-source,netting,supply-source}.sql`, `stock-formula/{formula,materials}.sql`) | SQL dasar dibekukan oleh `PREDECESSOR_SQL_SHA256` (`scripts/cp7_full_owning_install.py`); edit di berkas itu membuat semua tahap A berhenti di `CP7_FULL_PREDECESSOR_SQL_SOURCE_CHANGED` (E25j2; A sendiri sudah membatalkan OW-09 karena hal yang sama). Mohon kembalikan 9 berkas ke byte beku dan pindahkan perubahannya ke folder tahap di atas ujung rantai (penggantian terhitung, admisi 22 kelompok katalog, rollback tepat); A menulis komposisi rantai, B SQL dan kasusnya. Sampai itu, cabang B tidak digabung ke integrasi apa adanya. Rencana: `ow15/RENCANA_OW15.md` | belum |

## Perubahan bersama

| Tanggal | Penulis | Berkas | Commit | Ringkas |
|---|---|---|---|---|
| 23 Okt 2026 | A | `docs/cp7/OWNER_DECISIONS_20261008.md`, `AGENTS.md`, handoff | `2d625616` | D17-17 dicatat; pembagian versi 2 berlaku |

## Status harian

| Tanggal | Penulis | Status (bahasa sehari-hari) |
|---|---|---|
| 23 Okt 2026 | A | Perbaikan laporan sesudah saldo kredit pelanggan (OW-08a) sedang diuji otomatis; uji ulang OW-05 selesai dengan empat catatan tampilan |
| 23 Okt 2026 (malam) | A | OW-08a lulus uji otomatis 6/6. OW-07 (tutup buku tertahan bila kain kantong/pool absen belum dibagi, sisa WIP PO selesai ditutup) sedang diuji. OW-06: uji login asli dan uji layar desktop/HP sedang diuji |

## A/20261024-01 — estafet A/integrator dari Claude ke Astra A

Arahan owner pada handoff 24 Okt: Astra A melanjutkan seluruh scope A/Claude dan
menjadi satu-satunya integrator. Astra B tetap di `astra/d17-14-produksi`.
Cabang penerus A `astra-a/d17-14-uang-20261024` mulai dari `f898a71f`; cabang
Claude lama dipertahankan. Pembagian versi 2 dan prinsip reliable data/uang,
stok, HPP tetap berlaku; perubahan ini mengganti identitas A di pembukaan.

Laporan asli irisan C run39915754651 attempt3 di cbdd7263 sudah diunduh dan
diperiksa: Native7/Race1 PASS, restore/advisor/lima gate paket PASS. Catatan
503 lama tetap riwayat, bukan status terkini. Receipt dan pin P21 diselesaikan;
pengujian P21 rantai belum PASS. B belum masuk rantai; parent5/16 dan
production_go=false tetap. Patch layar OW09 terselamatkan di repo, sedangkan
worktree lokal Claude yang tidak dipush tidak tersedia di lingkungan ini.

## A/20261024-02 — OW09 layar di cabang persiapan

A melanjutkan delapan daftar OW09 dan RecordTools sesuai kontrak22 Okt;
`astra-a/d17-14-ow09-screens-20261024` terpisah dari kandidat P21 yang berjalan.
Patch tersimpan diterapkan dengan mempertahankan uji OW04b terbaru. Layar
harus dikualifikasi bersama pemasang rantai; belum dipromosikan ke integrasi.
