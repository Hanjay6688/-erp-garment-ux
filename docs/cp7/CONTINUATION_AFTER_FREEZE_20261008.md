# Kelanjutan sesudah pembekuan kandidat audit — 8 Okt 2026

Owner: "Pengembangan kebijakan dan fitur tambahan di atas dicatat sebagai kelanjutan terpisah, supaya paket yang
sedang diaudit tidak terus berubah." Pekerjaan di bawah **tidak** masuk kandidat audit
`audit-candidate/final-20261008/`. Setiap butir dikerjakan di atas kandidat itu, diuji sendiri, lalu diajukan
sebagai kandidat lanjutan dengan buktinya sendiri. Keputusan sumber: `OWNER_DECISIONS_20261008.md`.

| Urut | Kelanjutan | Yang harus dibuktikan sebelum aktif |
|---|---|---|
| K1 | PL-5 B: kebijakan yield histori berversi (180 hari, ≥5 grup selesai, ≥200 PCS potong, produk+size lalu model yang sama, Wilson satu sisi 90%) | Catatan kebijakan bertanda tangan owner (versi, alasan, waktu); `history_yield` membaca bukti grup habis PL-8 yang masih berlaku; kasus Native sampel cukup/kurang, batas bawah tepat, tidak lintas model, tidak 100%, bukti yang dibatalkan koreksi/pembatalan/backdate keluar dari histori; fallback A ditinjau/UNKNOWN. |
| K2 | Retensi staged 7 hari sesudah selesai/dibatalkan | Purge hanya job DONE/FAILED/dibatalkan yang lewat 7 hari; job yang belum selesai, dokumen transaksi dan bukti audit tidak tersentuh; hasil kedaluwarsa diberi keterangan jelas di UI dan reader menolaknya dengan kode jujur. |
| K3 | Hemat penyimpanan hasil 5.000 target | Ukur ukuran disk nyata satu run (header/halaman/intermediate setelah kompresi TOAST); hapus intermediate segera setelah halaman terverifikasi; tanpa mengubah isi, hash atau halaman yang dibaca pengguna. |
| K4 | Penjalan server (pg_cron) untuk job staged | Job tetap lanjut saat halaman ditutup; buka ulang melanjutkan job/UUID yang sama; tiap unit `statement_timeout` 8 dtk; hak aktor diperiksa ulang tiap unit tanpa `auth.uid()`; tidak ada hitung ganda. |
| K5 | Downstream staged sesuai urutan owner: rencana/rekomendasi produksi → Business Report → pengingat → AI | Setiap fitur memakai hasil lengkap terverifikasi (header + semua halaman + identity_hash), bukan satu halaman. |
| K6 | Penjalan bukti PL-8 otomatis di server | Bukti diperiksa terhadap versi sumber; tidak berlaku lagi setelah koreksi/pembatalan. |
| K7 | Optimasi capture, hitung baru dan "Cek sumber" 5.000 target | Capture diterima sementara 4,4–4,6 dtk sebagai latar; "Cek sumber" 5.000 target dekat 8 dtk dan pernah ditolak di runner lebih lambat (`evidence/freeze-20261008/04`); optimasi tanpa melonggarkan angka, hash, akses atau batas 8 dtk; 3 dtk tetap sasaran, tidak ditandai tercapai sebelum terukur. |
| K7a (dikerjakan 8 Okt, sesudah dua kegagalan p19-scale5 di `a96def4d`) | Pembacaan sumber histori (`history_source_within`) | Tiga perubahan berhasil-sama: tanggal produk pertama per root dihitung sekali (sebelumnya satu pindai tabel produk penuh per produk, O(P²)); daftar fakta dirakit sekali (sebelumnya dua kali); hitung jurnal penjualan per penjualan dihitung sekali. Ukur lokal (data sintetis 5.000 produk, 15.000 gerak stok, 9.996 baris penjualan; bukan bukti CI): output sama persis (jsonb dan md5 teks, selain `captured_at`), histori 4,6 → 1,1 dtk, seluruh sumber analisis 6,0 → 2,9 dtk. Bukti CI di p19-scale5 berikutnya. |
| K8 | Konfigurasi nyata CP6 | Diisi owner dari tabel pilihan/rekomendasi/transaksi tertahan; akun dan kategori nyata tidak dikarang. |
| K9 | Hosting jangka panjang | Keputusan owner (biaya, backup, batas penyimpanan); tidak ada perubahan hosted tanpa izin terpisah. |

Tetap: `independent_acceptance=false`, `installed_P21_acceptance=false`, `production_go=false`.
