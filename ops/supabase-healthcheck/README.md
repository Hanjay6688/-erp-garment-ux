# Pemeriksaan database berkala — persiapan, belum terpasang

Permintaan owner 13 Okt 2026: otomatis menjaga aktivitas database dengan biaya Rp0.
Disiapkan terpisah oleh Astra; penulis utama tetap mengintegrasikan pemasangan.
Basis yang diperiksa: `68bb8828836f34a0e054a548c0dadb190666051c`.
Ini tambahan operasional sesudah kandidat audit, bukan penerimaan audit independen.

## Cara kerja

Satu koneksi setiap enam jam (empat kali sehari), transaksi READ ONLY,
SELECT konstanta + identitas database/role + status transaksi. Tidak membaca tabel bisnis,
tidak memanggil RPC produk, tidak membuat cron di Supabase, dan selalu rollback/close.
Target dibatasi ke Enteng menurut D13-7. Legacy tidak diterima. Data transaksi dan password
tidak dicetak. Gagal koneksi, target salah, role istimewa, atau hasil salah membuat job gagal.
Tidak ada resume otomatis, perubahan paket, atau tindakan penagihan.

Ini memberi aktivitas database dan memeriksa konektivitas, **bukan jaminan anti-pause**.
Supabase tidak menjamin ambang tetap yang memastikan proyek Free selalu aktif.
Tidak dapat membangunkan proyek yang sudah paused. Hasil PASS bukan bukti seluruh ERP sehat.

## Integrasi oleh writer

1. Gunakan repository operasional **privat**, sesuai usulan backup D13-7; jangan langsung menyalakan
   pada repo aplikasi publik atau menambah jadwal di kandidat beku. Tidak ada perubahan pada cabang writer.
2. Pada pemasangan yang diizinkan owner, sediakan role khusus `erp_healthcheck`: LOGIN,
   NOSUPERUSER, NOCREATEDB, NOCREATEROLE, NOREPLICATION, NOBYPASSRLS, NOINHERIT,
   hanya CONNECT ke `postgres`, tanpa grant tabel bisnis dan tanpa membership role lain.
   Password kuat disimpan melalui pengaturan Secrets; jangan kirim ke chat/repo/log.
   Role ini **belum dibuat**. Tidak ada SQL pemasangan yang dijalankan oleh Astra.
3. Simpan connection URL session pooler (port 5432) sebagai Secret `ERP_HEALTHCHECK_DATABASE_URL`.
   Format username `erp_healthcheck.<project-ref>`; URL tidak memakai query string.
   Salin hostname pooler sebenarnya dari dashboard, jangan menebak region.
   Client memakai TLS verify-full dan trust store sistem; jika gagal, perbaiki trust/koneksi,
   jangan menurunkan verifikasi TLS. URL direct juga didukung bila runner punya IPv6.
4. Salin `healthcheck.py` ke `scripts/healthcheck.py` dan template workflow ke
   `.github/workflows/erp-healthcheck.yml` pada default branch repo operasional privat.
   Set variable `ERP_HEALTHCHECK_PROJECT_REF=siimvrusnzxexizpyoib`.
5. Uji pada database sekali pakai dengan role tersebut: respons read-only, penolakan write,
   timeout, cleanup sesi, dan ketiadaan perubahan data. Setelah izin pemasangan, aktifkan
   `ERP_HEALTHCHECK_ENABLED=true`, jalankan manual sekali, lalu periksa run terjadwal.
   Jangan menyebutnya terpasang hanya karena file ada; butuh bukti manual dan jadwal sungguhan.
6. Untuk Rp0, gunakan runner standar, tanpa paid overage (budget Actions = 0 dengan penghentian
   saat kuota habis). Maksimal 124 run/bulan x timeout 3 menit = 372 menit runner; ini batas
   konfigurasi, bukan durasi yang sudah diukur. Kuota privat dibagi dengan backup dan pekerjaan
   lain: hitung bersama. Jangan menaikkan budget untuk mempertahankan jadwal.
7. Periksa notifikasi kegagalan GitHub milik owner. Tidak ada WhatsApp/email tambahan yang dipasang
   atau dikirim paket ini. Job yang sama sekali tidak terpicu tidak menghasilkan alarm sendiri;
   pantau tanggal sukses terakhir juga. GitHub bisa menunda atau melewatkan jadwal.

Backup malam pada basis di atas masih template dengan jadwal dikomentari. Backup yang benar-benar
berjalan kelak juga menghasilkan aktivitas database, tetapi jangan menganggap template itu sudah
melindungi dari pause. Health check tidak menggantikan backup; tidak menjalankan restore/dump/prune.

## Batas bukti dan mematikan

Uji lokal memakai koneksi tiruan untuk memeriksa penguncian target, redaksi rahasia, hasil gagal,
READ ONLY, rollback dan close. **Belum diuji dengan PostgreSQL nyata, pooler hosted, atau jadwal GitHub**.
Tidak ada koneksi ke Supabase asli saat pembuatan. Tidak ada jadwal aktif dan tidak ada biaya layanan baru.
`production_go:false` tetap. Astra sebagai penulis tambahan ini tidak memberi penerimaan independennya.

Matikan dengan variable `ERP_HEALTHCHECK_ENABLED=false` dan disable workflow.
Karena role khusus belum ada, tidak ada perubahan akses database yang harus dibatalkan saat ini.

## Acuan yang dibaca 13 Okt 2026

- https://supabase.com/docs/guides/platform/free-project-pausing
  (aktivitas query beberapa kali sehari biasanya cukup, tanpa jaminan anti-pause).
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule
  (default branch saja; jadwal dapat tertunda/terlewat; repo publik dapat nonaktif setelah 60 hari tanpa aktivitas).
- https://docs.github.com/en/billing/concepts/product-billing/github-actions
  (kuota gratis dan penggunaan runner privat).
- `docs/cp7/OWNER_DECISIONS_20261008.md` D13-7 dan batas pemasangan.

Uji lokal: `python -m unittest discover -s ops/supabase-healthcheck -p 'test_*.py' -v`.
