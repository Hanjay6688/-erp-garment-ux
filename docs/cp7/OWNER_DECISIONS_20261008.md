# Keputusan owner 8 Okt 2026 — catatan writer

Sumber: pesan owner di chat writer Claude, 8 Okt 2026. Kalimat owner dikutip apa adanya; kolom "arti untuk
pekerjaan" adalah catatan writer dan tidak menambah aturan. Keputusan yang sudah disahkan sebelumnya
(GBD-03 opsi 1, lima keputusan D11, arahan 7 Okt) tidak dibuka ulang.

**Pembekuan.** Owner: "Bekukan kandidat audit sekarang. Pengembangan kebijakan dan fitur tambahan di atas dicatat
sebagai kelanjutan terpisah, supaya paket yang sedang diaudit tidak terus berubah." Maka butir 3–9 di bawah
**tidak** diimplementasikan di kandidat audit; semuanya masuk `CONTINUATION_AFTER_FREEZE_20261008.md`.
Kandidat audit: `audit-candidate/final-20261008/`.

| # | Keputusan owner (kutipan) | Arti untuk pekerjaan |
|---|---|---|
| Integrasi | "Boleh push ke `cp7/integration`, tanpa force push dan tanpa menyentuh `main`. Catat SHA akhirnya dan pastikan bukti CI sesuai kode yang digabung." | Fast-forward `cp7/integration` ke SHA kandidat; seluruh workflow yang terpicu dan 15 workflow kualifikasi dijalankan pada SHA itu; receipt di `audit-candidate/final-20261008/FREEZE_RECEIPT.json`. |
| 1 P20 | "siapkan paket final untuk auditor di sesi terpisah. Audit harus memeriksa sendiri seluruh cakupan, bukan cuma mengulang temuan penulis. Penulis tetap boleh membantu reproduksi dan perbaikan, tetapi tidak memberi penerimaan independen." | `audit-candidate/final-20261008/AUDITOR_START_P20.md`. Writer tidak pernah menulis `independent_acceptance=true`. |
| 2 P21 | "tunggu audit diterima dan izin pemasangan terpisah. Gladi yang hijau tetap dicatat sebagai gladi. `production_go:false`." | Gladi `37716123319` tetap berlabel latihan; `installed_P21_acceptance=false`, `production_go=false`. |
| 3 PL-5 B | "setuju paket usulan histori: 180 hari, minimal 5 grup selesai dan 200 PCS potong, per produk+size lalu fallback model yang sama, batas bawah Wilson satu sisi 90%. Jangan lintas model atau menganggap yield 100%. Bila data kurang, gunakan A yang ditinjau atau UNKNOWN. Simpan keputusan sebagai kebijakan berversi dan uji sebelum diaktifkan." | Parameter usulan `PL5_YIELD_POLICY_PROPOSAL_20261007.md` disetujui. Implementasi (kebijakan berversi + `history_yield` + kasus Native) adalah kelanjutan; sampai lulus uji, sistem tetap `PENDING_POLICY_VALUE`. |
| 4 Retensi | "hasil analisis sementara disimpan 7 hari setelah selesai atau dibatalkan. Jangan hapus job yang belum selesai, dokumen transaksi, atau bukti yang diperlukan audit. Hasil kedaluwarsa harus diberi keterangan jelas." | Nilai 7 hari menggantikan `PENDING_POLICY_VALUE` retensi staged. Implementasi (jadwal purge + label kedaluwarsa) adalah kelanjutan. |
| 5 Prioritas 5.000 | "rencana/rekomendasi produksi → Business Report → pengingat → AI. Setiap fitur baru harus memakai hasil lengkap yang sudah diverifikasi." | Urutan kelanjutan downstream staged. Halaman tidak pernah dipakai sebagai hasil lengkap. |
| 6 Penjalan | "arah akhirnya berjalan di server, supaya tetap lanjut saat halaman ditutup. Membuka ulang harus melanjutkan job yang sama, bukan menghitung ulang atau menggandakan pekerjaan." | Driver server (pg_cron) adalah kelanjutan; kontrak UUID/job yang sama tetap. |
| 7 Capture | "Capture 4,4–4,6 detik: diterima sementara sebagai bagian pekerjaan latar belakang. Layar tetap responsif dan progresnya jelas. Optimalkan semaksimal mungkin; 3 detik sasaran, bukan alasan melonggarkan angka, hash, akses, atau batas 8 detik." | Pilihan capture ditutup sementara: diterima sebagai latar. Batas 8 dtk, hash dan akses tetap. |
| 8 PL-8 | "arahkan penjalan bukti otomatis di server. Bukti harus diperiksa terhadap versi sumber dan tidak boleh tetap dianggap berlaku setelah koreksi atau pembatalan." | Runner server PL-8 adalah kelanjutan; aturan versi sumber yang sudah ada tetap. |
| 9 CP6 | "keputusan yang sudah disahkan jangan ditanyakan ulang. Untuk delapan pengaturan nyata yang masih kosong, kirim tabel sederhana berisi pilihan, rekomendasi, dan transaksi yang tertahan. Akun serta kategori nyata jangan dikarang." | Tabel dikirim ke owner; nilai nyata tetap diisi owner. |
| PR #45 | "PR #45 tetap terpisah; jangan merge ke `main` dulu." | Tidak ada merge ke `main`. |

Status tetap: `independent_acceptance=false`, `installed_P21_acceptance=false`, `production_go=false`.
