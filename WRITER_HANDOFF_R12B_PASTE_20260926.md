# Handoff auditor → writer (Opus), R12-B — keputusan owner 26 Sep + tanggapan atas laporanmu (§32, 2aee623) — TEMPEL KE WRITER
Satu versi gabungan (owner + GPT + Fable). Sumber: `OWNER_DECISIONS_CP6_DRAFT.md` (D08–D11, UI-01), `WRITER_HANDOFF_R12_FINAL_PASTE_20260926.md`, §32.9-mu.

## A. Keputusan owner yang baru (tertulis, apa adanya, di `OWNER_DECISIONS_CP6_DRAFT.md`)
1. **D09 — ACC-C12 = opsi (a).** Setiap item pending wajib rujukan sumber: lembar hitung + baris/item, atau lot sumber. Identitas sumber melekat pada barang dan tetap sama
   meski diajukan dengan kunci permintaan baru. Jangan mengunci seluruh lembar (satu lembar bisa banyak barang). Uji wajib: barang sama + kunci baru **ditolak**; replay kunci
   sama **tidak menambah** qty/jurnal; barang berbeda **tetap diterima**. Status ditutup setelah auditor memverifikasi.
2. **D10 — selisih invoice laundry (multi-ukuran).** Dalam layanan/tarif yang sama, biaya dan selisih dibagi menurut **jumlah potong terkait**. Bila vendor, proses, atau
   paket berbeda, **pisahkan menurut sumber tagihannya**; jangan diratakan ke seluruh barang. Tidak ada pembagian menurut tarif ukuran; owner tidak perlu ditanya lagi soal itu.
   Sesuaikan contoh dan kasus multi-ukuran (T24) dengan aturan ini; tulis klarifikasinya di dokumen keputusan (§9 addendum) dan di oracle untuk run baru; hasil lama tetap apa adanya.
3. **D11 — 13 nilai kebijakan (7 aksesori + 6 laundry).** Buat **satu tabel operasional**: nama kebijakan, kegunaan, pilihan yang tersedia, rekomendasi + alasan, transaksi yang
   tertahan selama belum diisi. Nilai tetap `PENDING_POLICY_VALUE` sampai owner memilih. Audit lanjut dengan konfigurasi uji yang **dicatat per run**.
4. **UI-01.** Tampilan belum mengikuti demo Cloudflare; diam bukan persetujuan. Halaman BC/BD dan berikutnya mengikuti tampilan **dan interaksi** demo. Dikerjakan belakangan
   sesuai urutan owner (sudah sesuai catatanmu di §32.9). Fungsi server tidak berubah.
5. **D08 tetap** beserta syarat ujinya. Jangan catat "izin sesi terbuka" sebelum benar-benar terjadi. **T6** tetap operator pada salinan yang diizinkan.

## B. F3/D08 — tanggapan atas laporan blokirmu
- Blokirnya ada di pengaman izin sesi Claude Code-mu, bukan aturan kontrak. Owner akan membuka izin edit untuk `src/accessoryIssue.ts` dan `src/laundryQcModel.ts` di
  sesimu; **jangan** dibuang dan **bukan** owner yang mengedit. Sampai izin itu nyata, statusnya "menunggu izin sesi" (jangan ditulis terbuka).
- Setelah izin ada: (1) `git status` + `git diff` dulu; jangan commit berdasarkan dugaan isi; (2) bila ada apa pun selain dua baris regex (sisa komentar), kembalikan ke HEAD
  dan terapkan ulang bersih mengikuti pola `src/accessoryService.ts:58`; UUID yang bentuknya rusak tetap ditolak; (3) tulis di §32 bahwa tidak ada baris role/izin/RLS/grant
  yang berubah, dengan diff; (4) tes unit + browser Nota Ambil Aksesori dan Laundry/QC dengan mandor/model UUID kanonik non-RFC **tetap aktif** + kontrol v4; jangan
  menonaktifkan seed; (5) commit + catat head, hash skenario, run/job di §32. Kalau masih diblokir: satu laporan ringkas (aksi yang ditolak, alasan pengaman, persetujuan
  spesifik yang dibutuhkan), tanpa jalan memutar.

## C. Sinkronisasi dengan §32.9-mu — mana keputusan owner, mana verifikasi auditor
| Butir §32.9 | Status sekarang |
|---|---|
| Nilai 6 kebijakan laundry (+7 aksesori) | **Owner** — menunggu tabel D11 darimu, baru owner memilih |
| Representasi klaim laundry lama ALL-W05 (GBD-03) | **Owner, tetapi butuh bahan darimu**: susun 2 opsi berangka (mis. klaim = piutang ke vendor yang diselesaikan lewat potongan invoice berikutnya vs klaim = penyesuaian nilai FG/laundry dengan catatan), dengan efek ke buku dan ke laporan cutover. Belum diputuskan. |
| F3/D08 | **Owner: izin sesi** (dalam proses, belum nyata) → lalu writer + verifikasi auditor |
| Opsi ACC-C12 | **Diputuskan D09 (a)** → writer implementasi → verifikasi auditor |
| Arah D07 / rumus toleransi | **Tinggal verifikasi auditor.** D07 owner = "setel ulang ke tingkat dokumen"; rumus ≤ 0,01 per bahan × dokumen adalah spesifikasi teknis auditor yang kamu pakai. Auditor uji ulang (5 jalur `xaudit_12_f1f2` harus diam; kontrol negatif harus bunyi). Owner tidak perlu memutuskan angka, kecuali ingin toleransi lain. |
| Selisih invoice multi-ukuran | **Diputuskan D10** → writer sesuaikan T24 + oracle → verifikasi auditor |
| Inventaris ID cutover (operator) | tetap tugas **operator**, baca-saja; menentukan P3/P2 F3 |
| L8 substitusi guard; pembanding rollback BC+BD; GBD-01/02; `STALE_F2` bersyarat | **Auditor** (masuk daftar audit BD) |
| UI mengikuti demo Cloudflare | **Owner sudah menegaskan (UI-01)**; dikerjakan belakangan |
| BE, uji gabungan 75+22 | writer berikutnya |

## D. Dua permintaan kecil yang tertinggal
- Konfirmasi dari log nama kasus INCOMPLETE di T2 run 36208946534 (dugaanmu `ACCESSORY_CONNECTED_ZERO` yang sudah digantikan).
- Audit BD dimulai auditor pada commit yang dipin (§32, 2aee623; produk vs alat sesuai §32.6). Pekerjaan yang tidak bergantung keputusan di atas lanjut. CP6 tetap HOLD.
