# Paket gabungan CP1–CP7: uji ulang r1 + audit akhir (D14-13, D14-16)

**Status: SIAP DIKIRIM** pada kandidat `dfab13bf62398a69a02bf6221c06d29075e5e40b` (15 Okt 2026). Owner yang mengirim: salin kotak di `HANDOFF_FABLE.md`,
`HANDOFF_ASTRA.md` dan `HANDOFF_SOL.md` ke sesi masing-masing auditor. Penulis tidak mengirim apa pun.

Keputusan owner D14-16 (15 Okt 2026, `docs/cp7/OWNER_DECISIONS_20261008.md`): uji ulang r1 tidak dikirim terpisah;
sesudah celah D14-14 selesai, satu paket gabungan pada satu kandidat. Paket ini berisi dua bagian:

- **A. Uji ulang r1:** perbaikan penulis atas temuan audit penuh CP1–CP7 `0b7049d9` (Fable, Astra, Sol). Klaim per
  temuan dan bukti: `../cp1-7-fix-r1-20261015/README.md` dan `FINDINGS_TRACKER.md`.
- **B. Audit akhir (D14-13):** (1) sambungan antar tahap dari awal sampai akhir: pembelian → stok → potong → jahit →
  laundry → QC → barang jadi → jual → kas, hutang, piutang, buku besar; (2) setiap layar UX demo dibandingkan dengan
  layar tersambungnya: apakah datanya asli dan perilakunya sama.

| Berkas | Isi |
|---|---|
| `README.md` | Status, kandidat, cakupan, butir yang sudah diketahui |
| `HANDOFF_FABLE.md`, `HANDOFF_ASTRA.md`, `HANDOFF_SOL.md` | Kotak yang disalin owner ke sesi masing-masing auditor (bagian A + B) |
| `CI_RECEIPT.json` | Semua workflow dan job pada kandidat (dibuat `scripts/cp7_ci_receipt.py`) |
| `GAPS_D14_14.md` | Tiga celah yang dikerjakan sebelum audit akhir (D14-14): G1 jahit selesai + upah, G2 selesai PO + HPP final, G3 workflow basi; arsip CI kedaluwarsa (D14-17) |
| `CHAIN_MAP.md` | Fokus 1: 13 sambungan utama + 7 rantai samping, mekanisme, uji yang ada, celah |
| `SCREEN_MAP.md` | Fokus 2: 48 menu × 3 mode aplikasi, uji browser per layar, celah |
| `WRITER_HANDOFF.md` | Serah-terima untuk penulis cadangan (bukan untuk auditor) |

## Kandidat

- **Commit `dfab13bf62398a69a02bf6221c06d29075e5e40b`**, tree `886f83312958b53781a450a4ea2a8fb2147b3be3`, cabang `claude/new-session-deapao`. Commit sesudahnya hanya dokumen
  (`git diff --name-only dfab13bf <head cabang>` semuanya di bawah `docs/`).
- Kualifikasi satu commit (`CI_RECEIPT.json`, 80 run workflow, 131 job): semua workflow kualifikasi r1 (25),
  51 workflow `cp7-*` yang dijalankan ulang (G3), ditambah `cp7-group-end-diagnosis` dan
  `cp7-supabase-restore-drill`. Semua workflow hijau pada commit ini, dengan tiga catatan yang tidak disembunyikan:
  - `CP6 Candidate CodeQL (T3)`: run push 38738714861 dibatalkan oleh aturan antrean workflow itu
    (`cancel-in-progress`) karena penulis juga menjalankannya manual; run manual 38738889358 hijau.
  - `CP7 Offsite Backup` run 38739002359 hijau pada percobaan kedua. Percobaan pertama gagal menyalakan database uji
    sebelum satu kasus pun berjalan: port 54324 sudah dipakai di mesin GitHub (4 kali dicoba). Kemungkinan besar
    bentrok dengan port sementara mesin (rentang 32768–60999); belum dibuktikan. Log percobaan pertama tersimpan di
    run yang sama. Workflow ini tidak berubah sejak `6cf2b7f9`, tempat ia hijau pada percobaan pertama.
  - `CP6 T3 Release Package` berjalan dua kali pada commit ini (manual di cabang kerja dan push); keduanya hijau.
- `supabase/` tidak berubah sejak `0b7049d9`. Yang berubah sejak kandidat r1 `66baa8e8` (yang tidak pernah dikirim):
  G1, G2, G3 dan D14-17 (`GAPS_D14_14.md`; `git diff 66baa8e8 dfab13bf -- src scripts supabase tests .github`).
- Kualifikasi sebelumnya pada `6cf2b7f9`: 77 dari 78 hijau; `CP6 T3 Release Package` bagian browser berhenti karena
  arsip CI kedaluwarsa (run 38727609578, log disimpan). Perbaikannya hanya di workflow itu (`GAPS_D14_14.md` §3a).

## Butir yang sudah diketahui penulis (bukan temuan auditor; boleh diuji)

- **Jahit selesai, upah borongan dan HPP final** sekarang punya jalan dari aplikasi (G1, G2). Batas: potongan dengan
  tarif per SKU/ukuran (wave BF) ditolak `WAVE_SKU_RATES`; PO yang sudah selesai tidak bisa dibuka lagi (tidak ada
  pembalik Native); tanggal selesai PO selalu hari ini WIB.
- **Mode Enteng menampilkan data contoh di 23 dari 48 menu**, termasuk semua menu Penjualan, 6 menu Keuangan dan
  Absensi (`SCREEN_MAP.md` §1–2). Layar tersambungnya ada, tetapi hanya dibuka di mode uji sekali pakai; rencana
  menyalakannya di Enteng belum tertulis di mana pun.
- **Data induk harian** (pelanggan, supplier, mandor, lokasi, master kain/aksesori) tidak punya layar tersambung
  (`SCREEN_MAP.md` butir 10).
- **FABLE-012:** 82 penulis `erp` masih bisa dieksekusi peran `authenticated` lewat SQL; tidak terjangkau lewat Data
  API. Pencabutan ditunda ke CP7C (D14-9).
- **Arsip CI:** daftar tabel "sebelum U" diambil ulang di setiap run (D14-17); tidak bisa lagi dibuktikan sama persis
  dengan daftar 15 Sep. 37 workflow CP6 lama yang memanggil bootstrap dari checkout kandidat beku tidak bisa berjalan.
  Dua arsip F05 (`11139828865`, `11141076740`) habis 31 Okt; salinannya ada di artifact `11967162735`.
- Dua dokumen penulis yang salah sudah diberi koreksi bertanggal: `docs/cp7/RETIRED_CP6_SALES_MANUAL_13.md` dan
  `docs/cp7/p18/P18_FULL_CYCLE.md`.

Butir terbuka lama yang tetap berlaku: `CHAIN_MAP.md` §4.

## Larangan (sama dengan putaran sebelumnya)

Tidak boleh dimutasi: main, deployment Cloudflare, Supabase hosted Enteng (`siimvrusnzxexizpyoib`), legacy
ERP-Garment (`vlxdhpkjeevubjxexnfo`, read-only), production. Mode Enteng diuji dengan build lokal + backend sekali pakai
atau HTTP tiruan, bukan ke hosted. Tidak meminta password, token atau kunci di chat. `production_go:false`.

## Hasil yang diminta dari tiap auditor

Satu cabang audit baru per auditor, dua laporan yang dikunci dengan commit sebelum membaca laporan auditor lain di
putaran ini: `RETEST_<NAMA>_dfab13bf.md` (bagian A, per temuan: DITUTUP / MASIH TERBUKA / BARU) dan `FINAL_<NAMA>.md` +
`FINDINGS.json` (bagian B: vonis per sambungan B1–B13 dan S1–S7, vonis per menu untuk mode `DISPOSABLE_TEST` dan mode
Enteng, daftar yang harus beres sebelum pemasangan ke Enteng, daftar "belum saya periksa"), ditambah ringkasan owner
≤ 10 kalimat dalam bahasa sehari-hari.
