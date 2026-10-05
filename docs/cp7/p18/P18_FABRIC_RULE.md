# P18 — Pengingat kebutuhan kain (`FABRIC_NEED`)

Status: kandidat sumber di cabang `claude/new-session-deapao`, belum dikualifikasi Native. `full_P18_acceptance=false`, `independent_acceptance=false`, `production_go=false`. CP6 tetap HOLD.

## Tujuan

Sebelumnya, baris kain dari analisis bersama sengaja tidak ikut ke pengingat. Aturan aksesori (`ACCESSORY_NEED`) mengecualikan baris `FABRIC_*`, supaya bukti kain tidak tercatat sebagai bukti aksesori. Setelah P08 menghubungkan angka fisik kain, pengingat kain mendapat aturan sendiri, `FABRIC_NEED` ("Kebutuhan kain"). Aturan ini bekerja di samping aturan produksi, aksesori, piutang dan utang.

## Aturan

1. **Satu kondisi per baris kain.** Setiap baris `FABRIC_*` di analisis bersama mendapat tepat satu kondisi dengan kunci `FABRIC_NEED:<target>:<material_key>`. Nilainya salinan persis `additional_external` dari baris itu. Pengingat tidak menghitung ulang angka kain.
2. **Positif → masih perlu ditangani (ACTIVE).** Tambahan dari luar lebih dari nol (ASSUMED, bertumpu pada resep) dibuka sebagai kondisi aktif. Teks panel menegaskan bahwa ini bukan perintah beli.
3. **Nol asumsi tidak pernah "selesai".** Tambahan dari luar = 0 yang masih ASSUMED menjadi `NO_CURRENT_GAP`, tidak `RESOLVED`. Episode yang sudah terbuka tetap dipertahankan; tidak ada penutupan berdasarkan asumsi.
4. **UNKNOWN tetap perlu diperiksa.** Baris kain yang resepnya belum direview (`FABRIC_UNREVIEWED`) atau yang angka fisiknya belum terbukti menjadi `DATA_REVIEW`. Alasannya disalin dari fakta, misalnya `FABRIC_RECIPE_NOT_REVIEWED`, `FABRIC_WIP_IDENTITY_UNRESOLVED` atau `FABRIC_SHARED_SUPPLY_SPLIT_UNDECIDED`. Seperti domain produksi/aksesori, `DATA_REVIEW` tidak membuka episode, dan tidak ada angka yang diubah menjadi nol.
5. **Original lama → `SOURCE_CHANGED`.** Penerimaan atau draf potong membuat analisis lama `ARCHIVED_STALE`. Kondisi dari Original itu menjadi "Analisis perlu diperbarui".
6. **Pengaturan eksplisit, satuan sama.** Kebijakan `FABRIC_NEED` bisa global atau per produk/ukuran (TARGET), dengan "Satuan dasar kain" yang diisi sendiri. Tanpa pengaturan, statusnya `UNCONFIGURED`, bukan nol dan bukan mati. Satuan ditulis persis seperti satuan bahan Native; khusus aturan kain boleh huruf kecil (misalnya `yd`), karena data Native lama bisa memakai huruf kecil. Ambang hanya dibandingkan bila teks satuannya sama persis; satuan berbeda, termasuk `YD` lawan `yd`, menjadi "Satuan perlu disamakan". Tidak ada konversi dan huruf tidak disamakan. Nilai ambang dan satuan adalah keputusan pemilik (PENDING_POLICY_VALUE), tidak diisi otomatis.
7. **Tanpa pengiriman.** Pratinjau hanya ke tujuan lokal uji (`LOCAL_TEST_SINK`). Tidak ada penerima, WhatsApp, penjadwal, atau DML bisnis.
8. **Cakupan.** Rule source melaporkan `fabric: COMPLETE_AUTHORIZED_ORIGINAL_UNKNOWN_PHYSICAL_AND_UNREVIEWED_RECIPE_RETAINED`. Domain kain mengikuti akses analisis bersama (seperti produksi/aksesori).

## Yang berubah

| Berkas | Perubahan |
|---|---|
| `scripts/cp7-src/reminders/rule-condition-source.sql` | Domain `FABRIC`, loop baris kain, kunci cakupan `fabric`. |
| `rule-policy.sql`, `policy-history.sql`, `local-sink.sql` | `FABRIC_NEED` masuk daftar aturan (termasuk lingkup TARGET) dan label pratinjau "Kebutuhan kain". |
| `src/nativeRuleSource.ts` | Penerima tertutup: domain/kunci/scope/nilai persis, alasan kain wajib sesuai keadaan, jumlah kondisi kain = jumlah baris kain, cakupan `fabric` wajib. |
| `src/nativeReminderPolicy.ts`, `src/NativeReminderPolicyPanel.tsx` | Aturan kelima dan input "Satuan dasar kain". |
| `src/NativeRuleSourcePanel.tsx` | Kalimat alasan kain dalam bahasa sehari-hari. |
| `scripts/cp7_rule_policy_cases.py`, `scripts/cp7_rule_source_cases.py` | Oracle penerus (ID dan jumlah kasus tetap): lima aturan, satuan `M` fixture untuk kain, nilai/cakupan kain. |
| `scripts/cp7_p18_fabric_rule_*`, `scripts/cp7_f05_analysis_probe.py` | Suite Native baru 11 kasus (mode `fabric_reminder`). |

## Kasus (deklarasi `P18_FABRIC_RULE.json`)

Tujuh DB: aktif dari Original (176 ASSUMED), kebijakan satuan persis (layak/di bawah/satuan beda; TARGET menimpa GLOBAL), nol asumsi tidak menutup episode (penerimaan 200 nyata → 0 ASSUMED, episode yang sama tetap aktif), identitas WIP belum pasti tanpa episode, resep belum direview di semua target, pembagian bersama belum diputuskan, dan pratinjau lokal "Kebutuhan kain 176". Satu race nyata dua sesi: pemeriksaan episode bersamaan → tepat satu episode. Satu Auth/HTTP nyata. Dua browser desktop/mobile: simpan kebijakan fixture, kondisi aktif 126 dengan PO tepat waktu, episode ASSUMED terbuka, dan bisnis Native tidak berubah.

## Bukti lokal (bukan bukti kualifikasi)

LOCAL_PG16_DEV: pemasangan bundel analisis + seluruh rantai pengingat beserta verifikasinya PASS. Uji asap `condition_rows` sesuai rancangan (ACTIVE/NO_CURRENT_GAP/DATA_REVIEW/SOURCE_CHANGED, satuan beda → UNIT_REVIEW_REQUIRED). Uji unit penerima dan panel PASS. Kualifikasi Native wajib di CI (workflow `claude-p18-fabric-rule.yml`); attention284, rule-lifecycle16 dan p18-e01-9 wajib dikualifikasi ulang karena SQL pengingat berubah.

## Batas skala (catatan P19)

Sumber kondisi menolak seluruhnya (`CP7_RULE_CONDITION_SCOPE_INCOMPLETE`) bila ada lebih dari 15.000 kondisi atau lebih dari 8 MB. Penolakan ini menyeluruh; tidak ada potongan sebagian. Jumlah kondisi kira-kira jumlah target × (1 produksi + baris aksesori + 1 kain), ditambah dokumen piutang/utang. `FABRIC_NEED` menambah satu kondisi per target, sehingga batas efektif jumlah target turun. Contoh: dengan rata-rata satu baris aksesori, batas efektifnya sekitar 5.000 target dikurangi jumlah dokumen tagihan. Uji beban P19 belum dijalankan; angka ini batas desain, bukan bukti kinerja.

## Batas

Ini satu bagian P18 (konsumen bersama untuk kain). Siklus dummy penuh P18 (stok/WIP/HPP/GL/utang/kas end-to-end), P19 skala, P20 audit independen dan P21 pemasangan tetap terbuka.
