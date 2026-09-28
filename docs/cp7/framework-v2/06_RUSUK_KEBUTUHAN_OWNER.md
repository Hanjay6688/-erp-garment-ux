# Sambungan kebutuhan owner — revisi 2, 28 September 2026

Status: **FRAMEWORK_REVISED / IMPLEMENTATION_NOT_STARTED / CP6 HOLD**. Mandat owner pada28 September adalah membaca, mengkritik, dan memperbarui framework; bukan menulis produk atau mengaktifkan pengiriman. Revisi ini melengkapi v1, bukan menghapus scope lama. Pada konflik rincian rancangan, bab ini dan kontrak v2 berlaku; keputusan bisnis owner tetap di atas rancangan teknis.

## 1. Putusan review dan arti tambahan ini

**Setuju dengan arah v1. Perlu mempertegas kontrak pelaksanaan sebelum P01 dikunci.** Satu mesin authoritative, WIP unik, empat waktu, unknown bukan nol, audit independen, dan bukti T1/T2/T3 sudah tepat. Sebanyak313 cek v1 adalah validasi persiapan, bukan kelulusan ERP.

Review mandiri menemukan: DTO v1 hanya menyimpan total alokasi per sumber tanpa pasangan sumber→target; timeline hanya angka/date sehingga unknown dan gap intrahari belum tegas; schema bentuk belum menjaga hubungan antarangka; M01–M08 belum memiliki expected angka kernel/promotion yang cukup; sumber BF SKU/range lebih baru daripada pin framework. Ini **kekurangan kontrak/evidence persiapan**, bukan vonis bug runtime CP7. P01 memang direncanakan untuk memfinalkan kontrak; revisi ini mengerjakan sebagian persiapannya sekarang.

Sembilan probe offline v1 terdiri dari dua kontrol dan tujuh variasi kontrak. Nilai PCS0,5, allocated21 dari sumber20, COMPLETE dengan capture belum lengkap, dan LOST_SALES minus lolos schema bentuk. UNKNOWN pada timeline dan rincian edge tambahan ditolak karena bentuknya belum tersedia. Bukti ada di `review/`; tidak ada ERP/native/Auth/browser CP7 dijalankan.

## 2. Daftar kebutuhan yang harus berujung ke layar dan bukti

| ID | Kebutuhan owner | Sumber → perhitungan → hasil | Bukti penutup |
|---|---|---|---|
| OWN28-01 | Tanya AI | Authorized AnalysisResult → prompt terstruktur → salin/buka ChatGPT/manual fallback | E18, X17; angka, syarat dan izin sama; tanpa API AI berbayar |
| OWN28-02 | SKU/size yang disarankan | FG+WIP+histori demand+membership → gap exact size dan waktu → Stok/Planner/Buat-Bagi Potongan | O01–O12, X01–X06, X18–X20 |
| OWN28-03 | Output laporan | Metric dictionary+run/scenario → template deterministik → Business Report dan arsip revisi | E08/E16, X16; contoh output ada, bukan sekadar tabel data |
| OWN28-04 | Skala prioritas produksi | Gap bertanggal+kelayakan aksi+deadline+status → urutan tindakan dengan alasan | O17, X18/X19; profit unknown tidak menjadi angka nol |
| OWN28-05 | Reminder produksi | Gap/WIP telat/status sumber → episode dan aksi pemeriksaan/produksi yang sah | X20/X24, RMD-T01–T08/T11–T17 |
| OWN28-06 | Reminder aksesori/bahan | BOM tertaut+terpasang+sisa eligible+incoming unik → tambahan kebutuhan/peringatan tugas | O09, X21/X24; issue bukan consumption |
| OWN28-07 | Reminder utang/piutang | Invoice/opening/payment/credit/reversal+due date → outstanding dan jatuh tempo | X22/X23/X24; tanpa cash forecast baru |
| OWN28-08 | Koneksi reminder ke WA | Episode+jadwal+penerima berizin → payload → occurrence/outbox/adapter/status | X25–X30 dan RMD-T18–T31/T35/T36; batas tahap di §8 |
| OWN28-09 | SKU komersial dan size/range | Commercial SKU/version+membership bertanggal → physical member/lot/size | X01–X05; range bukan identitas fisik baru |
| OWN28-10 | Kerja per keluarga, ringkas dan tidak berputar | Kontrak→impact map→patch keluarga→T1→kandidat T2→rilis T3 | X31/X32; tanpa mengurangi gate atau mengulang semua tes tanpa delta |

Setiap baris wajib mempunyai owner packet, input authoritative, hasil pengguna, positif/negatif, jalur unknown, dan status. `registries/owner_delta.json` menjadi daftar kendali. Tidak boleh hanya menambah judul menu dan menyebut kebutuhan selesai.

## 3. Identitas SKU/range dan histori yang dipakai CP7

Sumber pembaruan: kontrak BF dalam `docs/cp6-bf-sku-range-handoff-20260928.md` dan `docs/cp6-bf-sku-implementation.md` pada kandidat audit6739a2f. Ini sumber desain/hasil audit terdahulu, **bukan pembacaan head terbaru atau accepted base**. P00 mengimpor acceptance aktual BD/BE/BF, delta FREE/WAIVED, release dan last check CP6. Field accepted_execution_base tetap null sampai ada bukti sah.

1. **SKU komersial** mengelompokkan harga, resep aksesori dan referensi tarif. **Produk fisik** tetap exact root+size+version; stok/lot/sales/retur/HPP tidak digabung menjadi satu lot range.
2. PRODUCT target mengandung identitas fisik existing, brand, exact size, dan `commercial_identity` bertanggal. Jika sumber legacy belum dipetakan: `LEGACY_UNMAPPED`, tampilkan physical source yang sah; jangan menciptakan SKU palsu atau menggabungkan demand otomatis.
3. Range31–33→31–34 memindahkan keanggotaan bertanggal, tidak memindahkan stok/COGS lama. Revisi ekonomi dan membership dipisahkan dari perubahan identitas fisik. Ganti harga saja tidak membuat seri histori demand fisik menjadi produk baru.
4. Analisis exact size memakai physical root yang stabil. Ringkasan komersial menyebut basis `AS_KNOWN` atau `CURRENT_RESTATED`; regrouping laporan terkini harus berlabel. Report dan plan lama tetap menunjuk membership yang dibekukan.
5. Contoh: histori size34 terjual6 sebelum pindah grup. Dalam laporan lama tetap kelompok asal; tampilan current-restated boleh kelompok baru dengan label, tetapi total lintas grup tetap6, bukan12. Stok/biaya tidak berubah karena pengelompokan.
6. Default rancangan status produksi pada commercial SKU; bulk action membawa daftar member+revision yang direview dan berlaku atomik. Anggota berubah sebelum submit → review ulang. Jangan diam-diam mengaktifkan member baru atau membuat override per size tanpa kebijakan. STOP/PAUSED tidak menghasilkan aksi START_NEW; shortage/WIP lama tetap terlihat sebagai informasi/tugas. Penjualan existing tetap mengikuti haknya sendiri.
7. Tidak ada asumsi tiga ukuran, ukuran berurutan, atau range teks yang bisa dipecah dengan minus. Singleton27, satu ukuran32 dalam grup, ukuran alfanumerik,4/5/6 anggota, dan komposisi tidak rata harus tetap valid. Helper lusin tidak mengubah manual13 PCS; tanpa aturan pembagian sisa, operator memilih komposisi sah.
8. BOM/price/tarif bersama dipakai dari versi yang sah untuk pekerjaan bersangkutan. PO lama, rework dan celup ulang punya source contract masing-masing; jangan memakai revisi grup hari ini untuk recost atau matching historis. UNKNOWN berbeda dari FREE/WAIVED sah dengan alasan/scope. Temuan FREE/WAIVED CP6 tidak dianggap sembuh oleh bab ini.

P03 memiliki subkartu identity/membership/status; P05 memiliki cohort demand; P10/P11 melindungi exact lot dan sales allocation; P13 menjaga valuation; P14/P15 menampilkan grouping dengan basis tanggal. X01–X05 menghubungkan semua consumer ini.

## 4. Kontrak hasil satu mesin: detail yang sebelumnya belum terangkai

Kontrak v2 berada di `contracts/analysis.schema.json`, `backbone.ts`, dan contoh yang sudah disesuaikan. Ini **usulan boundary**, belum parser/endpoint ERP. P01 melakukan code generation/parity atau pemeriksaan ekuivalensi sebelum implementasi.

### 4.1 Alokasi dan kecocokan adalah relasi sumber→target

`allocation_edges` memuat source_key, target_key, exact size, input_qty, projected_output_qty, match, eligible_at, assumption_ids, dan source refs. Kecocokan berada pada edge: satu sumber bisa cocokA tetapi tidak cocokB. `sources.allocated` tetap ringkasan input; bukan pengganti edges.

Contoh dua sumber S1/S2 masing-masing10 dan target A/B masing-masing10: S1→A,S2→B dan S1→B,S2→A punya total sama tetapi bisa berbeda kompatibilitas/ETA. Karena itu total saja tidak cukup. Edge tidak boleh menyatakan output final pasti sebelum command QC/identitas sah. Input dan projected output dipisah untuk yield; batas source diperiksa pada input.

Semantic validator minimal: target/source ada dan unik, exact size cocok, tidak ada alokasi positif pada INCOMPATIBLE/UNKNOWN/NEEDS_CHECK, sum input edges=source allocated≤physical/eligible input, sum output tidak melampaui input pada unit PCS yang sama, dan tidak menghitung sumber yang sama lagi sebagai incoming. Scope teredaksi boleh tidak mengungkap constraint global, tetapi tindakan yang tidak terbukti feasible ditahan.

### 4.2 Timeline tidak mengarang nol dan tidak menyembunyikan keterlambatan

Demand/supply/balance/unmet/backlog pada timeline menjadi FactValue. Missing/unknown tetap typed; timeline boleh PARTIAL tanpa mengubahnya menjadi nol. `timing_basis`, `timing_policy_id`, `first_gap_at`, `min_intraday_balance` dan event_refs menjelaskan ketepatan waktu. Timestamp diketahui dipakai engine; data tanggal saja memakai konvensi konservatif berlabel. Jika posisi intrahari tidak dapat dibuktikan, hasilnya unknown/assumed, bukan “aman”.

BACKLOG: saldo negatif berarti kebutuhan tertunda, dan backlog_qty menunjukkan besarnya. LOST_SALES: stok projected tidak negatif, unmet_demand dicatat terpisah tanpa dibawa sebagai order nyata. Semua itu simulasi, bukan pengakuan penjualan hilang aktual. Contoh FG0, demand5 pukul08, supply5 pukul16: saldo akhir BACKLOG0 namun gap pagi5; kebalikan urutan tidak punya gap. Pada LOST_SALES dengan urutan pertama, unmet5 dan stok akhir5. Supply sore tidak memuaskan kebutuhan pagi yang sudah hilang dalam mode tersebut.

### 4.3 Angka, konteks metric dan guard

COUNT fisik dan jumlah perintah PCS harus integer; forecast/rate ekspektasi boleh decimal dengan unit dan jenis proyeksi yang jelas, tidak diakui sebagai potongan barang aktual. Uang/meter/kg decimal sesuai domain, signed hanya pada nilai yang memang boleh negatif. Metric berisi scope_kind/key, period_start/end, knowledge_mode, formula, operands, readiness dan versi. Gross margin negatif sah bila rugi; negative stock actual tidak disamarkan sebagai saldo simulasi. Satu metric per tuple scope+period+mode+version; aggregate persentase dihitung dari operands, bukan rata-rata label persen.

Schema bentuk dan semantic validation adalah dua lapis. `COMPLETE` mensyaratkan capture_complete; UNKNOWN critical tidak menghasilkan rekomendasi KNOWN; refs/assumption IDs wajib resolve; hidden scope tidak masuk totals/prompt. Validator persiapan menguji beberapa aturan ini sebagai contoh, **bukan implementasi parser/server lengkap atau sertifikat keamanan**. Seluruh aturan harus diuji pada runtime di P01/P02 dan gate terkait.

## 5. Rekomendasi, prioritas produksi, dan hasil laporan

Satu kartu tindakan menjawab: **kerjakan apa, SKU/size mana, berapa PCS, paling lambat kapan, kenapa sekarang, sumber apa yang dipakai, apa yang masih belum pasti**. Kartu memperlihatkan gap dasar, gap bersyarat setelah kandidat, jumlah feasible, shortage belum teratasi, dan tambahan akibat pembulatan. Saran produksi baru dipisah dari percepat laundry/QC, lengkapi data, atau periksa kandidat.

Urutan rancangan menggunakan aturan yang bisa dijelaskan: gap yang akan terjadi sebelum pasokan siap → deadline nyata → aksi eligible yang lebih cepat menutup gap → ukuran yang kurang → stable ID. Jangan menjadikan profit besar alasan menyembunyikan gap mendesak; margin boleh menjadi tambahan hanya dengan policy pilihan dan cost valid. Deadline unknown masuk daftar perlu cek yang terlihat, tidak menjadi aman atau selalu paling belakang. Manual override beralasan/berversi tidak boleh mematikan Stop, permission, atau constraint kapasitas.

Action key mencakup intent+canonical source/group+scenario. Satu batch yang membantu dua SKU menghasilkan satu tindakan sumber dengan dua child kebutuhan. Dua masalah berbeda pada batch yang sama—fisik terlambat dan invoice belum final—tetap dua intent tertaut. Kategori filter bukan dua salinan tindakan.

**Business Report wajib mengeluarkan laporan yang bisa dibaca**, bukan hanya menyediakan data mentah. Bentuk rancangan: Briefing Harian, Review Mingguan/periode, Analisis & Pengecualian, Arsip. Isi minimum: kondisi utama, tindakan terurut, SKU/size, WIP/material/kapasitas, kas–utang–piutang aktual sesuai izin, HPP/margin beserta readiness, data kurang, dan sumber. Satu template deterministik mengonsumsi AnalysisResult; JSX, Reminder dan Tanya AI tidak membuat formula sendiri.

`contracts/report.output.example.md` memberi contoh konkret. Report lama immutable, revisi baru tertaut; periode sebanding, bukan hari berjalan melawan hari penuh tanpa label. Publish on-demand adalah CP7. Distribusi terjadwal mengikuti kontrak notification; format ekspor PDF/Excel baru tidak otomatis menjadi mandat. Jika format tambahan dipilih kelak, renderer mengambil angka yang sama.

Tanya AI V1 mengambil projection authorized dari snapshot tersebut. Prompt berisi tujuan, periode, angka, alasan, asumsi, unknown, source refs, dan pertanyaan; catatan bebas ditandai DATA. Ringkasan volume tidak boleh membuang caveat/source-capacity constraint. Clipboard gagal punya selectable text; popup gagal punya tombol terpisah. Tidak ada query-string payload, API key AI, auto-send atau writeback transaksi dari jawaban AI.

## 6. Adaptive model: selesai bila bisa memilih dengan benar, bukan sekadar tidak error

M01–M08 tetap berlaku. Tambahkan kernel oracle dengan input, initial state, parameter, horizon, expected output, precision/tolerance dan metode independen. Untuk SES fixture teknik: initial10, alpha0,5, observations berikut20 lalu30 → level15 lalu22,5; forecast satu langkah22,5. Ini konfigurasi uji, bukan default pabrik. Setiap kernel yang benar-benar dipilih untuk produk harus mempunyai fixture angka sendiri, termasuk intermittent/zero/unknown bila berlaku; menamai model tanpa implementasi yang terbukti tidak cukup.

Tambahkan **positive promotion**: tiga fold horizon lengkap, tiap actual10; baseline5 dan challenger9 → MAE5 versus1, signed bias−5 versus−1, absolute tail error5 versus1. Dengan policy guard fixture, challenger dipromosikan; tie atau data kurang mempertahankan baseline. Angka ini menguji selector, bukan membuktikan seluruh model belajar dari data nyata. Kernel-fit dan selector wajib diuji terpisah lalu bersama pada dataset memenuhi syarat.

Outer holdout hanya untuk audit estimasi kualitas dan tidak dipakai tuning/seleksi. Perubahan cutoff, backdated-known-later, kalender, range/membership, lead time dan observation availability harus tercatat dalam dependency/model history. Synthetic superiority tidak menjadi janji akurasi/keuntungan pabrik.

## 7. Tiga keluarga reminder bisnis, satu pusat perhatian

`contracts/reminder.rules.json` dan subkartu P16-A…P16-E memisahkan domain tetapi memakai engine/episode/permission yang sama. Source tetap authoritative; tidak membuat ledger utang atau reservation kedua.

| Keluarga | Pemicu | Dasar/penyelesaian yang sah | Yang tidak boleh terjadi |
|---|---|---|---|
| Produksi | Gap size bertanggal, supply telat, pekerjaan outstanding, review status/data | Run terbaru dan perubahan source/coverage yang terbukti | Stok rendah langsung berarti potong lagi; kandidat dianggap FG; Stop menciptakan START_NEW |
| Bahan/aksesori | Tambahan material, ready di lokasi kurang, return perlu inspeksi, valuation/entitlement pending | BOM tertaut, installed, unused eligible, incoming; inspeksi/nilai/settlement menurut intent | Issue dianggap terpasang; customer-owned dianggap milik perusahaan; barang kembali menutup valuation yang belum selesai |
| Utang/piutang | Outstanding due/overdue, jatuh tempo mendekat sesuai policy, credit/payment belum dialokasikan, invoice/cost pending | Invoice/opening+linked payment/credit/reversal, tanggal jatuh tempo sah, scope counterpart | Nominal invoice bruto dianggap masih terutang; credit lintas invoice dihitung dua kali; due date kosong menjadi hari ini |

Contoh AR: invoiceA100+B80, paymentA30, credit20 dialokasikanB → outstandingA70+B60=130. Credit20 yang sama tidak boleh mengurangi keduanya menjadi110. Unallocated credit ditampilkan terpisah sampai aturan aplikasi existing menyatakan applied; jangan membuat urutan alokasi baru. AP memakai lifecycle sumbernya sendiri. Dispute/pending memengaruhi label/tindakan sesuai kontrak; bukan penghapus kewajiban diam-diam. Due date unknown → jumlah outstanding tetap diketahui, overdue unknown.

Setiap rule menyimpan version, scope/lokasi, metric/unit, comparator, threshold/recovery, enabled, severity, due basis, cooldown/quiet policy dan reason. Nol, null, disabled dan invalid dibedakan. Policy inheritance deterministik; nilai contoh tidak aktif otomatis. Preview menunjukkan input dan hasil sebelum disimpan.

Condition observation, episode, attention dan delivery berbeda. ACK/snooze/DONE manual tidak melunasi utang atau menyelesaikan kekurangan. Unknown observation tidak menutup episode. Pulih lalu muncul kembali membuat episode baru tertaut. Schedule reminder tidak mengubah deadline produksi atau tanggal jatuh tempo invoice. Satu status in-app menjelaskan last evaluation, data stale, source action dan history.

## 8. WA: backbone lengkap sekarang, status kesiapan dan aktivasi dipisahkan

Owner kembali menegaskan kebutuhan koneksi WA pada28 September. Karena mandat saat ini **framework**, revisi ini merancang sambungan lengkap dan kasusnya sekarang. Pembagian lama tetap dicatat: CP7 menyediakan engine/reminder/UI serta contract+dry-run readiness; scheduler/worker/provider live dan pembuktian operasi mandiri berada pada CP7C. Jika owner memajukan implementasi kanal ke CP7, pindahkan packet/gate-nya secara eksplisit dengan tes sama; jangan membuang requirement atau mengaktifkannya diam-diam. Provider, penerima, biaya dan tanggal aktivasi belum dipilih oleh pesan ini.

Alur: **source committed → coherent analysis → condition/episode → jadwal/occurrence → authorized digest → outbox intent → adapter → delivery evidence**. Adapter WA tidak menghitung gap/saldo. HTTP provider tidak berada dalam transaksi pembelian/laundry/sales. Event rollback tidak menghasilkan pesan posted.

Kontrak di `contracts/notification.ts` menetapkan schedule, verified recipient binding, message envelope, adapter capabilities dan outcome. Delivery intent unik atas environment+occurrence+binding+channel; payload_hash bukti isi, bukan bagian key untuk membuat pesan baru ketika angka berubah. Scope+source revision+policy+template+access epoch disimpan. Secret berada di server; payload/tampilan tidak menerima token provider. Deep link opaque tetap memerlukan login/izin ERP.

Jadwal mendukung harian/hari pilihan/sekali/H-minus, timezoneAsia/Jakarta, next3times, quiet hours, expiry dan catch-up policy. Konfigurasi baru disabled. Contoh08.00WIB=01.00UTC hanya fixture, bukan jadwal aktif owner. Setelah downtime, usulan coalesce ke ringkasan terbaru; occurrence lama tetap missed/suppressed. Pesan kosong sesuai policy, tidak diisi klaim “semua aman” ketika data gagal.

Sebelum dispatch: recheck rule/schedule version, expiry, source masih relevan, recipient active/opt-in/current scope, destination binding dan freshness. Redact **sebelum** render; total/nama/judul juga dibatasi. Source pulih saat queued → suppress/regenerate dengan intent yang sama sebelum request keluar. Setelah request mungkin keluar, payload attempt dibekukan untuk reconciliation, bukan diganti diam-diam.

Lease+fencing mencegah dua worker memiliki claim sah sekaligus. Gagal sebelum request terbukti boleh retry menurut policy; rejection pasti dicatat; timeout setelah mungkin terkirim → UNKNOWN dan reconcile status/idempotency jika capability tersedia. Tanpa lookup/dedup, tahan blind resend dan tampilkan tugas in-app. ACCEPTED berbeda dari DELIVERED/READ; callback diverifikasi, duplicate/out-of-order tidak menghasilkan efek domain atau status palsu. Tidak menjanjikan exactly-once eksternal. Restore disposable mematikan egress dan merekonsiliasi send watermark sebelum aktivasi real.

Kesiapan tidak boleh diringkas menjadi satu centang: CONTRACT_READY → LOCAL_SINK_VERIFIED → PROVIDER_CONFIGURED → AUTHORIZED_TEST_ACCEPTED → DELIVERY_VERIFIED_IF_SUPPORTED → LIVE_ENABLED. Status unsupported delivery receipt dilabeli, tidak dipalsukan. **Dalam paket ini semua runtime status NOT_RUN; tidak ada nomor dipakai atau pesan dikirim.** Sumber master V2.8–V2.10/RMD-T18–T31 sudah memuat aturan terkait; revisi menghubungkannya ke packet dan kontrak CP7.

## 9. Kerja per keluarga dan aturan selesai yang tidak berputar

`registries/families.json` mengelompokkan22 packet lama; dependency packet tetap berlaku. Keluarga adalah batas kepemilikan/impact/test, **bukan perintah menyelesaikan seluruh keluarga sebelum keluarga lain**. Contributor hanya masuk pada kontrak dan path yang stabil; satu integrator memegang shared schema/routing/ACL/release.

| Keluarga | Packet | Hasil bersama |
|---|---|---|
| F0 Baseline & kontrak | P00/P01 | Accepted receipt, kontrak, independent oracle, mapping source |
| F1 Mesin analisis & apply | P02–P08 | Snapshot/identity/WIP/demand/model/scenario/recovery yang sama |
| F2 Fisik & gudang | P09/P10 | Material/FG/lot/size dan handoff authoritative |
| F3 Keuangan & hak | P11–P13 | Sales/return/payroll/HPP/AR/AP/close reconcile |
| F4 Tampilan & laporan | P14/P15/P17 | Stok/Planner/BR/V1 satu angka dan alasan |
| F5 Reminder & sambungan WA | P16-A…E | Manual/production/material/ARAP episode dan notification readiness |
| F6 Bukti kandidat & paket | P18–P21 | Full flow, scale, independent audit, release receipt |

Sebelum coding keluarga: tulis kontrak, daftar caller/trigger/consumer termasuk lama, fixture sah, expected independen, scope negatif dan exit gate. Untuk bug, cari root cause dan seluruh jalur terdampak; satu finding dapat memiliki beberapa subcase yang tetap terlihat. Jangan menyatukan dua root cause hanya agar jumlah finding kecil.

Sesudah patch: jalankan T1 keluarga dan kontrol tetangga yang terpengaruh. T2 atas kandidat stabil; T3 atas paket qualified. Ulangi bukti bila dependency/permission/schema/clock/lock berubah, bukan hanya karena nomor commit berubah. Perubahan dokumen murni cukup parity yang jujur. Kegagalan fixture tidak menjadi bug produk, dan bukan alasan mengganti expected agar hijau.

Setelah dua percobaan akar sama tidak selesai: hentikan patch gejala, lakukan impact/root-cause review. Setelah tiga kegagalan setup: perbaiki metode/environment. Ini aturan diagnosis, bukan batas yang boleh meninggalkan defect. Tes tambahan harus menutup risiko/mandat spesifik; tidak menambah permutation tanpa tujuan. Status keluarga hanya ACCEPTED bila semua mandatory subcase lulus/disposition sah dan auditor gate terpenuhi.

Receipt pendek: base/head/schema, family+packet, delta kontrak, changed symbols+affected callers, cases PASS/FAIL/INCOMPLETE/NOT_RUN, evidence hash, request ambigu, temuan aktif, owner writer, next exact step. Satu CURRENT_STATE; histori disimpan, tidak disalin ribuan baris setiap ronde.

Writer boleh mengganti/mengeliminasi **usulan teknis** yang kurang cocok dengan delta berisi alasan, pengganti dan coverage yang tetap terlindungi. Kebutuhan owner, batas scope, oracle bisnis dan independent gate tidak boleh hilang lewat eliminasi teknis. Tidak perlu meminta owner memutuskan nama folder, tipe field atau implementasi index.

## 10. Urutan mulai dan pertanyaan yang benar-benar tersisa

Sekarang: review paket revisi, catat keberatan spesifik dan delta; CP6 tetap diaudit/diselesaikan terpisah. Setelah accepted CP6 dan mandat implementasi: P00 mengimpor BD/BE/BF+release; P01 mengunci kontrak v2 dan semua dependency; P02 coherent vertical slice dengan singleton27, grup31–34, draft sale, WIP candidate dan cost pending. Jalankan X01–X12 sebelum consumer mengandalkan payload. Integration lane authoritative sales/material berjalan sesuai dependency, tidak menunggu seluruh halaman selesai.

Nilai produksi nyata—service target, kalender/kapasitas, batch rounding, threshold, penerima/provider WA/jadwal/biaya—belum boleh ditebak. Gunakan fixture dan jalur unknown/disabled; bangun kemampuan dahulu. Jangan bertanya ulang apakah perlu Tanya AI/BR/prioritas/reminder/SKU-range: semuanya sudah diminta. Live activation dan production GO tetap keputusan terpisah.

Revisi ini tidak menjanjikan CP7 tanpa hambatan. Tujuannya membuat hambatan punya pemilik, input yang jelas, bukti penutup dan batas keputusan sebelum writer memulai pekerjaan mahal.
