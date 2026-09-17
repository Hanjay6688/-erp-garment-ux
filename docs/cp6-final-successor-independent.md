# Audit independen successor CP6 — sedang berjalan

Satu writer audit; produk belum diubah. `production_go:false`; CP7 belum dimulai.

Checkpoint masuk `1ee47b02192a6fb1ccf85c1c12bd5a68a12d4542`, tree
`9a520ab5fe2e0fe87375268c1d437912d73455b7`, parent
`2c9465994b3827bc3db82af52753dc5eb80df141`. Snapshot runtime writer tersebut
ber-tree `3fe4f342ea41c987c4a693339d5590db3b486f2a`.
Produk terakhir berubah pada `47671d9ba2cfb8d02658388adb364b2ae6b89e8d`, tree
`46f4f605444c72dc32282025b859ab66375178b3`; frontend nominal dan backend AJ.
SHA alat audit dibedakan dari SHA produk ini. Byte produk src/SQL/package tetap
sama; pemeriksaan runtime memverifikasi 533 fungsi dan 157 objek relasi.

## Rekonsiliasi masuk

- Native35174491617: FAILURE. Business mewarisi12 pengamatan tanggal HOLD;
  bukan PASS seluruh CP6. CodeQL35174491674: keempat job SUCCESS.
- Artifact10477389132:53577549 byte,293 entry unik, CRC valid. SHA256 byte lokal
  `146dc8de156bfbd18060b40d3a5b7af0d33a99e19c95f371ee2ca36dd5f11ee0` cocok.
- Fresh230 pada47671d9:179 PASS,39 CONTROL_PASS,12 DATE_POLICY_REVIEW_REQUIRED,
  0 incomplete. Case ID unik230, bukan230 alur bisnis biasa yang semuanya PASS.
- Artifact10477942082:53007482 byte,292 entry, CRC valid; SHA256
  `9d2c1906c3f6bd5c11e46d7baa9740d4eb11d260f6d63c8b88d09bb4950c6abd` cocok.
- Attempt pertama berhenti pada fixture tombol reject setelah claim sudah
  REJECTED. Rework setelahnya incomplete. Follow-up membetulkan fixture,
  menjalankan12 rework fresh dan mengikat ulang218 hasil lain ke47671d9.
- Matrix460 adalah23 generasi ×5 operasi ×4 jadwal maintenance/rollback.
  Tetap REUSED_EVIDENCE historis, bukan460 alur bisnis fresh pada AJ.

## Bukti tambahan yang harus selesai

Empat alur recovery → draft sale → posting → invoice material final → recost
FG/COGS → reversal invoice → reversal sale → reversal recovery. Angka dasar:
10 unit material×10,10 cucian×7; percobaan gagal berbayar menambah70 bila ada.
Hanya2 barang recovery tersisa sebelum penjualan1. Invoice final10×12.75
menambah27.50 ke biaya sumber. Oracle ditulis dari angka ini.

Tiga batch import campuran memeriksa error per baris, larangan prepare,
koreksi draft, preview ulang, replay prepare dan posting20 unit bernilai25.
Dua pengamatan tanggal membaca confidence pada tanggal historis yang sama,
bukan menempelkan confidence hari ini pada laporan lama.
Pemeriksaan parser nominal34 kasus adalah tes parser saja; UI/HTTP dibuktikan
terpisah oleh alur layanan asli dan review bukti writer.

Belum ada hasil native tambahan pada saat checkpoint rencana ini dibuat.
Native memakai temporary schema USAGE hanya di transaksi fixture; pengembalian
ACL/data/catalog diperiksa. Bukti native tersebut tidak menggantikan role HTTP.

## Aturan tanggal dan CSV yang tetap terbuka

Master owner AD section16.1–16.5 memisahkan tanggal fisik, ekonomi, sistem,
dan buku; melarang READY sebelum recalc/integrity lengkap; late facts di periode
tertutup memakai controlled adjustment di periode terbuka. Tidak ditemukan
pilihan eksplisit tanggal buku untuk seluruh keluarga koreksi pada periode
terbuka. Jangan memilih kebijakan baru atau mengubah HOLD menjadi PASS diam-diam.

Master section21.1 mewajibkan preview, row errors, totals, idempotency dan
recovery import. Parser/upload CSV dan caller aplikasi belum ditemukan; masih
BELUM TERUJI. Section CP7 dan21.2 menempatkan penyambungan UI sales/payroll/
finance serta full dummy flow pada CP7. Penempatan UI CSV belum eksplisit;
belum diberi N/A atau dipindah ke CP7.

Prinsip: “VENI. VIDI. VICI. ERP. — I CONQUERED ERP.”
“Reliable data adalah dewa.”
“Keuangan—termasuk laporan—stok, dan HPP adalah raja.”
