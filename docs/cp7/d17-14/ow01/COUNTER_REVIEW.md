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

## Pemeriksaan silang berikutnya: lifecycle dan authority

- Dua penilaian awal independen sama-sama membuktikan first notice terminal tidak kembali setelah opt-in. Tafsir awal satu pemeriksa bahwa itu disengaja ditarik setelah dibandingkan dengan D17-5/D17-14. Perbaikan hanya new ACCESSORY_NEED: pertahankan pending, bukan tulis ulang terminal history atau membuat repeat baru. Legacy tetap.
- Pemeriksa lain menangkap repeat yang sudah antre lalu setting diubah0/interval diperpanjang. Ditambah current interval + exact predecessor ACCEPTED pada semua tahap instant; digest tetap terpisah. Model actual SQL mempertahankan kegagalan kausal kode6efd dan enam kontrol candidate lulus; bukan Native/provider.
- UI review menangkap first-round provider-refused retry yang sempat berubah label; tiga alasan retry nyata dipertahankan. Dua DOM tambahan lulus bersama seluruh25 lama; baseline UI module lulus25/gagal2 baru. Root gabungan parser/DOM60 PASS.
- Race review menangkap HELD_QUIET usang setelah quiet dimatikan; new-kind dinormalisasi PENDING setelah current settings/quiet gate. UNKNOWN/DISPATCHED/ACCEPTED tetap tidak diubah.
- Current owner semula hanya dicek sebelum lock pada settings/key/test/resolve. Ditambah cek sesudah wait dan sebelum commit; cached resolve ikut row lock. Delapan kasus race dideklarasikan sebelum Native run, tidak diklaim sudah lulus.
- Root sempat menyisipkan PERFORM di antara SELECT dan IF FOUND untuk resolve. Peer menunjukkan FOUND tertimpa; root mengganti dengan nullability primary key. Ini kesalahan patch writer yang dikoreksi sebelum dipush, bukan kegagalan lingkungan.
- Root menduga helper outbox memakai item_episode, tetapi kedua peer menunjuk alias episode pada helper aktual; dugaan ditarik, expected tidak diganti.
- Integration proposal agen sempat lupa IDS Python dan DECLARED, walau JSON diubah. Peer menangkapnya; root memakai import aktual untuk membandingkan exact IDS/count terhadap manifest, bukan percaya source-check proposal.
- CI a106/run39446129227/job118708414268 mengonfirmasi42501 after_snapshot pada14 slot yang tersisa,63 PASS/14 INCOMPLETE; selector baru mencapai source check. Peer sudah mereproduksi dengan exact helper, termasuk tabel kosong, dan menemukan EXECUTE cp7_capture belum diberikan. Grant sempit + GRANTS manifest + verify assertion dipasang; tidak menghapus guard/expected. Seluruh bukti pertama tetap disimpan.

Native77 (54 Native/9 race/5 HTTP/9 browser) dideklarasikan sebelum eksekusi; seluruh65 ID lama dipertahankan. Sampai receipt CI ditulis: Native baru, provider fake, browser asli, pemulihan, dan kecepatan perjalanan pengguna BELUM TERBUKTI. product_go/production_go tetap false; Enteng dan WA nyata tidak disentuh.

## Koreksi sesudah CI pertama

Kandidat754f387a, WA run39440200668/job118687701608 attempt1 gagal pada verifier hak postgres, observed cases0. Summary asli+traceback dipertahankan di CI_39440200668_FIRST_FAILURE.json; full Original tetap pada artefak/run GitHub. Stack smoke job118687702412 lulus, tetapi tidak menguji helper aksesori. Tidak ada expected kasus yang diubah. Perbaikan helper dan verifier terikat dependency baru perlu Native ulang; bukan klaim masalah lingkungan atau sekadar menghapus assert.

Final copied-file peer pins: pause f76d151d965f90db5e3c767e539dec7fb59cd2b4dcd34071537b6e6fac73c879; authority b502b80b0e8d8ef773f79636b46fb421a3932000b99f1ed93c1f5c3486731e24. Peer membaca ulang byte-identik dengan sumber proposal. Root import exact metadata86 lulus; registration-only membangun1+8closures tanpa database/case execution. UNKNOWN dan DIGEST punya subkasus baru, bukan diasumsikan tercakup oleh legacy. Root sempat menduga shared-copy TEST rate akan bentrok; runner modes.py175–194 ternyata membangun ulang setiap registered race. Dugaan ditarik, tidak ada limit produk atau timestamp TEST lama diubah. Hanya target UNKNOWN milik fixture sendiri di-age11menit dengan label.

Sebagian raw log/patch/source snapshot mempunyai whitespace asli yang harus dipertahankan. File itu dikompresi byte-exact, bukan dibersihkan atau ditulis ulang. Manifest EXACT_RAW_EVIDENCE_GZIP.json mengunci path, jumlah byte dan SHA256 hasil dekompresi; gzip -dc memulihkan isi asli. Git text whitespace checks dapat berjalan tanpa menutupi kegagalan atau mengubah hasil pertama.
