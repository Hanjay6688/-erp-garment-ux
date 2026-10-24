# Peta penyambungan pilihan ke satu mesin

Hasil pembacaan kode24 Oktober2026. Ini rencana implementasi berikutnya;
fungsi di bawah belum diganti oleh stage konfirmasi. Tidak ada kredit forecast.

| Jalur sekarang | Perubahan yang harus dibuktikan |
| --- | --- |
| cp7_baseline_native.source_within(integer) | Tangkap pilihan terbaru yang sudah diketahui pada captured_at, terikat root+size dan versi produk. |
| cp7_reorder_inputs.capture_baseline(integer) | Tangkap konfigurasi yang sama untuk reorder dan sumber bounded. |
| cp7_baseline_native.build(jsonb,jsonb) | Gunakan resolver demand yang sama, dengan seluruh histori untuk menemukan sumber pembanding. |
| cp7_analysis_stage.baseline_rows(jsonb,jsonb,jsonb,text) | Gunakan resolver yang sama; pembanding bisa berada di luar chunk target. |
| cp7_history_bounded.compile dan cp7_reorder_inputs.compile | Saat raw stock besar, histori saat ini dihitung per chunk. Selesaikan histori sumber yang diperlukan sebelum menghitung target; jangan membatasi analog ke chunk yang kebetulan sedang diproses. |
| cp7_analysis_stage fase BASE_ROWS | Bounded memiliki histori lengkap dalam reference; staged lama mempunyai baris HIST tersimpan. Ambil sumber pembanding lengkap dari sumber yang sesuai, tanpa snapshot baru. |
| cp7_reorder_inputs.points | Profil yang dipilih sudah memakai hasil target Native yang sama. Pertahankan jalur tersebut dan beri provenance basis demand yang tepat. |
| Baseline, supply, bounded-work dan reorder fingerprints | Revisi pilihan/CLEAR dan kode resolver harus ikut identitas sumber; reader/freshness tidak boleh melupakan perubahan ini. |
| Engine signatures dan bounded producer hash | Tambahkan dependensi consumer dengan versi eksplisit; jangan melabel ulang snapshot/UUID metode lama. |

Pilihan adalah hubungan target–pembanding dan skala berversi. Bukti awal disimpan
utuh untuk audit; perhitungan baru harus memakai histori pembanding pada query dan
kedua clock snapshot baru yang sama. Jangan memakai total lama selamanya, atau
menganggap data setelah capture sudah diketahui sebelumnya. Perubahan versi
fisik target/pembanding, profil, pencabutan pilihan atau histori yang kurang harus
memiliki alasan server yang jelas dan gagal tertutup.

Urutan yang telah ada pada cp7_demand.estimate tetap manual terpilih, own history
cukup, analog yang direview, lalu UNKNOWN. Jangan mengubahnya tanpa keputusan.
Untuk analog, simpan numerator persis available_total_pcs * scale_factor dan
denominator hari AVAILABLE sampai cp7_baseline.target melakukan pembulatan PCS
akhir. Jangan memasukkan mean yang sudah ditrunkasi sebagai total satu hari.

Jika profil memakai buffer statistik, simpangan baku harus berasal dari histori
pembanding yang sama dan dikalikan skala yang sama. Syarat statistik existing tetap;
kekurangan hari/simpangan baku tidak diisi nol. Buffer hari atau statistik dipakai
sekali, dan supply/WIP/order/cadangan tetap melalui engine existing satu kali.

Implementasi berikut harus stage opt-in tersendiri dengan sumber forward/inverse
dipin, predecessor tepat dan delta katalog22 terhitung.47 sumber qualified yang
tersimpan tidak diedit untuk menyamarkan perubahan. Bukti minimum: tanpa pilihan
paritas legacy, prioritas manual/own, analog nonzero dengan pecahan berulang,
ukuran/versi/profil berubah, CLEAR dan recorded clock, source di chunk berbeda,
reorder/produksi memakai angka identik, freshness, skala2000 dan Auth/browser.
Model kompleks tetap memerlukan kebijakan aktivasi berversi dan bukti backtest
yang sah; peta analog ini tidak mengesahkan registry usulan menjadi keputusan owner.

## Temuan tambahan sebelum hook diaktifkan

`choice.apply` saat ini membandingkan full source sebelum dan sesudah insert.
Begitu pilihan masuk fingerprint consumer, insert pilihannya sendiri pasti mengubah
fingerprint. Overlay consumer harus membandingkan konfigurasi sesudah dengan tepat
satu delta target/revisi/receipt yang baru committed dalam transaksi, lalu memeriksa
seluruh sumber lain terhadap snapshot semula. Jangan sekadar menghapus seluruh
pilihan dari freshness atau menonaktifkan pemeriksaan kedua. Revision/CLEAR/actor/
reason/evidence/recorded clock harus tetap bagian identitas sumber perhitungan.
Untuk confirmation berikutnya, ambil snapshot baru bila pilihan sudah berubah.

Tidak boleh menambahkan captured_at baru yang bergerak pada objek fingerprint
pilihan. Gunakan baris pilihan immutable (recorded_at sudah tetap); clock penangkapan
mengikuti c.captured_at yang sudah ada dan menjadi batas pemilihan source_at.

Kernel estimate menerima analog.reason lewat cp7_wip.key (maksimal200 karakter),
sedangkan alasan konfirmasi memang mengizinkan1000. Input kernel harus menunjuk
ID/revisi pilihan yang sudah direview; simpan alasan lengkap dalam provenance,
jangan memotong alasan pengguna. Gabungkan refs secara distinct sebelum memanggil
kernel yang menolak duplikasi; jangan diam-diam membuang refs melewati batas existing.
Kernel target saat ini maksimum3660 counted days, meski query historis inklusif bisa
3661 hari. Consumer tidak memperluas batas kernel atau menciptakan threshold baru.
