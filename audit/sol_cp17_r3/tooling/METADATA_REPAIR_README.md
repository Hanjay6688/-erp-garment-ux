# Kualifikasi metadata Sol Q1

Patch ini memperbaiki dua kesalahan pencatatan identitas milik audit Sol. Tidak ada perubahan aplikasi, SQL, kasus bisnis, query CodeQL, permission workflow, atau ref checkout. Pembatasan probe baru dari sesi sebelumnya tetap berlaku.

1. **T3 browser berhenti sebelum kasus.** Run awal `39146762759`, job `117732074565`, meminta path `scripts/cp7-src` yang belum ada pada UI historis `e43e0ed4bab5ba9a803100e57ddfd7cd2647c631` (tree `05fc26cf00a6e5253192f4bd2ec7d7f4bdf06bc1`). Hook baru membedakan checkout historis itu dari checkout kandidat. Path historis yang tidak ada dicatat eksplisit. Kandidat tetap wajib HEAD `b53b5acdf260b03ebac3474e9ae837fcef6f6eb1`, tree `32f54240a60e01ab8b1ffad7267d285a669be520`, lima tree produk tepat, serta tanpa perubahan tracked pada produk.
2. **CodeQL selesai menganalisis tetapi gagal binding.** Run awal `39146762479` membandingkan HEAD produk b53 dengan SHA workflow audit d850. Gate usulan memvalidasi HEAD/tree produk terhadap pin b53 dan menyimpan SHA workflow pada field terpisah. `GITHUB_SHA` tidak ditimpa. Loop pemeriksaan SARIF dan predikat kelulusannya identik secara AST dengan gate asli.
3. **Lingkup fase dibatasi.** Usulan T3 hanya menjalankan fase `browser` yang berhenti sebelum uji. Bukti `install` job `117732074327` dan `capture` job `117732074500` tetap dari run awal. CodeQL tetap empat bahasa. Nama workflow/run/artefak baru memuat `metadata-q1` agar tidak menyamarkan hasil awal.

`PATCH_MANIFEST.json` memuat hash sebelum/sesudah, daftar tepat perubahan, dan hubungan ke run awal. `METADATA_ONLY.patch` adalah diff terhadap commit workflow awal `d850ca7aeebdc3dfec15f2cc3190297e334a3273`. Selain dua step metadata, perubahan hanya nama workflow/run/artefak serta pembatasan matrix T3 ke browser. Semua field YAML lain dicocokkan setelah dikembalikan secara terstruktur ke nilai awal.

Pemeriksaan lokal final: 16 pemeriksaan metadata positif/negatif PASS, termasuk HEAD/tree/path kandidat salah, worktree produk berubah, checkout historis tidak dipin, path absen tidak eksplisit, dan SHA workflow yang dipakai sebagai SHA produk. Konstanta dicocokkan terhadap objek Git publik. Tidak ada database, HTTP, kasus bisnis, atau scan CodeQL yang dijalankan oleh pemeriksaan lokal ini.

Patch disiapkan lokal dan publikasinya dilakukan root melalui pemeriksaan normal. Hasil CI awal tetap FAIL/INCOMPLETE sampai ada bukti kualifikasi baru yang dibaca sendiri; pemeriksaan metadata lokal tidak membuat hasil bisnis atau gate CodeQL lama menjadi PASS.
