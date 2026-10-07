# Bantuan penulis: gunakan kembali timeline tanpa tambahan supply

Owner meminta bantuan memperingan pekerjaan Claude pada 7 Oktober 2026.
Ini kontribusi implementasi di cabang terpisah, bukan penerimaan audit independen.
Claude tetap integrator; `cp7/integration`, `main`, hosted dan konfigurasi owner tidak diubah oleh bantuan ini.

## Perubahan

Basis persis: `aa638356e13aeffe7b2a2aa96f17dbe19676db1f` pada cabang Claude.
Satu fungsi produk berubah: `cp7_netting_native.build` di `scripts/cp7-src/planning/netting.sql`.

Build menghitung timeline tanpa supply untuk menentukan `risk_at`, lalu menghitungnya kembali saat menyusun baris akhir. Bila tidak ada directed/candidate edge, keenam argumen panggilan kedua identik dengan panggilan pertama. Fungsi timeline bersifat immutable.

Patch menahan hasil pertama dalam array lokal. Peta target menunjuk ordinal array; guard target duplikat yang lama tetap berjalan sebelum pembacaan array. Baris dengan supply tetap memanggil timeline asli dengan seluruh edge. Hasil UNKNOWN juga dipertahankan persis. Target yang tidak dapat direncanakan tetap memakai alasan UNKNOWN yang lama.

Tidak ada perubahan rumus, public RPC, signature, pemilik fungsi, ACL, timeout, batas data, source fingerprint, format keluaran, atau cache lintas transaksi. Semua fungsi selain build diperiksa byte-identik oleh probe. Tidak ada perubahan pada CP6 ataupun kernel `cp7_baseline.net/timeline`.

## Bukti dan batas

- Probe mandiri bantuan: `scripts/cp7_astra_timeline_reuse_probe.mjs`.
- Pembanding hasil: sumber aa638356 persis, dipasang berdampingan dengan kandidat; seluruh `jsonb::text` dan SQLSTATE + pesan penolakan pertama harus identik.
- Fixture: generator penulis yang sudah ada, ditambah kontrol Astra untuk target berbeda tanpa supply dan supply campuran. Producer jadwal di-stub seperti fixture lama; netting dan kernel SQL nyata. Ini bukan uji aplikasi/Auth/browser.
- Kasus lengkap yang dideklarasikan: 571; mode plan auto/custom/generic; dua mutasi wajib tertangkap (mengabaikan supply, memakai timeline target pertama untuk semua target).
- Benchmark: 100/300/1000 target, 0/100 posisi, horizon 10 hari. Kedua versi dipanaskan dalam satu sesi, kemudian A/B/B/A; hash dan panjang seluruh hasil harus sama. Waktu kernel bukan SLA aplikasi.
- Uji awal lokal PGlite PG18.3: 145/145 cocok, 16 jenis penolakan, 26 supply events, dua mutasi tertangkap. Percobaan pertama berhenti sebelum kasus pertama karena ekstensi pgcrypto belum dimuat; wrapper lokal kemudian memuat ekstensi itu. Runtime produk/probe tidak dilonggarkan. Bukti PostgreSQL Native masih PENDING sampai run cabang selesai.
- Biaya tambahan: array timeline dipertahankan selama satu pemanggilan build. Memori puncak backend belum diukur; tidak ada klaim bahwa ini menyelesaikan beban memori/sumber/transfer aplikasi.

## Pengambilan oleh integrator

1. Bandingkan diff terhadap head Claude terbaru; jangan timpa perubahan yang sedang berjalan.
2. Ambil perubahan satu fungsi beserta probe bila bukti Native pada commit kandidat lulus.
3. Jalankan regresi Native analisis, netting, attention dan P19 aplikasi penuh di head hasil penggabungan. Bukti kernel tidak menutup gerbang tersebut.
4. Periksa kembali `financial_source`, transfer/manifest, dan batas 1.000 produk. Optimasi ini tidak mengubah ketiganya dan tidak membuktikan 5.000 target dapat diproses aplikasi.

`independent_acceptance=false`, `full_P19_acceptance=false`, `production_go=false`.
Karena Astra membuat patch ini, penerimaan independen patch harus dilakukan peserta lain.
