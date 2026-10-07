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
- Uji awal lokal PGlite PG18.3: 145/145 cocok, 16 jenis penolakan, 26 supply events, dua mutasi tertangkap. Percobaan pertama berhenti sebelum kasus pertama karena ekstensi pgcrypto belum dimuat; wrapper lokal kemudian memuat ekstensi itu. Runtime produk/probe tidak dilonggarkan.
- Biaya tambahan: array timeline dipertahankan selama satu pemanggilan build. Memori puncak backend belum diukur; tidak ada klaim bahwa ini menyelesaikan beban memori/sumber/transfer aplikasi.

## Hasil PostgreSQL Native yang sudah dibaca

Kandidat kode/probe: `1c4028d8e804c61a555a0343ae42403ca64fd694`.
[Run 37585398848](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37585398848), job `112674235997`, PostgreSQL 16.15 sekali pakai: **PASS pertama**.

Seluruh arsip asli diunduh dan diverifikasi: 571 ID unik / 571 dieksekusi, 288 keluaran berhasil dan 283 penolakan yang identik (16 jenis), 404 supply events, 2/2 mutasi tertangkap dan versi benar tetap lulus. Canary buku besar utuh. Semua hash dan panjang hasil benchmark identik. Ini 571 perbandingan yang lulus, bukan 571 transaksi berhasil.

| Target | Posisi supply | Sebelum | Sesudah | Waktu berkurang |
|---|---:|---:|---:|---:|
| 100 | 0 | 457 ms | 271 ms | 40,7% |
| 300 | 0 | 1.374 ms | 812 ms | 40,9% |
| 1.000 | 0 | 4.648 ms | 2.786 ms | 40,1% |
| 100 | 100 | 966 ms | 854 ms | 11,6% |
| 300 | 100 | 2.104 ms | 1.616 ms | 23,2% |
| 1.000 | 100 | 5.834 ms | 4.061 ms | 30,4% |

Angka adalah rerata dua pengukuran A/B/B/A yang sudah dipanaskan pada satu sesi dan satu runner. Ini penghematan kernel; latensi aplikasi penuh harus diukur lagi oleh integrator.

Arsip permanen: `docs/cp7/evidence/astra-timeline-reuse-20261007/{RECEIPT.json,NATIVE_REPORT.json.gz,NATIVE_JOB.log.gz}`. RECEIPT mengikat commit, artifact, hash ZIP, hash JSON asli dan seluruh ledger kasus. Commit bukti setelahnya tidak mengubah source produk yang diuji.

## Perbaikan kecil penguji bawaan

Shell S0 pada run `37585398642`, job `112674235620`, berhenti sebelum tes produk karena `cp7_probe_evidence_test.py` belum memasukkan `p19_transport` dan `p19_scale` ke lingkungan finalizer tiruan. `NameError: p19_transport` direproduksi lokal; kedua berkas sumber persis sama dengan aa638356 sebelum patch bantuan.

Tambahan dua flag `False` menyamakan fixture dengan mode default driver. Seluruh tujuh kontrol lama lulus: kegagalan pemulihan, ID salah, grup hilang dan kegagalan sebelumnya tetap INCOMPLETE. Tidak ada assertion atau kriteria PASS yang dihapus. Log gagal pertama tetap disimpan di `SHELL_FIRST.log.gz`; hasil tujuh kontrol lokal ada di `FINALIZER_FIX_LOCAL.log.gz`. Kelulusan ini tidak dianggap kelulusan seluruh Shell/Native bisnis; Shell penerus dan kualifikasi head gabungan tetap perlu dibaca tersendiri.

## Pengambilan oleh integrator

1. Bandingkan diff terhadap head Claude terbaru; jangan timpa perubahan yang sedang berjalan.
2. Ambil perubahan satu fungsi beserta probe bila bukti Native pada commit kandidat lulus.
3. Jalankan regresi Native analisis, netting, attention dan P19 aplikasi penuh di head hasil penggabungan. Bukti kernel tidak menutup gerbang tersebut.
4. Periksa kembali `financial_source`, transfer/manifest, dan batas 1.000 produk. Optimasi ini tidak mengubah ketiganya dan tidak membuktikan 5.000 target dapat diproses aplikasi.

`independent_acceptance=false`, `full_P19_acceptance=false`, `production_go=false`.
Karena Astra membuat patch ini, penerimaan independen patch harus dilakukan peserta lain.
