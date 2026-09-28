# Penerimaan independen revisi CP6 dan CP7 — 29 September 2026 WIB

**Addendum putusan akhir:** master G04 telah diverifikasi dari byte aslinya. **CP6 CLOSED / diterima sesuai cakupan kontrak; R10 OPEN_CP7; `production_go=false`.** Lihat [CLOSURE_R10_SCOPE.md](CLOSURE_R10_SCOPE.md). Writer terbaru `10a8347` hanya mengubah dokumentasi; seluruh hasil runtime dan asal tes di bawah tetap pada kandidat produk yang sama.

**Putusan: dua perbaikan diterima. CP6-FINAL-01 dan CP7-DELTA-01 CLOSED/PASS.** Tidak ada bug produk baru yang terbukti dalam pemeriksaan perubahan ini. Penerimaan berlaku pada kandidat di bawah; `production_go=false` tetap terpisah.

| Kandidat | Commit |
|---|---|
| CP6 writer | `fab23e77669f899594f983b41a6301c32246958b` |
| Produk/paket CP6 | `434b18215f57dd7a361ca621341488d3c31e9703` |
| CP7, PR #31 | `fa0ed346c322b8f24924f19f3a39f4117e6a0068` |
| Probe dan workflow auditor | `2506454eb686e000c69cfd1f6b422be57e4b62e4` |

Head writer dan CP7 diperiksa kembali setelah pengujian dan masih sama. Jalur produk CP6 tidak berubah antara commit paket dan kandidat terakhir. Seluruh 30 hash paket cocok; 29 pendahulu BF tidak berubah. BF release: `9bf4b5642c9d6af3369f98ad265bd802ee993fac7e1d8d290412184588392643`.

Ini **retest terbuka, bukan audit buta**: laporan, perubahan writer, dan probe lama sudah dibaca. Independensi dijaga dengan oracle tertulis sebelum run, kandidat dibekukan, ekspektasi tambahan auditor, dan hasil eksekusi sendiri. Fixture bersama dan tes writer yang digunakan kembali dinyatakan asalnya. Auditor tidak mengubah kode produk, merge, deploy, atau data production/UAT/legacy.

## Hasil tes yang dijalankan auditor

[Run independen 36466041148](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36466041148), kedua job SUCCESS. Semua jumlah berikut adalah kasus unik; pengulangan lokal dan CI tidak dijumlah dua kali.

| Kelompok | Hasil | Asal skenario |
|---|---:|---|
| CP6 native pada paket 30 berkas | 8/8 PASS | 3 probe asli auditor sebelah + 4 kasus batas waktu baru auditor ini + 1 kasus Grade B writer |
| CP6 benturan konversi/master | 4/4 PASS | Jadwal writer, dieksekusi ulang auditor |
| CP7 kontrak/proyeksi akses | 10/10 PASS | 7 probe asli auditor ini + 3 variasi akses writer |
| CP7 browser desktop/HP | 6/6 PASS | Skenario browser writer, dieksekusi ulang auditor |

Tidak ada FAIL, INCOMPLETE, atau kasus browser yang dilewati. Build CP7 beserta gate kepemilikan/akses dan pemeriksaan artefak juga lulus.

### CP6-FINAL-01 — riwayat konversi: CLOSED

Probe asli tetap identik, SHA-256 `584de8be2246e2bba85b9f2e1c1bbd5619c7d18279de1f53bbb42e0d8ff3a736`. Percobaan memundurkan perpindahan range ke tiga detik sebelum konversi sekarang ditolak oleh `BF_TARIFF_HISTORY`. Kontrol posting FG dan penjualan tetap ditolak oleh guard komitmen BOM. Tidak ada pelonggaran oracle lama.

Empat kasus baru menyilangkan **identitas sumber/tujuan × konversi POSTED/REVERSED**. Masing-masing membuktikan:

- Perubahan pada T−1 mikrodetik dan tepat T ditolak secara utuh; versi, dokumen, stok, saldo, dan kelompok HPP historis tidak berubah.
- Perubahan pada T+1 mikrodetik diterima. Identitas di T tetap lama; identitas baru mulai pada waktu yang tepat.
- Replay UUID tidak menambah versi atau dampak kedua.
- Pembalikan konversi tetap mengembalikan stok dan saldo FG/COGS/WIP tepat ke sebelum konversi; label dokumen tetap benar.

Empat jadwal dua sesi membuktikan serialisasi ketika konversi atau perpindahan master berjalan dahulu, baik sesi pertama commit maupun abort. Tidak ada database race yang tertinggal.

Perubahan produk menambahkan pemeriksaan akar fisik anggota lama/masuk, sumber/tujuan, POSTED/REVERSED, dan mengambil lock FG/HPP sebelum lock master. Tidak ada perubahan grant, fungsi publik tambahan, atau aturan harga. Hasil ini menutup celah konversi yang dilaporkan; laporan lama tidak pernah membuktikan nilai uang/jurnal rusak, dan retest tidak mengubah klaim historis itu.

### R14 — Grade B berisi: bukti yang hilang sudah dilengkapi

Auditor menjalankan ulang skenario writer berupa penjualan native, pindah range, dan retur menjadi Grade B. Hasil: **18 Grade A + 1 Grade B = 19 PCS**, nilai Grade B **42,00**, lot asal benar, jumlah/nilai antargrade cocok, serta inverse tepat. Ini menutup kekurangan bukti laporan Grade B berisi pada skenario tersebut; bukan klaim setiap jalur Grade B telah diuji.

### CP7-DELTA-01 — proyeksi keuangan: CLOSED

Tujuh probe asli auditor ini tetap identik; probe perbandingan biaya yang dahulu gagal sekarang PASS. OPERATIONS tidak lagi menerima payload perbandingan keuangan, OWNER tetap menerima data sesuai haknya, DENIED kosong, dan objek sumber tidak dimutasi. Tiga kasus writer menambah variasi KNOWN/ASSUMED/UNKNOWN dan pergantian akses. Browser desktop/HP memastikan keluaran lama tidak bertahan setelah perubahan akses serta status partial/error/stale tetap terlihat.

Pengujian ini menggunakan data sintetis. Tidak ada klaim akses backend atau gabungan CP6/CP7 sudah teruji. Temuan sebelumnya juga tidak membuktikan kebocoran data nyata atau nominal perbandingan tampil pada UI.

### Paket dan isolasi

Paket AC..BF dipasang langsung pada database sementara dengan baseline yang diselaraskan sampai AB. Semua 30 berkas lulus; backup/restore mengembalikan makna data yang sama. Seluruh gate paket bernilai true: installed, primary unchanged, backup/restore, security advisors, dan runtime. Auth sebelum/sesudah 0; skema publik dan batas fixture tiap kasus dipulihkan.

Catatan akurat untuk security advisor: keluaran mentah berstatus `REVIEW_REQUIRED`, karena pemasangan lengkap AC..BF menambah **143 INFO `rls_enabled_no_policy`** (73 → 216). Gate paket yang tidak diubah menerima kategori ini. Ini tidak boleh ditulis sebagai “nol temuan advisor”, dan tidak dibebankan sebagai bug baru akibat revisi BF.

## Cross-check bukti writer — dipisah dari tes auditor

Angka berikut cocok dengan log job aslinya. Auditor **tidak** mengaku menjalankan ulang seluruh angka ini.

| Bukti writer | Hasil terverifikasi | Run |
|---|---|---|
| CP6 paket runtime | 97 native, 26 race, 8 Auth/HTTP, 27 browser BF + 10 browser AU PASS | [36463334464](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36463334464) |
| CP6 rollback | 147 pemeriksaan PASS; byte produk/rollback tetap sama pada kandidat | [36462684960](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36462684960) |
| CP7 | 619 tes dan 6 browser PASS | [36460822362](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36460822362) |

Run writer yang awalnya gagal tetap tercatat. Koreksi menyamakan representasi waktu UTC/Jakarta untuk instant yang sama, dan menggeser rangkaian fixture pemulihan agar prasyarat tidak berada di masa depan. Produk, guard, angka ekspektasi, dan probe auditor asli tidak dilonggarkan. Retest terakhir lengkap lulus.

## Disposisi dan batas cakupan

- **Tidak ada pekerjaan perbaikan produk baru untuk writer dari retest ini.** Dua tiket di atas dapat ditutup dengan penerimaan independen ini. Temuan lama yang sudah lulus tidak dibuka ulang.
- Hasil audit perubahan CP6 sebelumnya, 11 native + 1 Auth/HTTP, tetap menjadi bukti historis pada kandidat sebelumnya; tidak dihitung ulang sebagai tes putaran ini.
- R03 tetap memakai wave fisik terpisah bila ukuran sama mempunyai dua referensi pekerjaan berbeda.
- R10 tetap OPEN: layar penjualan merupakan simulasi. Lulus engine jual/retur bukan bukti posting penjualan melalui UI terhubung. Addendum putusan akhir telah memverifikasi bahwa master G04 menempatkan pekerjaan UI tersebut pada CP7; tidak menjadi syarat tambahan penutupan CP6.
- CP7 tetap cangkang sintetis yang diizinkan owner. Integrasi operasional dan otorisasi backend harus diverifikasi pada kandidat gabungan ketika koneksi dibuat.
- Penerimaan dua perbaikan ini menyelesaikan blocker yang diuji, bukan pernyataan seluruh aplikasi siap produksi. Tidak ada merge atau deployment dari auditor; `production_go=false`.

Oracle, probe, dan ringkasan per kasus tersimpan bersama laporan ini: [ORACLE.md](ORACLE.md), [probe.py](probe.py), [evidence.json](evidence.json), [package-hashes.json](package-hashes.json). Artefak mentah run: CP6 `10988694180`, CP7 `10989802592` (retensi sampai 28 Oktober 2026). [Handoff gabungan writer](HANDOFF.md) memuat tindakan dan batas yang sama.
