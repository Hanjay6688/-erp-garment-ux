# OW01 — pemeriksaan silang internal writer

Base f412e61be645b974ecca27862501b8e5b6e0c2ab. Enam pembantu GPT-6.1 Sol Max; tidak ada turunan agen dan tidak ada edit produk paralel. Root menerapkan dan menggabungkan perubahan. Penilaian awal dipisah sebelum temuan dibagikan; sumber kontrak dan reproduksi menentukan penyelesaian. Ini bukan audit independen.

| Skenario | Expected dari kontrak | Temuan awal dan disposisi |
|---|---|---|
| Snapshot memiliki target ganda / halaman lain | Tolak ambiguitas; original harus berasal dari halaman kondisi | Ditambah count tepat satu, scope/mark wajib, target ord dan batas halaman cocok. Source recheck kedua menyetujui; runtime Native belum tersedia. |
| Binding BOM/profil berubah lalu FG menutup gap lama | Jangan menyatakan sumber lama selesai | Binding dibandingkan sebelum nol; target berubah ditahan. |
| BOM kosong eksplisit tetapi WIP tidak diketahui | Kebutuhan aksesori nol, bukan produksi selesai | KNOWN_ZERO_ACCESSORY_NEED diperiksa sebelum guard WIP; teks UI khusus. |
| Review verdict dipasang ke jenis/key produksi | Parser menolak | Guard rule/kind/prefix dan regresi ditambah; tes aktual lulus. |
| UNKNOWN diberi angka pembelian/ambang tercapai | UNKNOWN tetap null | Detail tertutup 20 kunci; gross BOM terpisah, threshold NOT_EVALUATED_UNKNOWN. |
| Unit kosong atau gross 0.001 / 9007199254740993 | Unit sah dan desimal tepat | Trim unit dan format desimal string; tes positif/negatif aktual lulus. |
| WA memformat BOM 0.001 atau gross sangat panjang | Tidak membulatkan menjadi nol atau memotong angka | SQL trim_scale tepat; segmen gross+unit hanya dimasukkan utuh jika <=25 karakter. Model ekspresi enam kasus lulus, bukan Native. |
| 20 notice tertahan mendahului notice ke-21 | Ditahan tanpa menghalangi pemeriksaan berikutnya | last_rechecked_at mengurutkan ulang upaya; simulasi fungsi SQL kandidat + source sintetis lulus instant/digest, tanpa klaim provider. Countervariant hanya mengubah urutan, bukan diklaim commit lama. |
| Run satu notice kedaluwarsa, notice lain valid | Hanya item kedaluwarsa ditahan | Tidak lagi menandai semua ACCESSORY_NEED gagal. Upaya yang gagal tetap dihitung pada cap. Source recheck kedua menyetujui. |
| Run baru, target/kategori sama | Episode dan outbox sama, tidak ada instant ganda | apply_one memperbarui OPEN; hanya INSERT mengantrekan. Oracle proposal agen yang salah mengharapkan RESOLVED telah dikoreksi ke HOLD sebelum dijalankan. |
| postgres bukan superuser | Private helper tetap memiliki hak dependensi nyata | Penilaian sumber semula mengandalkan inherited membership; CI39440200668 membantah composite expectation itu sebelum kasus berjalan. Belum diketahui privilege mana yang false. Helper diganti memakai staged_authority dengan schema USAGE/EXECUTE eksplisit; tidak mengandalkan broad private-table access dan tidak menambah ERP DML. Native mencatat admin setup terpisah dari public recheck authenticated non-superuser. |
| Policy baru dinyalakan sesudah run DONE | Batas legacy satu pemrosesan per run dijelaskan | Usulan rescan otomatis ditarik sebagai blocker karena tidak ada kontrak mengharuskannya. Perubahan policy off->on memerlukan analisis baru; notice yang sudah antre selalu direcheck. |
| Owner mematikan WA saat source menunggu | Tidak memakai revision/settings lama | Try-lock settings dan revision sesudah source waits; quiet diperiksa dengan clock baru. Source review saja sampai CI. |
| Fixture STAFF memakai custom role P02 | Uji mencapai kontrak izin yang dimaksud | Peer menangkap fixture salah; proposal memakai seeded STAFF dan permission nyata. Guard tidak diubah. |

Bukti lokal baru: 58/58 parser+DOM, TypeScript, source/access/CSS, 71 fungsi PLpgSQL compile dengan empty row stubs, dan fairness sintetis. Kompilasi pertama mempertahankan dua kegagalan lexer `1then`; kode diperbaiki menjadi `1 then`. DOM proposal pertama mempertahankan dua caption salah; produk diperluas ke aksesori.

Run frontend luas pertama: 191 berkas lulus, 34 gagal; 1880 test lulus, 51 gagal, 30 skipped. Sebagian besar memerlukan PostgreSQL Native/non-root yang tidak tersedia di lingkungan ini. Satu kegagalan berbeda berasal dari gzip bukti lama yang belum dimaterialisasi oleh sparse checkout; file dikembalikan byte-identik dari HEAD dan test itu sendiri kemudian lulus. Tidak ada expected diubah dan tidak ada native-failure dinyatakan hijau lewat skip. Detail pertama disimpan di local-all-frontend-first.log.

Native77 (54 Native/9 race/5 HTTP/9 browser) dideklarasikan sebelum eksekusi; seluruh65 ID lama dipertahankan. Sampai receipt CI ditulis: Native baru, provider fake, browser asli, pemulihan, dan kecepatan perjalanan pengguna BELUM TERBUKTI. product_go/production_go tetap false; Enteng dan WA nyata tidak disentuh.

## Koreksi sesudah CI pertama

Kandidat754f387a, WA run39440200668/job118687701608 attempt1 gagal pada verifier hak postgres, observed cases0. Summary asli+traceback dipertahankan di CI_39440200668_FIRST_FAILURE.json; full Original tetap pada artefak/run GitHub. Stack smoke job118687702412 lulus, tetapi tidak menguji helper aksesori. Tidak ada expected kasus yang diubah. Perbaikan helper dan verifier terikat dependency baru perlu Native ulang; bukan klaim masalah lingkungan atau sekadar menghapus assert.
