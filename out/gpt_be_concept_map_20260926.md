# GPT — Peta konsep BE untuk dibahas dengan writer
Tanggal: 26 September 2026. Status: KONSEP / BELUM DIIMPLEMENTASIKAN ATAU DIUJI.
CP6 HOLD · audit_complete=false · production_go=false.

## 1. Identitas dan batas pekerjaan
- Permintaan owner: "BACA BE coba lu liat lu petakan dl, tar gw tanya writer sekarang dia setuju konsep lu ga".
- Sumber writer dipin pada `7d33d84d0f93c54c43e7acd9d2df4d89d6d6f2e2`; audit parent saat membaca `857a597b063c90edc3efe6d645c78d4fcdd36543`.
- Pada tree writer ini belum ditemukan family `cp6_be*`. Handoff §32 masih menyebut BE sebagai pekerjaan berikutnya. Ini pembacaan kontrak dan sumber existing, bukan audit runtime BE, bukan persetujuan desain writer.
- GPT hanya menulis berkas GPT di cabang audit. Tidak mengubah produk, SQL, workflow, kebijakan aplikasi, hosted, legacy, production, atau cabang writer/kompetisi.
- Penomoran M/P di bawah menggunakan kontrak asli yang hash-nya sudah dibekukan di AUDIT_PROGRESS.md. Kontrak mengungguli konsep ini; nama tabel/API baru diserahkan kepada writer.

## 2. BE terdiri atas empat pekerjaan
| Bagian | Masukan → hasil yang diperlukan | Sambungan | Dasar |
|---|---|---|---|
| BE-01 Ganti merek FG sendiri | Lot FG sumber → FG SKU tujuan dengan ukuran, grade, jumlah, dan asal barang terlacak | Konversi existing + BC untuk aksesori baru, barang bongkaran, pemeriksaan dan nilai pulih | M:4828–4843, 5057–5096; C6:22–23 |
| BE-02 Rework BS ke SKU baru | BS asal → pekerjaan rework nyata → hasil GOOD/BS dengan identitas yang benar | BS Resolution/rework existing; biaya dan lineage konversi | Handoff:2706; pagar identitas C6:28–29. Rincian target dan tahap posting perlu dipetakan writer |
| BE-03 Celup ulang BS ke SKU baru | BS asal → kirim/proses vendor → hasil aktual/QC → SKU tujuan | BD untuk jasa/tarif/invoice; BE untuk perubahan SKU dan asal biaya | C6:25–29, 147–148, 174–180; M:4192–4215 |
| BE-04 ALL-C04 kain kantong | Sisa gudang + asal pengeluaran/alokasi sebelum cutover → lanjutan periode dan koreksi biaya yang sah | Impor opening + kain kantong/period allocation existing | M:466–511; P:406–439; handoff:2300,2631 |

**ALL-C04 bukan konversi SKU.** Writer menaruhnya di family BE sebagai pekerjaan tersendiri. Jangan sampai hilang dari cakupan karena BE sering diringkas menjadi "ganti SKU".

## 3. Konsep alur yang disarankan

### BE-01 — ganti merek
1. Pilih lot sumber, SKU tujuan yang sah, lokasi, tanggal fisik, dan jumlah per ukuran/grade. Server memeriksa stok yang benar-benar tersedia dan identitas yang berlaku.
2. Catat aksesori baru yang benar-benar dipakai serta biaya jasa berbukti. Harga stok, harga nota mandor, dan reimbursement tidak saling menggantikan.
3. Sahkan lewat command konversi canonical: source keluar dan destination masuk atomik, dengan lineage. Bukan edit langsung identitas lot lama, bukan penerimaan produksi baru.
4. Barang bongkaran dicatat terpisah: yang belum kembali, sudah diterima, sudah diperiksa, dan sudah dinilai. Contoh 100 hang tag diharapkan, baru 80 kembali, berarti 20 outstanding; bukan 100 stok tersedia. Jika 100 kembali tetapi 20 rusak, statusnya berbeda.
5. Ganti merek boleh berjalan sebelum semua bongkaran kembali. Barang/nilai yang belum diketahui tetap terlihat pending; jangan membuat stok atau nilai pulih dari perkiraan.

Jumlah fisik sumber dan tujuan tetap seimbang per ukuran/grade pada konversi ganti merek. Perubahan grade karena hasil QC rework adalah kejadian berbeda dan harus punya bukti.

### BE-02 — rework ke SKU baru
- Pesanan rework harus menunjuk BS sumber, kuantitas yang ditahan/dikirim, pelaksana, dan target yang diizinkan. Target bukan penggantian `product_id` bebas pada dokumen lama.
- Bedakan jumlah dikirim, kembali sebagian, hasil GOOD, hasil BS, dan masih di pelaksana. Draft/partial tidak boleh diam-diam menciptakan stok siap jual atau biaya dua kali.
- Baseline UI existing menyimpan hasil kumulatif dan COMPLETE mensyaratkan hasil terhitung sama dengan jumlah kirim. Rute SKU baru perlu mempertahankan invariant itu atau menjelaskan perluasan resmi untuk kehilangan/disposisi; kekurangan tidak boleh hilang diam-diam.
- GOOD ke SKU baru hanya dibentuk setelah proses dan QC yang sah. Hasil gagal tetap tercatat sesuai identitas/keadaannya; nama target tidak otomatis menjadikannya GOOD.
- Hindari posting GOOD ke SKU lama lalu menambah GOOD ke SKU baru tanpa menghabiskan keluaran antara. Kalau writer memakai dua command existing, hubungan, atomisitas, dan konservasinya harus dibuktikan.
- Rework biasa yang tidak mengubah SKU tetap harus berjalan dengan perilaku existing.

### BE-03 — celup ulang
- Gunakan alur pekerjaan nyata seperti BE-02, dengan vendor laundry dan jenis proses/tarifnya. SKU berubah hanya melalui command konversi, bukan akibat memilih master harga atau mengubah warna pada invoice.
- Pisahkan **rewash BS baseline tanpa biaya vendor** dari **celup ulang berbayar**. Master harga laundry normal tidak otomatis mengizinkan tagihan rewash atau menetapkan tarif celup. Nilai kebijakan kosong tetap pending/ditolak sesuai kontrak.
- Sesuai arahan owner D10, tidak ada tarif laundry per ukuran dalam operasi yang diminta. Ukuran tetap dicatat untuk jumlah barang. Jangan membuat kebutuhan input tarif per ukuran baru demi BE. Tarif proses/vendor yang nyata dan aturan tagihnya tetap harus jelas.
- Saat barang di vendor, barang itu tidak boleh tersedia serentak sebagai stok sumber dan FG tujuan. Terima hasil dan QC secara nyata; belum diketahui ditampilkan unknown/pending.
- Invoice susulan/koreksi biaya menaut ke pekerjaan dan sumber biaya yang sama, lalu memengaruhi hasil yang masih WIP, sudah FG, sudah terjual, atau sudah dikonversi lagi. Pembayaran invoice dan kredit klaim mengikuti dokumennya masing-masing; BE tidak membuat utang kedua.
- Retry jaringan bukan pencelupan baru. Pencelupan nyata kedua adalah pekerjaan baru, dengan jejak dan kebijakan biayanya sendiri.

### BE-04 — kain kantong lintas cutover
Pisahkan tiga keadaan; jangan impor ketiganya sebagai stok:
1. **Sisa di gudang:** hanya jumlah dan nilai yang benar-benar masih ada masuk opening stock.
2. **Sudah ditarik, belum dialokasikan:** simpan asal pengeluaran dan nilainya sebagai sumber yang dapat ditelusuri. Jangan tarik stok atau bebankan biaya historis itu sekali lagi.
3. **Sudah dialokasikan:** nilai yang sudah terkandung dalam saldo awal WIP/FG/hasil periode tidak dibukukan ulang sebagai alokasi baru. Perlu tautan asal agar koreksi berikutnya tetap dapat dijelaskan.

Alokasi opsional yang disahkan **memindahkan biaya periode ke HPP**, bukan sekadar membagi beban. Denominator adalah seluruh hasil SELESAI_DIJAHIT sah dalam periode, termasuk Afui. Kontrak memberi contoh 11,25 → WIP 5,62 + FG 3,38 + COGS 2,25; setelah koreksi menjadi 15,00 → 7,50 + 4,50 + 3,00. Stok tidak keluar lagi. Cancel alokasi membalik alokasi/HPP, bukan mengembalikan kain fisik.

Untuk periode yang benar-benar melewati cutover, writer perlu menjelaskan sumber pengeluaran dan hasil jahit historis yang dapat diimpor secara sah. Jangan mengarang PO/absensi/pengeluaran lama, mengabaikan denominator pra-cutover, atau mengalokasikan ulang bagian yang sudah masuk saldo awal. Jika bukti asal belum cukup, tampilkan kekurangannya; jangan mengklaim ALL-C04 selesai hanya karena sisa gudang berhasil diimpor.

**Errata GPT:** oracle lama `out/r9_all_oracle.md:224` tidak tepat jika larangan masuk WIP/FG diterapkan sesudah alokasi periode disahkan. Koreksi lengkap: `out/gpt_all_c04_oracle_errata_20260926.md`. Berkas beku lama dipertahankan.

## 4. Aturan biaya dan sambungan BC/BD
Konservasi yang diwajibkan M:5083–5096:
`nilai FG tujuan + nilai aksesori pulih + biaya/rugi terpisah = nilai FG sumber + biaya tambahan sah`.

- HPP sumber dibawa; tambahan aksesori/jasa masuk sekali. Jangan sekaligus memakai expense, manual label cost, dan tambahan HPP untuk pengeluaran yang sama.
- Aksesori produksi normal GOOD × BOM/reimbursement tetap terpisah. Ganti merek tidak memanggil penerimaan FG produksi ulang untuk memperoleh entitlement lagi.
- Barang bongkaran baru dinilai setelah bukti dan kebijakan sah. Penilaian terlambat harus menyesuaikan turunan yang tepat tanpa menulis ulang histori produksi.
- Nilai pulih tidak boleh sekaligus menjadi stok baru sementara nilai yang sama tetap penuh pada FG tanpa perlakuan biaya yang menjelaskan keseimbangannya.
- BC sudah punya custody/inspection/valuation, tetapi **itu belum membuktikan penilaian bongkaran konversi mengoreksi biaya FG**. `bc_value_custody_v1` saat ini memanggil adjustment dengan akun kredit kebijakan; writer perlu menunjukkan adapter biaya/lineage khusus konversinya. Ini risiko integrasi yang perlu dibuktikan, bukan temuan cacat BE yang sudah berjalan.
- BD menyediakan jalur jasa/invoice/koreksi, tetapi sumber tagihan pekerjaan celup/rework harus dipetakan secara eksplisit. Kemampuan invoice laundry normal saja belum cukup.
- Tanggal fisik/ekonomi/pembukuan dipertahankan; periode tertutup memakai koreksi sah dan filing lama tidak ditulis ulang.

## 5. Titik existing yang sudah dibaca
| Sumber pada head dipin | Fakta pembacaan | Implikasi |
|---|---|---|
| `src/InventoryControlPages.tsx:201–255` | BrandConversionPage memakai data simulasi; tombol mengabarkan backend belum disentuh | Perlu form terhubung dan bukti browser nyata; demo bukan bukti BE |
| `src/ConnectedBsResolutionPage.tsx:218–307` | Partial/COMPLETE rework dan tujuan pelaksana sudah ada; form yang dibaca belum menawarkan SKU tujuan baru | Perlu ekstensi terarah, tidak mengganti seluruh resolusi BS |
| `scripts/cp6_av_definitions.py:52,76–86` dan paket AJ rework | Builder AV mengambil completion AJ dan menambah guard existing-stock pada produk BS asal | Baseline lineage harus dijaga; ini pembacaan sumber, bukan introspeksi fungsi DB final |
| `scripts/cp6_bc_objects_service.sql:61–68,642–679` | Sumber outstanding mengenal CONVERSION; valuation custody memakai policy dan native adjustment | Ada komponen untuk dipakai ulang; wiring konversi dan biaya tetap perlu bukti |
| `scripts/cp6_bd_objects_pricing.sql:398` | Ada propagasi biaya konversi dari PO | Uji bahwa sumber BE betul-betul terhubung, termasuk opening/non-PO bila masuk scope |
| `src/ConnectedPocketFabricPage.tsx:148,173–195` | Halaman existing menjelaskan beban lalu alokasi opsional ke HPP | BE melengkapi opening/asal historis C04; jangan membangun ledger alokasi kedua |

Tidak ada pemeriksaan runtime BE dalam pekerjaan ini. Desain harus menggunakan guard izin, source revision, idempotensi, mutex, inverse dan journal existing; tidak ada izin untuk melonggarkan guard.

## 6. Matriks bukti yang perlu ditulis sebelum implementasi BE
Semua baris di bawah **BELUM**: belum ada skenario executable, run ID, job ID, atau hasil BE. Ini rancangan cakupan, bukan penerimaan.

| ID konsep | Kasus | Hasil yang dituntut | Dasar |
|---|---|---|---|
| GBE-01 | Ganti merek sebagian lot, beberapa ukuran | Source OUT = target IN per ukuran/grade; sisa sumber benar; biaya tidak ganda | M:4828–4843 |
| GBE-02 | Dua pengguna konversi sumber sama; penjualan berlomba dengan konversi | Tidak overdraw; kegagalan atomik; hanya transaksi sah yang membukukan | Invariant stok/konversi M:4828–4843 |
| GBE-03 | 100 aksesori diharapkan, 80 kembali; bandingkan 100 kembali/20 rusak | Outstanding berbeda dari damaged; belum kembali tidak masuk stok | M:3925–3940,5094 |
| GBE-04 | Nilai pulih belum ada lalu dinilai setelah target dijual/diretur/dikonversi | Pending jujur; konservasi biaya dan propagasi turunan; histori lama tetap | M:5083–5096 |
| GBE-05 | GOOD/BS partial rework, target baru, retry COMPLETE | Tidak ada FG ganda; hasil tidak melampaui sumber; QC dan lineage lengkap | C6:28–29; baseline rework existing |
| GBE-06 | Target tidak sah, salah ukuran, atau mencoba menaikkan grade hanya lewat master | Ditolak tanpa efek; hasil nyata/QC diperlukan | M:4828–4843; C6:28–29 |
| GBE-07 | Rewash gratis vs celup berbayar; tarif belum diketahui | Tidak ada asumsi biaya nol atau utang tanpa policy; kontrol positif dengan policy sah | C6:174–180; M:4192–4215 |
| GBE-08 | Invoice celup susulan setelah sebagian output terjual/konversi kedua | Estimasi diganti/dikoreksi sekali; biaya mengikuti sumber aktual | M:4192–4215,5092 |
| GBE-09 | Replay jaringan dan pekerjaan celup nyata kedua | Replay tidak menambah proses/stok/tagihan; pekerjaan baru punya asal sendiri | M:4204–4215 |
| GBE-10 | Inverse saat turunan dipakai vs sebelum dipakai | Penolakan/koreksi tertaut sesuai dependensi; tidak menghapus pembayaran/penjualan nyata | M:3954–3967,5092–5100 |
| GBE-11 | Opening kain kantong: sisa, ditarik-belum-alokasi, sudah-alokasi | Tidak stok/expense/HPP ganda; identitas asal stabil lintas batch | M:466–511; C6:30–34 |
| GBE-12 | Alokasi lintas cutover, koreksi nota, cancel, sumber stale/overlap | Denominator historis sah + Afui; hasil exact decimal; tidak ada tarik stok kedua | M:470–487; P:406–439 |
| GBE-13 | Browser/HTTP role sah vs tanpa izin, respons hilang, WIB, unknown | Jalur nyata dari input sampai jurnal; fail-closed; request ulang tetap satu | C6:32–34; guard existing |
| GBE-14 | Sumber opening/non-PO dan hasil konversi sebagai sumber lanjut | Asal biaya sah; tidak membuat PO historis palsu; inverse/recost tertelusur | C6:30–34; M:3954–3967,5092 |

75 kasus C6 lama saja tidak membuktikan celup ulang SKU baru: C6 sendiri menyatakan LAU-06b tambahan scope yang belum dirinci oleh 36 tes laundry lama. Tambahkan kasus BE khusus lalu regresi baseline BC/BD, T2, paket T3, rollback, dan browser pada head produk final.

## 7. Yang perlu dijawab writer atas konsep ini
1. Setuju atau koreksi empat batas pekerjaan BE-01..04; petakan command existing yang dipakai dan ekstensi yang diperlukan.
2. Nyatakan matriks target yang sah untuk ganti merek, rework, dan celup: atribut apa boleh berubah, apa harus tetap, dan bukti QC apa diperlukan. Jangan memakai batas demo sebagai kontrak.
3. Tunjukkan urutan status/kuantitas dan kapan FG/biaya diposting, terutama partial rework ke SKU baru; buktikan tidak ada output ganda.
4. Tunjukkan jalur biaya aksesori pulih dan invoice terlambat sampai barang turunan terjual/retur/konversi lanjut; bedakan komponen BC/BD yang tersedia dari adapter BE yang belum ada.
5. Petakan adapter ALL-C04 untuk ketiga keadaan dan denominator lintas cutover; tandai data historis wajib, pending, dan pencegahan alokasi ganda.
6. Sertakan tabel kasus → kontrak → oracle dan rencana paket/rollback. Bila perlu keputusan bisnis tambahan, jelaskan pilihan serta dampaknya; jangan menafsirkan persetujuan konsep sebagai pengisian akun/tarif produksi.

## 8. Referensi pin
- M: `ERP_V3_2_Master_Pulih_20260923.md`, SHA256 `f21ac70360915a1f1021b42a3918e862ca7d11cf88c1b90c5627b4490c69af07`.
- P: `ERP_V3_2_Perubahan_Pulih_20260923.md`, SHA256 `92966cd6ed27e64123be6c52e2263bfbdb3db91c97f2e441c3bdc98589397676`.
- CP7: `ERP_ADDENDUM_BUSINESS_REPORT_CP7_2026-09-18.md`, SHA256 `4566ab6f1c8e53bc21c70c0c777f780b526305815e04d5913a5c858dfaa85886`.
- C6: `docs/contracts/ERP_ADDENDUM_OWNER_DECISIONS_CP6_2026-09-25_LAMPIRAN_C6.md`, blob pada head dipin `de787a5ec1bc85b5f92e2afc490bc32d8ddaca31`. Rev4 yang disahkan: commit `4c61acad2270e11a2aca762237790a68cf36278a`, SHA256 `42e0481579497c0acfe45d7092681741d431efaaeb7c200533051690b1d25f35` menurut header dan catatan ratifikasinya.
- Handoff writer: `docs/cp6-au-r1-handoff.md` pada head dipin, khususnya §29.6/§32.
- D10/13 kebijakan: `docs/cp6-d11-kebijakan-dan-gbd03.md:20–21`, blob `3450aeccceb34d8c5a39614cfd82a7899d2ea48c`. Rekomendasi writer di sana bukan nilai produksi yang otomatis disahkan.
- Oracle historis: `out/r9_all_oracle.md:220–227`, `out/fable_all22_oracles_pre_code.md:506–533`, audit parent dipin. Yang satu belum menggantikan yang lain; aturan kontrak terbaru yang dipakai.

## LANGKAH BERIKUTNYA
Owner membawa konsep ini kepada writer. Writer menjawab enam butir §7 dengan pemetaan implementasi/rujukan untuk setiap perbedaan. Setelah desain cukup jelas, auditor menulis skenario dan oracle executable tersendiri; hanya sesudah head BE final tersedia dilakukan audit native/HTTP/browser serta rekonsiliasi gate. Jangan melabeli BE ACCEPT berdasarkan peta ini.
