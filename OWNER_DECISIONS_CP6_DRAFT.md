# Daftar keputusan owner CP6 — usulan 25 September 2026

> **STATUS 25 Sep 2026 (2026-09-25T01:35:00Z): D01–D06 DISAHKAN OWNER sesuai Rekomendasi A (usulan di dokumen ini), termasuk akun lawan AX = pendapatan lain-lain.**
> Konfirmasi langsung owner di sesi audit Fable (chat claude.ai/code session_01Lr2LJrWiWmYCCUgwrZnJeY), 25 Sep 2026 ~01:25 UTC: "Ya, semua sesuai usulan" untuk D01–D06 termasuk akun lawan AX = pendapatan lain-lain (OTHER_INCOME). Label: OWNER_CONFIRMED_CHAT. Tiga kontrak (M/P/BR) belum berubah; addendum bernomor masih harus ditulis writer dan disahkan owner secara tertulis.
> Bagian di bawah dipertahankan apa adanya sebagai draft asal; status per keputusan ada di bagian "Pengesahan dan status".

**DRAFT asal — pada saat ditulis belum disetujui owner dan belum mengubah tiga kontrak.**
Dokumen ini menyiapkan pilihan yang konkret. Membaca atau menyimpan draft tidak berarti meratifikasinya. Putusan audit tetap HOLD; production_go=false.

Produk acuan: 9add57ea8c2b6b2dc37c0134717d4d39ba30b5dc. Sumber audit gabungan yang dibaca:44cc69d8f9c5f26aa5d50103a2fb827de0b0f01f. Sumber proposal writer:d284e9b4f4e9e6bede36b4fa0dd7966ce785fa8c. Hasil native baru Fable diperlakukan sebagai laporan Fable dalam tugas ini; tidak ada run baru GPT atau verifikasi ulang log native pada tugas keputusan owner ini.

M = ERP_V3_2_Master_Pulih_20260923.md; P = ERP_V3_2_Perubahan_Pulih_20260923.md; BR = ERP_ADDENDUM_BUSINESS_REPORT_CP7_2026-09-18.md. Hanya tiga kontrak ini menentukan kewajiban yang sudah berlaku. Catatan writer/auditor di bawah membantu menjelaskan keputusan tambahan, bukan menggantikannya.

## Yang sudah diputuskan — tidak perlu ditanyakan ulang

| Topik | Aturan yang sudah berlaku | Pekerjaan pelaksana |
|---|---|---|
| ERP-DEC03 / ALL | ALL data awal sudah disetujui: master, stok/nilai awal, kas/piutang/utang/uang muka, serta dokumen operasional terbuka. M:1024 secara eksplisit menggantikan catatan lama. | Buktikan cakupan, transport CSV, caller, lifecycle dan browser. Bukan meminta owner memilih ALL lagi. M:1043 masih memuat kekurangan cakupan, bukan pencabutan izin. |
| Draft yang di-prepare | Prepare tetap DRAFT dan editable. Perubahan membuat preview lama stale; finalisasi memakai isi terakhir di bawah lock. M:1025,3817. | CP6-19 perlu dibuktikan lewat UI/RPC atau jalur yang memang diizinkan dengan grant produk asli. SQL edit dengan grant tambahan belum membuktikan reachability produk. Owner tidak perlu memutuskan ulang boleh mengedit atau tidak. |
| Dasar tanggal invoice | Pada periode terbuka, koreksi biaya mengikuti tanggal invoice; periode tertutup memakai controlled adjustment. Posted facts dan filed snapshot dipertahankan. M:1022,1059–1065,3816. | Klarifikasi tanggal perpindahan nilai antartahap, bukan membatalkan keputusan tanggal invoice. |
| Aksesori 7 PCS | Tujuh PCS tetap tujuh; harga eceran manual yang valid. M:44,1023,1066–1071. | Verifikasi implementasi sesuai kontrak. Tidak perlu memilih prorata/eceran lagi. |
| Prefix dan unknown | Backdate tidak boleh merusak prefix qty/value; unknown bukan nol; scope/tanggal report harus sama dengan pemeriksaannya. M:3820,3825. | Jangan meminta izin owner untuk membiarkan stok historis negatif atau false READY. |

Urutan sumber penting: M:1020–1025 berada sebelum arsip V5 yang dimulai di M:1053. M:1072–1078 adalah status lama ERP-DEC03. M:149–150 mengharuskan membaca status arsip menurut waktunya.

## Enam pilihan yang memang perlu dibuat eksplisit

Semua pilihan A di bawah adalah **rekomendasi GPT**, belum keputusan owner. Pilihan ini mengatur perilaku bisnis, bukan menyetujui angka hasil pengujian writer.

### D01 — Tanggal koreksi mengikuti posisi nyata barang

**Rekomendasi A:** tanggal invoice tetap tanggal dokumen/ekonomi. Untuk periode terbuka, delta biaya dibawa oleh unit pada akun/tahap tempat unit itu benar-benar berada. Delta tidak boleh masuk WIP sebelum pemakaian bahan, FG sebelum penyelesaian barang, atau COGS sebelum penjualan. Secara sederhana, tanggal delta pada suatu perpindahan mengikuti yang lebih akhir antara tanggal koreksi ekonomi dan tanggal perpindahan sah tersebut. Nominal dan lineage tetap direkonsiliasi, tidak dihitung dua kali.

Contoh satu unit, biaya10 dikoreksi menjadi12, invoice21 Sep; bahan dipakai22 Sep; FG selesai23 Sep; terjual24 Sep:

| Tanggal | Efek tambahan2 pada rantai nilai |
|---|---|
|21 Sep|Tambahan2 masih menjadi nilai bahan, apabila unit sudah diterima dan masih berada di bahan.|
|22 Sep|Tambahan2 berpindah dari bahan ke WIP.|
|23 Sep|Tambahan2 berpindah dari WIP ke FG.|
|24 Sep|Tambahan2 berpindah dari FG ke COGS.|

Tanggal sistem penerimaan koreksi tetap disimpan terpisah. Jika tanggal dokumen mendahului penerimaan fisik, aturan ini tidak menciptakan stok sebelum penerimaan: receipt/matching/uang muka harus menggunakan jalur sah yang sesuai; kasus itu harus diuji tersendiri.

Untuk periode tertutup, usulan ini mempertahankan tanggal ekonomi asal dan memakai tanggal pengakuan pada periode terbuka yang sah melalui controlled adjustment. Filed snapshot tidak ditimpa. Kasus batas periode—termasuk receipt tertutup tetapi tahap berikutnya terbuka—wajib mendapat expected eksplisit dan bukti tersendiri, tanpa diam-diam membuka periode.

Untuk ADJUSTMENT_DATE, pisahkan dua hal: kuantitas adjustment tetap pada waktu kejadian fisiknya; koreksi nilai yang datang belakangan mengikuti D01 serta aturan open/closed period. Nilai current, as-of, event, jurnal dan report harus cocok; satu field effective_date bukan bukti seluruh pembaca benar.

**Alternatif B:** owner menginginkan tanggal buku tunggal bagi seluruh koreksi. Ini memerlukan rancangan akun/penyajian penghubung yang jelas agar tidak mengurangi FG/WIP sebelum ada; bukan izin mencatat saldo tahap negatif atau langsung menerima oracle lama.

Dampak: klarifikasi delapan AS, dua belas kalender dan AO periode terbuka; AO tertutup serta ADJUSTMENT_DATE tetap memerlukan bukti teknis. Dasar: M:1022,1059–1065,3816,3820,3825,6148–6162. Usulan writer yang ingin diratifikasi terdapat pada scripts/cp6_t2_regression.py:42–52 dan scripts/cp6_ay_probe.py:1–22 pada d284e9b; keduanya bukan kontrak.

### D02 — Kapasitas saldo mengikuti tanggal yang dipakai

**Rekomendasi A:** refund, pemakaian, alokasi dan koreksi bertanggal hanya boleh memakai kapasitas sah pada tanggalnya, setelah memperhitungkan pemakaian/reservasi yang relevan. Penambahan saldo di masa depan tidak membenarkan saldo negatif pada tanggal yang lebih awal. Periksa juga setiap prefix yang terdampak setelah tanggal transaksi sampai current, bukan hanya saldo pada satu tanggal atau saldo akhir. Untuk uang muka, writer harus memetakan aturan ini pada saldo awal, koreksi, reservasi, alokasi, refund dan reversal sebagai satu keluarga.

Contoh: saldo67,25 pada20 Sep; koreksi efektif22 Sep menaikkannya menjadi100. Refund100 bertanggal21 Sep ditolak. Refund100 pada/setelah22 Sep baru mungkin sah jika tidak ada pemakaian/reservasi lain. Jika tanggal koreksi sebetulnya salah, gunakan koreksi fakta yang tertaut dan diaudit; jangan meminjam kapasitas masa depan.

Laporan operasional memakai fakta terkoreksi dengan tanggal efektif yang sah dan versi/waktu pembentukan jelas. Filed snapshot tetap immutable. Tampilan current tidak menyamar sebagai histori “apa yang diketahui saat itu”; jika known-as-of tidak tersedia, tandai tidak tersedia.

**Alternatif B:** beberapa jenis transaksi memakai kapasitas current meskipun diberi tanggal mundur. Owner harus menentukan daftar transaksi dan cara penyajian historisnya secara eksplisit. Ini tidak boleh menghapus larangan prefix negatif yang sudah berlaku untuk stok; memerlukan amandemen yang terukur, bukan sekadar label restatement.

Dampak: CP6-07/AUD-B04 dan hubungan dengan AUD-S04. Rekomendasi ini memperjelas aplikasi aturan tanggal pada uang muka; belum membuktikan seluruh temuan uang muka otomatis P1. Dasar: M:629–646,3816,3820,3825,6008–6021,6152; BR:271,375.

### D03 — Produk opsional pada WIP awal

**Rekomendasi A:** jika identitas produk diisi pada sumber WIP awal, identitas itu mengikat hasilnya. Produk/brand/warna/ukuran lain tidak boleh dipilih diam-diam saat completion. Jika produk belum ditentukan, output boleh ditetapkan pada boundary yang sah, setelah kecocokan PO/model/pola aktual/ukuran/material/warna dan fakta fisik yang tersedia diperiksa. Data yang belum diketahui tidak dianggap cocok otomatis.

Perubahan tujuan atas sumber yang sudah posted memerlukan jalur perubahan/konversi tertaut yang disepakati dan tidak menimpa fakta lama; jangan menjadikan completion sebagai jalan pintas mengubah sumber.

**Alternatif B:** field produk pada WIP awal hanya petunjuk, tidak mengikat. Jika dipilih, namanya dan perilaku UI harus jelas; tetap tidak boleh mengabaikan batas fisik seperti warna/material/ukuran, atau mengklaim perubahan brand tanpa provenance.

Dampak: oracle final CP6-18 dan kontrol positif WIP tanpa SKU final. Dasar yang sudah ada: M:359–379,3822; makna field opsional masih perlu dibuat eksplisit. CP6-19 tidak ikut keputusan ini.

### D04 — P-03: masalah menahan tanggal yang terdampak

**Rekomendasi A:** blocker yang dampaknya bisa dibuktikan menurut tanggal dan scope menahan laporan/closing yang terdampak saja. Untuk kegagalan sistemik, pemeriksaan yang belum terklasifikasi, atau dampak tanggal yang belum bisa ditentukan, tetap blok semua tanggal yang tidak dapat dibuktikan aman. Jangan menjanjikan kesiapan historis hanya karena current state tampak sehat.

Contoh: masalah terisolasi efektif24 Sep tidak otomatis membatalkan report20 Sep jika non-dampaknya benar-benar terbukti. Bila lineage/tanggal dampaknya tidak diketahui, report20 Sep juga belum boleh diberi READY.

**Alternatif B:** pertahankan kebijakan konservatif saat ini: semua kegagalan current-state yang belum mempunyai pengganti dated yang terbukti memblokir semua tanggal. Lebih banyak penolakan yang harus diselesaikan operator, tetapi tidak memerlukan inferensi scope yang belum terbukti.

Dasar: M:3825,5100. Definisi P-03 yang sedang dipertimbangkan: docs/cp6-aw-design.md:135–143 pada d284e9b. Dokumen writer menyebut banyak check “DATABLE” tetapi kode masih memblokir semua tanggal; label statis itu tidak membuktikan scoping aman.

### D05 — AX: barang jadi nyata tanpa sumber produksi

**Rekomendasi A untuk diratifikasi sebagai profil kebijakan:** hanya gunakan jalur ini bila barang fisik nyata dan tidak memiliki sumber nilai/produksi yang semestinya dipakai ulang. Buat lot non-PO dengan asal, pemeriksaan, actor, alasan, qty dan waktu fisik yang jelas. Jangan menciptakan produksi, upah atau reimbursement dari PO.

Nilai memakai pembanding HPP yang sah pada tanggal fisik, dengan lingkup dan cara rata-rata tertulis. Jika tidak ada pembanding yang sah, owner mengisi nilai dan alasan; nol hanya jika dipilih eksplisit dengan alasan. Bila pembanding sah ada, tidak ada override nilai bebas yang diam-diam menggantikannya. Usulan akun lawan writer adalah OTHER_INCOME/pendapatan lain-lain; ratifikasi akun ini secara eksplisit atau minta akun pengganti yang disetujui, jangan menyimpulkannya dari warna hijau tes.

**Alternatif B:** jika nilai/sumber belum jelas, simpan hasil pemeriksaan sebagai pending dan tahan posting finansial sampai diselesaikan. Keadaan itu tidak boleh disebut FG finansial final dengan nilai0.

Dasar tetap: M:3816,3818,3822–3825. Detail profil AX di atas adalah proposal yang perlu keputusan, ditelusuri dari scripts/cp6_ax_probe.py:1–9,181–202 pada d284e9b; bukan aturan akuntansi universal atau kesimpulan acceptance.

### D06 — Batas change request aksesori/laundry

**Rekomendasi A:** tutup semua kewajiban CP6 yang sudah disepakati serta perilaku kandidat yang akan diteruskan. Fitur CR baru yang belum masuk baseline dipisahkan sebagai successor sebelum consumer CP7 yang bergantung padanya. Jangan menunda bug baseline, kelengkapan ALL, 7 PCS, atau jalur lifecycle yang sudah menjadi kewajiban CP6 dengan menyebutnya CR.

Writer/auditor membuat daftar acceptance ID per fitur: baseline CP6, CR yang sudah masuk kandidat, CR tambahan yang ditunda, serta dependensi CP7. Untuk item yang sudah masuk kandidat, owner harus memilih menerima cakupannya untuk diuji tuntas atau merevisi kandidat secara eksplisit; tidak boleh diam-diam diberi N/A. Detail tarif/vendor/retur/servis yang belum diputus hanya menahan fitur terkait.

**Alternatif B:** semua CR aksesori/laundry yang ditentukan dalam daftar tersebut dikerjakan sebelum freeze final CP6; scope dan waktu pengujian lebih besar.

Dasar: M:1691–1699,1753–1757,4448–4479. Batas tahap diperiksa bersama Addendum CP7. Ini pilihan penempatan pekerjaan, bukan izin memulai CP7/deploy atau menghapus temuan lama.

## Cara menutup 25 disposisi T2 sesudah keputusan

| Kelompok | Jumlah | Setelah kebijakan tertulis |
|---|---:|---|
|AS tanggal|8|Oracle per tanggal/akun/nominal/lineage berdasarkan D01; pertahankan hasil beku lama, uji ulang skenario dengan oracle baru yang ditinjau auditor.|
|Kalender|12|Uji semua batas bulan/zona dengan D01 dan rekonsiliasi as-of; tidak sekadar ganti HOLD menjadiPASS.|
|AO terbuka|2|Uji pemindahan nilai mengikuti tahap dengan nominal yang tetap benar.|
|AO tertutup|2|Aturan controlled adjustment sudah ada; buktikan implementasinya, termasuk tanggal ekonomi versus pengakuan dan snapshot filed.|
|ADJUSTMENT_DATE|1|Perbaiki ketidaklengkapan pengujian; buktikan quantity/value/effective date dan seluruh reader/jurnal/report yang terdampak.|

Persetujuan D01 bukan persetujuan semua 25 hasil. Fixture payroll APPROVED-but-unpaid dan seed quieting harus dinyatakan, dibatasi pada kebutuhan fixture, serta tidak menutup kasus negatif payroll/readiness yang hendak diuji. M:3818,3824–3825,4322–4324,1769.

## Yang bukan tugas owner

Writer/auditor tetap mengerjakan perbaikan produk, ordinary-route reachability, identitas sumber lintas batch, kasus same-source dan distinct-source, cakupan selector, pembulatan, runner integrity, browser/Auth/race, serta rollback AC..AV varian rilis. Owner tidak perlu memilih SQL, indeks, helper WIB, atau memberi izin mengubah expected agar tes hijau.

## Pengesahan dan status

Semua D01–D06: **DISAHKAN OWNER (OWNER_CONFIRMED_CHAT, 25 Sep 2026) — pilihan A/usulan untuk semuanya.**

| ID | Keputusan owner | Sumber | Status kontrak |
|---|---|---|---|
| D01 | A — tanggal koreksi mengikuti posisi nyata barang; invoice tetap bertanggal invoice; periode tertutup lewat penyesuaian terkendali | konfirmasi chat 25 Sep | addendum belum ditulis |
| D02 | A — transaksi mundur hanya memakai kapasitas sah pada tanggalnya (refund 100 di tgl 21 dengan saldo 67,25 ditolak) | konfirmasi chat 25 Sep | addendum belum ditulis |
| D03 | A — produk WIP awal yang diisi mengikat hasil; kosong → ditentukan saat completion dengan kecocokan fisik/sumber tervalidasi | konfirmasi chat 25 Sep | addendum belum ditulis |
| D04 | A — masalah menahan tanggal/scope yang terbukti terdampak; sistemik/tidak jelas → blok semua | konfirmasi chat 25 Sep | addendum belum ditulis |
| D05 | A — barang jadi tanpa sumber = lot terpisah, pembanding HPP sah, nol eksplisit; **akun lawan pendapatan lain-lain (OTHER_INCOME) disetujui** | konfirmasi chat 25 Sep | addendum belum ditulis |
| D06 | A — kewajiban CP6 diselesaikan; CR tambahan dipisah sebagai kelanjutan sebelum consumer CP7; bug/baseline tidak ikut ditunda | konfirmasi chat 25 Sep | addendum belum ditulis |

Catatan asal draft (sebelum pengesahan):

Owner dapat memilih A atau B per ID, atau menuliskan perubahan pada klausul tertentu. Catat jawaban persis dan tanggal; susun addendum bernomor yang mengacu klausul tiga kontrak dan menyebut bagian yang diperjelas/diubah. Jangan mengklaim “kontrak sudah diperbarui” hanya dari commit draft ini.

Setelah pengesahan, writer menerapkan perilaku yang dipilih; auditor mengunci oracle dan menjalankan bukti pada source yang tepat. Gate keseluruhan tidak otomatis ACCEPT, dan tidak ada production GO dari keputusan kebijakan saja.

## Catatan auditor Fable (25 Sep 2026) — pembacaan atas draft ini

Status: draft ini tetap USULAN; catatan di bawah adalah pendapat auditor untuk membantu owner memilih, bukan persetujuan.

**Dua hal yang sudah diputuskan kontrak dan saya ubah perlakuannya di register:**
- ALL (M:1024): CP6-17 bukan lagi pertanyaan owner. Tugas auditor: buktikan cakupan (22 state / 6 keluarga per crosswalk GPT) lewat transport CSV, caller, lifecycle, browser. Status index: `CONTRACT_DECIDED_COVERAGE_OPEN`.
- Draft prepared boleh diedit (M:1025, M:3817): CP6-19 diuji ulang lewat jalur aplikasi yang sah (CREATE → SAVE_FILE → VALIDATE/FINALIZE → SAVE_FILE ulang → FINALIZE; skenario `audit/scenarios/xaudit_6.py`; rev1 run 36080176237 dan rev2 run 36080510340 INCOMPLETE karena fixture ditolak validasi produk; **rev3 run 36081137254 PASS 2/2 → CP6-19 REFUTED pada jalur aplikasi yang sah**; residu P3 opsional pada grant/cek ulang prepare RPC). Hasil SI-04 (edit SQL langsung) tetap tercatat, bukan bukti reachability.

**Pendapat auditor per pilihan (semua mendukung Rekomendasi A, dengan catatan):**
| ID | Pendapat | Konsekuensi pada temuan/oracle |
|---|---|---|
| D01 | Setuju A. Perilaku kandidat 9add57e yang saya ukur (date_family_1/2: leg bahan pada E, leg WIP/FG/COGS pada hari pindah tahap; tanpa AZ terjadi WIP negatif) sudah konsisten dengan A. Yang harus ditulis eksplisit: aturan hari untuk penyesuaian bahan (ADJUSTMENT_DATE) dan batas periode (receipt tertutup, tahap terbuka). | 8 AS + 12 kalender + 2 AO terbuka mendapat oracle tertulis; auditor menulis oracle baru (bukan mengganti expected lama) lalu rerun T2 pada head baru. Fixture QUIETED/PAYROLL_APPROVED harus dinyatakan di log run. |
| D02 | Setuju A. Dengan A, CP6-07 kembali menjadi cacat produk yang wajib diperbaiki (refund 100 pada 21 Sep ditolak karena kapasitas as-of 67,25), dan kelas AUD-S04 (stok) ikut diselesaikan dengan aturan yang sama. Dengan B, CP6-07 tetap P2 "as-of" dan owner harus mendaftar transaksi yang boleh memakai kapasitas current. | Oracle CP6-07: penolakan persis pada refund/pemakaian bertanggal yang melebihi kapasitas as-of; positive control: refund pada/setelah tanggal koreksi. |
| D03 | Setuju A. Kandidat saat ini tidak mengikat (SI-01: produk A/brand A/Blue → diselesaikan sebagai B/Red; `cp6_az_t1_family.sql:855-862` tidak merujuk product_id item opening). Dengan A, CP6-18 menjadi cacat P2 yang wajib diperbaiki; dengan B, UI harus memberi nama field "petunjuk" dan tetap menolak beda warna/material/ukuran. | Oracle CP6-18: completion dengan produk ≠ item opening (bila diisi) ditolak persis; bila kosong, harus lolos pemeriksaan kecocokan yang didokumentasikan. |
| D04 | Setuju A dengan syarat: per-date scoping hanya untuk cek yang lineage tanggalnya terbukti; sisanya tetap blok semua tanggal (= perilaku sekarang). Ini tidak mengubah temuan; hanya mengurangi false BLOCKED. | Tidak ada temuan yang bergantung; F1-03/CP6-14 tetap soal deklarasi fixture. |
| D05 | Setuju A. Perilaku AX yang saya uji sudah sesuai profil ini (nol eksplisit ditolak saat pembanding ada; konservasi; periode tertutup). Yang belum diputus hanya akun lawan OTHER_INCOME — perlu ratifikasi eksplisit owner. | Bila akun lawan diganti, jurnal AX dan reversal diuji ulang (fg_acc_1). |
| D06 | Setuju A. Daftar acceptance ID per fitur (baseline / CR sudah masuk / CR ditunda / dependensi CP7) dibuat writer, direview auditor. | GATE-16 turun dari HOLD ke ACCEPT hanya setelah daftar itu disahkan owner. |

Urutan yang saya sarankan: D01 dan D02 dulu (mempengaruhi 25 kasus T2 + CP6-07), lalu D03 (CP6-18), D05 (akun lawan), D04, D06.

## Konfirmasi owner langsung ke auditor (2026-09-25T05:29:02Z)
- Owner (sesi auditor, 2026-09-25T05:29:02Z): "Ya, teks itu sah" — addendum C0 bagian 1–8 hash d39762da0520f30268a73244e7471b7d990138e3cbe36475d639c7cfca8e926d (commit 5d54472) disahkan untuk D01–D05. Label: OWNER_CONFIRMED_TO_AUDITOR.
- Owner (sesi auditor, 2026-09-25T05:29:02Z) atas D03 §5.3: "Boleh posting, dicatat unknown." Syarat yang dinyatakan owner: model PO dan ukuran tetap cocok; merek/warna yang terisi wajib cocok; yang kosong dicatat unknown, bukan dianggap cocok; produk hasil ditetapkan saat penyelesaian dan dasar penetapannya disimpan; WIP lama tidak perlu ditolak hanya karena atribut sumbernya belum lengkap. Perilaku kandidat a095a9d sesuai (xaudit_7 A10_UNBOUND_BRAND_ONLY_COLOR_UNKNOWN_POSTS, writer UNBOUND_SOURCE_NO_ATTRIBUTES_CONTROL). Pertanyaan terbuka #1 di out/fable_t2_oracles_post_addendum.md TERTUTUP.
- D06: masih menunggu revisi lampiran C6 (lihat `out/fable_c6_annex_review.md`, `out/gpt_round8_c6_review.md`).
