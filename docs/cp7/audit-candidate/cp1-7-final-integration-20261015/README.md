# Paket audit akhir CP1–CP7: sambungan antar tahap dan layar (D14-13)

**Status: DRAF, belum untuk dikirim.** Owner mengirim paket ini ke auditor hanya sesudah penulis menulis
"SIAP DIKIRIM" di baris ini, bersama commit kandidat final. Urutannya ada di bagian "Sebelum dikirim".

Keputusan owner D14-13 (15 Okt 2026, `docs/cp7/OWNER_DECISIONS_20261008.md`): satu audit akhir CP1–7 sesudah uji ulang
r1 selesai, dengan dua fokus:

1. **Sambungan antar tahap dari awal sampai akhir:** pembelian → stok → potong → jahit → laundry → QC → barang jadi →
   jual → kas, hutang, piutang, buku besar.
2. **Setiap layar UX demo dibandingkan dengan layar tersambungnya:** apakah datanya asli dan perilakunya sama.

Audit penuh CP1–7 sebelumnya (`../cp1-7-full-20261014/`, kandidat `0b7049d9`) sudah memasukkan sambungan antar tahap
(SKN-22) sebagai fokus. Yang baru di audit akhir ini: fokus 2 (layar demo vs tersambung, termasuk mode Enteng), dan
pemeriksaan ulang sambungan sesudah semua perbaikan r1 (D14-2..D14-12).

| Berkas | Isi |
|---|---|
| `README.md` | Status, cakupan, langkah sebelum dikirim, butir yang sudah diketahui |
| `CHAIN_MAP.md` | Fokus 1: 13 sambungan utama + 7 rantai samping, mekanisme, uji yang ada, celah |
| `SCREEN_MAP.md` | Fokus 2: 48 menu × 3 mode aplikasi, uji browser per layar, celah |
| `GAPS_D14_14.md` | Tiga celah yang dikerjakan sebelum audit akhir (D14-14): G1 jahit selesai + upah, G2 selesai PO + HPP final, G3 workflow basi |
| `HANDOFF_FABLE.md`, `HANDOFF_ASTRA.md`, `HANDOFF_SOL.md` | Kotak yang disalin owner ke sesi masing-masing auditor |

## Kandidat

Sementara: `66baa8e8ddf601625bc831c7256f38eec883b496` (kandidat uji ulang r1, `../cp1-7-fix-r1-20261015/`, 25/25
workflow dan 69/69 job pada percobaan pertama). Bila uji
ulang r1 atau langkah di bawah mengubah kode, kandidat diganti dan kotak handoff diperbarui sebelum dikirim.

## Sebelum dikirim (urutan)

*Diubah 15 Okt 2026 oleh D14-16:* uji ulang r1 **tidak** dikirim terpisah. Sesudah celah D14-14 selesai dan
dikualifikasi, penulis menyiapkan satu paket gabungan (uji ulang r1 + audit akhir) pada satu kandidat. Langkah 1 di
bawah dibaca sebagai bagian dari paket gabungan itu; langkah 2 dan 3 sudah dikerjakan (`GAPS_D14_14.md`).

1. Uji ulang r1 oleh Fable, Astra dan Sol selesai; temuannya ditutup atau diputuskan owner.
2. **Workflow basi dijalankan ulang** pada kandidat (`CHAIN_MAP.md` §3 butir 3): sekitar 60 workflow `cp7-*` hanya
   berjalan saat push ke `cp7/integration` dan terakhir berjalan 8 Okt, sebelum penjaga D14-2, D14-3 dan FIN02.
   Penulis menambahkan tombol jalankan manual dan cabang penulis ke pemicunya, menjalankannya, dan membetulkan data uji
   yang ditolak penjaga baru tanpa melonggarkan oracle atau penjaga; log gagal disimpan.
3. Celah yang sudah terbukti dari kode (di bawah) dikerjakan atau diserahkan apa adanya, sesuai keputusan owner.
4. Kualifikasi satu commit, `CI_RECEIPT.json` untuk kandidat final, lalu kotak handoff diperbarui.

## Butir yang sudah diketahui penulis (bukan temuan auditor; boleh diuji)

Terbukti dari kode:

- **Jahit selesai tidak bisa dicatat dari layar tersambung** (`CHAIN_MAP.md` §3 butir 1, `SCREEN_MAP.md` butir 11).
  Akibatnya barang tidak bisa dikirim dari jahit ke laundry lewat aplikasi; semua uji rantai membuat catatan jahit
  lewat SQL.
- **Upah borongan dan HPP final** (`erp.post_work_completion`, `erp.finish_production_order`) tidak punya jalan dari
  aplikasi (`CHAIN_MAP.md` §3 butir 2).
- **Mode Enteng menampilkan data contoh di 23 dari 48 menu**, termasuk semua menu Penjualan, 6 menu Keuangan dan
  Absensi (`SCREEN_MAP.md` §1–2). Layar tersambungnya ada, tetapi hanya dibuka di mode uji sekali pakai; rencana
  menyalakannya di Enteng belum tertulis di mana pun.
- **Data induk harian** (pelanggan, supplier, mandor, lokasi, master kain/aksesori) tidak punya layar tersambung
  (`SCREEN_MAP.md` butir 10).
- Workflow basi sejak 8 Okt (di atas).
- Dua dokumen penulis yang salah sudah diberi koreksi bertanggal: `docs/cp7/RETIRED_CP6_SALES_MANUAL_13.md` (layar
  simulasi penjualan memang tampil di mode Enteng) dan `docs/cp7/p18/P18_FULL_CYCLE.md` (kas tidak lagi minus sejak
  D14-3).

Butir terbuka lama yang tetap berlaku: `CHAIN_MAP.md` §4.

## Larangan (sama dengan putaran sebelumnya)

Tidak boleh dimutasi: main, deployment Cloudflare, Supabase hosted Enteng (`siimvrusnzxexizpyoib`), legacy
ERP-Garment (`vlxdhpkjeevubjxexnfo`, read-only), production. Mode Enteng diuji dengan build lokal + backend sekali pakai
atau HTTP tiruan, bukan ke hosted. Tidak meminta password, token atau kunci di chat. `production_go:false`.

## Hasil yang diminta dari tiap auditor

Laporan format Pro Max §9 di cabang audit baru, dikunci dengan commit sebelum membaca laporan auditor lain di putaran
ini. Isinya: vonis per sambungan B1–B13 dan S1–S7 (TERSAMBUNG DAN TERUJI / TERSAMBUNG TANPA UJI APLIKASI / TIDAK
TERSAMBUNG), vonis per menu (SAMA / BEDA / TIDAK ADA LAYAR TERSAMBUNG) untuk mode `DISPOSABLE_TEST` dan mode Enteng,
daftar yang harus beres sebelum pemasangan ke Enteng, daftar "belum saya periksa", dan ringkasan owner ≤ 10 kalimat
dalam bahasa sehari-hari.
