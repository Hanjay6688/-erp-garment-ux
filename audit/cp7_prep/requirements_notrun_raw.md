
## AUD (12 kebutuhan)

| ID | Paket | Skenario kontrak | Expected (ringkas) | Sumber |
|---|---|---|---|---|
| AUD-G01 | P09 | Penerimaan/pembelian frontend belum dibuktikan connected | Resolve/requalify original finding against current accepted source; Gate/roadmap sesuai domain | 2:5784 |
| AUD-G02 | P09;P12 | Nota Mandor/master aksesori masih mempunyai jalur demo lokal | Resolve/requalify original finding against current accepted source; Gate/roadmap sesuai domain | 2:5785 |
| AUD-G03 | P09;P10 | Gudang dan Ganti Merek UI belum menjadi bukti ledger nyata | Resolve/requalify original finding against current accepted source; Gate/roadmap sesuai domain | 2:5786 |
| AUD-G04 | P11 | Penjualan, pembayaran, retur dan refund belum full UI→ledger terverifikasi | Resolve/requalify original finding against current accepted source; Gate/roadmap sesuai domain | 2:5787 |
| AUD-G05 | P12 | Absensi/payroll frontend masih state lokal; denominator/upah tidak boleh ditebak | Resolve/requalify original finding against current accepted source; Gate/roadmap sesuai domain | 2:5788 |
| AUD-G06 | P13;P15;P16 | Layar HPP/finance/close/audit/reminder belum mewakili sumber data resmi | Resolve/requalify original finding against current accepted source; Gate/roadmap sesuai domain | 2:5789 |
| AUD-G07 | P18 | Cakupan Auth/action/location belum lengkap lintas ERP | Resolve/requalify original finding against current accepted source; Gate/roadmap sesuai domain | 2:5790 |
| AUD-G08 | P18 | Parser/upload CSV belum punya bukti transport lengkap | Resolve/requalify original finding against current accepted source; Gate/roadmap sesuai domain | 2:5791 |
| AUD-G09 | P07;P14 | CP7 perencanaan adaptif masih spesifikasi, bukan fitur teruji | Resolve/requalify original finding against current accepted source; Gate/roadmap sesuai domain | 2:5792 |
| AUD-G14 | P19 | Performa dan cakupan interleaving belum diukur untuk beban pabrik | Resolve/requalify original finding against current accepted source; Gate/roadmap sesuai domain | 2:5797 |
| AUD-G15 | P08;P18 | Pagar pending mutation belum dibuktikan lintas seluruh layar/tab | Resolve/requalify original finding against current accepted source; Gate/roadmap sesuai domain | 2:5798 |
| AUD-G16 | P14;P18 | Validasi visual/mobile dan full build terbaru belum dijalankan | Resolve/requalify original finding against current accepted source; Gate/roadmap sesuai domain | 2:5799 |

## BR (39 kebutuhan)

| ID | Paket | Skenario kontrak | Expected (ringkas) | Sumber |
|---|---|---|---|---|
| BR-T01 | P14;P15;P16;P17 | Stok/Planner/popup/Business Report/Reminder membaca run+scope+scenario sama | Semua operand/status/narasi konsisten; tidak ada formula cabang | 2:2773 |
| BR-T02 | P02;P15;P16 | Buka, hitung, filter, baca riwayat, ekspor dan ACK | Ledger FG/WIP/uang/HPP/reservation sebelum-sesudah identik; hanya state analisis/perhatian sah berubah | 2:2774 |
| BR-T03 | P06;P15 | FG18,target48,WIPterarah12,candidateallocation10 | Qdasar18, Qbersyarat8; label bersyarat dan syarat kandidat ada | 2:2775 |
| BR-T04 | P06 | Timeline fixture hari1–10 BR.4 | Saldo akhir14,10,18,14,10,16,20,16,12,8; buffer tidak ganda | 2:2776 |
| BR-T05 | P06 | Incoming12 dipindah hari3→8 | Gapawal hari5 tetap tampak meski total akhir cukup; ETA terlambat tidak hijau palsu | 2:2777 |
| BR-T06 | P04;P06;P16 | Actual-low tetapi tertutup proyeksi WIP | Dua status berdampingan; actual FG tidak ditambah WIP | 2:2778 |
| BR-T07 | P08 | Shared kandidat20 antaraA/B, filter hanyaA, halaman lain/two user | Alokasi bersama total≤20; filter tidak mengembalikan kapasitas atau membocorkan scope | 2:2779 |
| BR-T08 | P04 | Kandidat tanpa SKU, metadata opsional kosong, referensi SKU tarif laundry | Kandidat ditemukan lewat lineage bila cukup; pricing reference bukan finalidentity | 2:2780 |
| BR-T09 | P04 | Revisi/warna/ukuran/bahan konflik | Match ditolak/PerluCek tepat, bukan fuzzy pasti | 2:2781 |
| BR-T10 | P04 | Partial jahit/laundry/QC/FG, rework/rewash, BS/missing/stuck/reversal | Sisa sumber unik benar; no multistage atau incoming double-count | 2:2782 |
| BR-T11 | P05;P11 | Draft→posted→return/cancel; cutoff availability dan demand sisa; order hanya jika existing | Efek draft tidak dikurangi dua kali; forecast/order pada bucket sama tidak diduplikasi; kontrol100−24−20=56 dengan asumsi demand residual ek | 2:2783 |
| BR-T12 | P05;P07 | Stockout, hari tersedia0jual, unknownavailability, promo dan SKUbaru | Perlakuan demand berbeda; no zero demand palsu/mass auto12PCS | 2:2784 |
| BR-T13 | P07 | Forecast horizon/metode/parameter/version/backdated knowledge | Baseline/gate rev3, no future leakage atau salah klaim akurasi | 2:2785 |
| BR-T14 | P06 | Ukuran total cukup tetapi exact size kurang | Gap tetap terlihat, tanpa substitusi size fiktif | 2:2786 |
| BR-T15 | P06 | Qty8→12 oleh policy batch, lusin/PCS serta sisa | Extra4 dan distribusi sah jelas; tidak menjadi seed global atau silent round | 2:2787 |
| BR-T16 | P03;P14 | SKU Stop/Tunda, tanggal review lewat, merek sama nomorSKU | No startbaru/auto-reactivate; pekerjaan lama tetap terlihat; brand lain terpisah | 2:2788 |
| BR-T17 | P13;P15 | Qty lengkap, biaya laundry UNKNOWN/recost pending | Analisis qty berjalan dengan label; margin final/rankingprofit ditahan | 2:2789 |
| BR-T18 | P02;P15 | Quantity query gagal/timeout/null/partialpagination/lineageconflict | Tidak ada0/Cukup/semuaaman palsu; partial per domain eksplisit | 2:2790 |
| BR-T19 | P06;P09 | Kebutuhan BOM, issue, pemasangan aktual, sisa teralokasi, retur dan dua skenario | Issue bukan bukti konsumsi; contoh100 kebutuhan/60terpasang/20sisa terverifikasi→40belum terpasang/20tambahan. Issue80 tanpa sumber tidak me | 2:2791 |
| BR-T20 | P06;P09 | Kain totalcukup tetapi roll tidak cocok; aksesori pos/used/quarantine | Feasibility dan ready qty sesuai real constraint; transfer/PO tidak otomatis | 2:2792 |
| BR-T21 | P06 | Gap100, material/capacity60 | Tulis gap100/feasible60/unresolved40; bukan shortage60 | 2:2793 |
| BR-T22 | P04;P06 | Kapasitas unknown/overloaded, kalender, ETA asumsi | Tidak mengklaim feasible/tepatwaktu; pekerjaan existing diperhitungkan | 2:2794 |
| BR-T23 | P06;P14 | Prioritas tie, role-filter, owneroverride dan HPPpending | Tie stabil; alasan/override terlacak; tidak ada hiddenprofitranking | 2:2795 |
| BR-T24 | P15 | Growth baseline0, margin27→24, agregasi persen | N/A yang tepat;3 poinpersentase; agregasi dari operand, bukan sumpercent | 2:2796 |
| BR-T25 | P11;P13;P15 | Cash actual internaltransfer, unpaidinvoice, AP/ARpartial, refund dan corrections | Kas/revenue/profit/outstanding/duedate tidak tertukar/ganda. Cash forecast bertanggal baru hanya diuji jika scope itu dipilih dan basisnya s | 2:2797 |
| BR-T26 | P10;P15 | Aging stockcohort dibanding lastmovement | Label benar; seluruhstock tidak diklaim tua hanya dari lastsale | 2:2798 |
| BR-T28 | P13;P15 | Contoh pertumbuhan omzet bersamaan laundrydelay, valid HPPdecomposition | Cooccurrence bukan sebab; attribution hanya untuk metode/source sah | 2:2800 |
| BR-T29 | P02;P15 | Tanggalintrahari/WIB dan perangkattimezone lain | Periode/known/effective/generation terpisah; no shiftdate/dayfull comparison palsu | 2:2801 |
| BR-T30 | P13;P15 | Invoice3bulan/backdate/recost, filedreport dan data as-known yang tersedia | Arsip asli utuh; current ditandai stale; revision explicit/scheduled authorized. Tidak rebuild/send semua arsip otomatis; tidak mengarang hi | 2:2802 |
| BR-T31 | P08;P15 | Sumber berubah setelah report/draf, stale deeplink | Arsip historis jelas; refresh/revalidate sebelum apply, no qty dariURL | 2:2803 |
| BR-T32 | P15 | Doubleclick/retry/ambiguouscommit, duarun/worker | Stable request identity; same retry replay; deliberate refresh versi baru; no doublepublishedcurrent | 2:2804 |
| BR-T33 | P02;P15 | Viewer/roleinactive/revoked/unauthorized + API/deeplink/export/cache/history | Semua layer fail-closed; totals/metadata tidak bocor | 2:2805 |
| BR-T34 | P16 | Temuan yang sama muncul tiap report, ACK/snooze/manualDONE | Incident sama; source tidak resolved palsu; reminder tidak membanjir | 2:2806 |
| BR-T35 | P15;P17 | Template unknown/candidate/truncated/catatanberbahaya | Tidak menghilangkan caveat/jika; no arbitrarycode/XSS/instructionexecution | 2:2807 |
| BR-T36 | P02;P15 | Snapshot/metode/policy/template sama; UUID/waktu generate/serialisasi berbeda | Operand/status/narasi dan semantic hash stabil untuk konten sama. Hash artefak byte boleh berbeda karena metadata; canonicalization tidak me | 2:2808 |
| BR-T37 | P02;P19 | Data besar/multipage, beberapa report/user/channel | Complete aggregation, boundedwork, sharedengine; performance dengan angka fixture nyata | 2:2809 |
| BR-T38 | P15;P16 | Generate on-demand; scheduled generation dan delivery diuji pada gate CP7C tersendiri | On-demand teruji tidak berarti scheduler/delivery lulus; reuseV2 dan batas NOT_RUN jelas. Scheduler tidak menjadi blocker tersembunyi BR on- | 2:2810 |
| BR-T39 | P21 | Upgrade/rollback/refusal/restore dan secrets/log/cache | Data/audit terjaga, restoreegressoff; no orphanroute/adapter/schema | 2:2811 |
| BR-T40 | P18 | Full real-wired flow desktop/mobile/iPad: report→SKU→WIP→draf→validapply→refresh | Source/Auth/API/DB/UI terhubung; no optimistic seed, role/race/refetch/stale benar; independent gate sesuai scope | 2:2812 |

## CP7 (35 kebutuhan)

| ID | Paket | Skenario kontrak | Expected (ringkas) | Sumber |
|---|---|---|---|---|
| CP7-01 | P03;P14 | SKU Stop produksi dengan penjualan tinggi dan stok kosong tidak menghasilkan usulan mulai produksi baru. Penjualan stok tersisa dan transaks | SKU Stop produksi dengan penjualan tinggi dan stok kosong tidak menghasilkan usulan mulai produksi baru. Penjualan stok tersisa dan transaks | 2:7032 |
| CP7-02 | P03 | Stop produksi pada satu merek tidak mengubah SKU bernomor sama di merek lain. Bulk action mengikuti pilihan ukuran/range yang benar. | Stop produksi pada satu merek tidak mengubah SKU bernomor sama di merek lain. Bulk action mengikuti pilihan ukuran/range yang benar. | 2:7033 |
| CP7-03 | P03;P04 | Menghentikan SKU dengan WIP berjalan menampilkan dampak tanpa membatalkan/menghapus WIP. Tanggal evaluasi Tunda tidak mengaktifkan produksi  | Menghentikan SKU dengan WIP berjalan menampilkan dampak tanpa membatalkan/menghapus WIP. Tanggal evaluasi Tunda tidak mengaktifkan produksi  | 2:7034 |
| CP7-04 | P04;P06 | FG kosong dan WIP yang relevan sudah di laundry menghasilkan informasi pasokan/ETA dan tindakan yang sesuai. | FG kosong dan WIP yang relevan sudah di laundry menghasilkan informasi pasokan/ETA dan tindakan yang sesuai. | 2:7035 |
| CP7-05 | P04 | WIP tanpa SKU muncul sebagai kandidat dari sumber pola/bahan/ukuran, termasuk ketika metadata opsional SKU kosong. | WIP tanpa SKU muncul sebagai kandidat dari sumber pola/bahan/ukuran, termasuk ketika metadata opsional SKU kosong. | 2:7036 |
| CP7-06 | P04 | Pola/bahan sama tetapi ukuran, warna, revisi atau proses bertentangan tidak berubah menjadi match pasti. | Pola/bahan sama tetapi ukuran, warna, revisi atau proses bertentangan tidak berubah menjadi match pasti. | 2:7037 |
| CP7-07 | P04;P08 | Satu batch kandidat 40 PCS yang cocok untuk dua SKU tidak dapat menutup total 80 PCS pada satu skenario rencana. | Satu batch kandidat 40 PCS yang cocok untuk dua SKU tidak dapat menutup total 80 PCS pada satu skenario rencana. | 2:7038 |
| CP7-08 | P03;P04 | Barang yang berpindah tahap atau menjadi FG hanya dihitung sekali. Reversal, partial, BS, missing, rework, dan rewash mempertahankan sisa ya | Barang yang berpindah tahap atau menjadi FG hanya dihitung sekali. Reversal, partial, BS, missing, rework, dan rewash mempertahankan sisa ya | 2:7039 |
| CP7-09 | P04;P06 | Incoming terlambat/ETA tidak diketahui tidak menutup kekurangan sebelum waktunya atau membuat status aman. | Incoming terlambat/ETA tidak diketahui tidak menutup kekurangan sebelum waktunya atau membuat status aman. | 2:7040 |
| CP7-10 | P05;P11 | Draft penjualan dihitung sekali pada availability dan perpindahan ke posted tidak menduplikasi permintaan. | Draft penjualan dihitung sekali pada availability dan perpindahan ke posted tidak menduplikasi permintaan. | 2:7041 |
| CP7-11 | P05;P06 | Data tipis menghasilkan estimasi berlabel beserta asumsi; angka aktual yang hilang tidak berubah menjadi nol. SKU tanpa histori dapat meliha | Data tipis menghasilkan estimasi berlabel beserta asumsi; angka aktual yang hilang tidak berubah menjadi nol. SKU tanpa histori dapat meliha | 2:7042 |
| CP7-12 | P06 | Range/ukuran kurang tetap terdeteksi walaupun total produk cukup. Pembulatan batch dan konversi UOM menjelaskan selisih dan tidak melanggar  | Range/ukuran kurang tetap terdeteksi walaupun total produk cukup. Pembulatan batch dan konversi UOM menjelaskan selisih dan tidak melanggar  | 2:7043 |
| CP7-13 | P08;P14 | Status SKU, stok, atau sumber batch berubah setelah draf dibuat: penerapan memeriksa ulang dan tidak memakai snapshot kedaluwarsa secara dia | Status SKU, stok, atau sumber batch berubah setelah draf dibuat: penerapan memeriksa ulang dan tidak memakai snapshot kedaluwarsa secara dia | 2:7044 |
| CP7-14 | P02;P08;P17 | Pengguna tanpa hak tidak dapat mengubah kebijakan, mengonfirmasi rencana, atau mengekspor snapshot berisi data di luar haknya. | Pengguna tanpa hak tidak dapat mengubah kebijakan, mengonfirmasi rencana, atau mengekspor snapshot berisi data di luar haknya. | 2:7045 |
| CP7-15 | P17 | Snapshot V1 mempertahankan angka sumber, asumsi, tanggal, dan keterbatasan dengan benar. Tidak ada panggilan API AI berbayar atau penulisan  | Snapshot V1 mempertahankan angka sumber, asumsi, tanggal, dan keterbatasan dengan benar. Tidak ada panggilan API AI berbayar atau penulisan  | 2:7046 |
| CP7-16 | P02;P19 | Dataset dengan banyak SKU/batch tidak terpotong oleh batas halaman UI. Hasil perhitungan memiliki waktu, versi rumus, versi kebijakan, serta | Dataset dengan banyak SKU/batch tidak terpotong oleh batas halaman UI. Hasil perhitungan memiliki waktu, versi rumus, versi kebijakan, serta | 2:7047 |
| CP7-17 | P06;P08 | Skenario kapasitas yang belum diukur diberi label asumsi; perubahan rencana tetap tidak mengubah stok/jurnal sebelum transaksi operasional y | Skenario kapasitas yang belum diukur diberi label asumsi; perubahan rencana tetap tidak mengubah stok/jurnal sebelum transaksi operasional y | 2:7048 |
| CP7-18 | P17 | Clipboard/popup ditolak: prompt tetap dapat disalin manual dan ChatGPT dapat dibuka terpisah. UI tidak mengklaim sukses palsu, tidak mengiri | Clipboard/popup ditolak: prompt tetap dapat disalin manual dan ChatGPT dapat dibuka terpisah. UI tidak mengklaim sukses palsu, tidak mengiri | 2:7049 |
| CP7-19 | P07 | Backtest/pemilihan parameter tidak memakai data masa depan, backdated entry yang belum diketahui saat itu, atau periode uji akhir. Horizon e | Backtest/pemilihan parameter tidak memakai data masa depan, backdated entry yang belum diketahui saat itu, atau periode uji akhir. Horizon e | 2:7050 |
| CP7-20 | P05;P07 | Hari nol saat tersedia, hari stockout, dan availability unknown menghasilkan perlakuan yang berbeda. TSB/model lain tidak menafsirkan stocko | Hari nol saat tersedia, hari stockout, dan availability unknown menghasilkan perlakuan yang berbeda. TSB/model lain tidak menafsirkan stocko | 2:7051 |
| CP7-21 | P07 | Metode fallback dipertahankan bila data tidak cukup atau kandidat tidak memberi manfaat yang memadai. Alasan, versi kebijakan, metrik terdef | Metode fallback dipertahankan bila data tidak cukup atau kandidat tidak memberi manfaat yang memadai. Alasan, versi kebijakan, metrik terdef | 2:7052 |
| CP7-22 | P06;P07 | Mode buffer hari dan buffer statistik tidak dihitung ganda. Target layanan merupakan kebijakan eksplisit; interval statistik dan skenario WI | Mode buffer hari dan buffer statistik tidak dihitung ganda. Target layanan merupakan kebijakan eksplisit; interval statistik dan skenario WI | 2:7053 |
| CP7-23 | P02;P08 | Menjalankan kalkulasi pada runtime yang diuji tidak mengubah data operasional atau reservation. Hak baca dan penyimpanan analisis terpisah d | Menjalankan kalkulasi pada runtime yang diuji tidak mengubah data operasional atau reservation. Hak baca dan penyimpanan analisis terpisah d | 2:7054 |
| CP7-24 | P03;P04 | Satu child batch yang berpindah jahit → DO laundry → receipt → QC → FG hanya menyumbang satu pasokan pada setiap snapshot, termasuk partial  | Satu child batch yang berpindah jahit → DO laundry → receipt → QC → FG hanya menyumbang satu pasokan pada setiap snapshot, termasuk partial  | 2:7195 |
| CP7-25 | P03;P04 | Dua child batch dari satu parent dibedakan dengan benar; batas parent/roll tidak membuat jumlah fisik dapat dipakai dua kali. | Dua child batch dari satu parent dibedakan dengan benar; batas parent/roll tidak membuat jumlah fisik dapat dipakai dua kali. | 2:7196 |
| CP7-26 | P03;P04 | Koreksi potongan sebelum laundry mengubah sisa dan proyeksi size; reversal mengembalikan keadaan melalui event tertaut tanpa menghapus histo | Koreksi potongan sebelum laundry mengubah sisa dan proyeksi size; reversal mengembalikan keadaan melalui event tertaut tanpa menghapus histo | 2:7197 |
| CP7-27 | P04;P12 | Rework GOOD tidak menciptakan produksi baru atau menduplikasi denominator/hasil; rewash, susulan stuck dan BS final mengikuti sisa kumulatif | Rework GOOD tidak menciptakan produksi baru atau menduplikasi denominator/hasil; rewash, susulan stuck dan BS final mengikuti sisa kumulatif | 2:7198 |
| CP7-28 | P04 | WIP laundry 60 PCS dengan ETA tepat waktu menutup proyeksi paling banyak sesuai estimasi hasil baik yang beralasan; jumlah dikirim, diterima | WIP laundry 60 PCS dengan ETA tepat waktu menutup proyeksi paling banyak sesuai estimasi hasil baik yang beralasan; jumlah dikirim, diterima | 2:7199 |
| CP7-29 | P04 | WIP tanpa final SKU dapat ditemukan dari pola+bahan+size meskipun metadata SKU opsional kosong, tetapi konflik revisi/warna/proses menghasil | WIP tanpa final SKU dapat ditemukan dari pola+bahan+size meskipun metadata SKU opsional kosong, tetapi konflik revisi/warna/proses menghasil | 2:7200 |
| CP7-30 | P04;P08 | Satu kandidat yang kompatibel dengan beberapa SKU mengikuti kapasitas sumber dan skenario global lintas halaman; membuka rekomendasi lain ti | Satu kandidat yang kompatibel dengan beberapa SKU mengikuti kapasitas sumber dan skenario global lintas halaman; membuka rekomendasi lain ti | 2:7201 |
| CP7-31 | P03;P14 | SKU Stop dengan WIP terarah tetap menampilkan pekerjaan yang perlu diselesaikan/ditinjau dan gap kebutuhan, tetapi kalkulasi ulang tidak mem | SKU Stop dengan WIP terarah tetap menampilkan pekerjaan yang perlu diselesaikan/ditinjau dan gap kebutuhan, tetapi kalkulasi ulang tidak mem | 2:7202 |
| CP7-32 | P02;P04 | Query WIP gagal, terpotong, timeout atau memiliki konflik lineage menghasilkan **Belum dapat dipastikan**; UI tidak menampilkan hijau/Cukup  | Query WIP gagal, terpotong, timeout atau memiliki konflik lineage menghasilkan **Belum dapat dipastikan**; UI tidak menampilkan hijau/Cukup  | 2:7203 |
| CP7-33 | P04;P08 | ETA asumsi dan ETA berbasis histori dapat dibedakan. Perubahan kalender/kapasitas atau keterlambatan membuat rekomendasi lama stale dan memi | ETA asumsi dan ETA berbasis histori dapat dibedakan. Perubahan kalender/kapasitas atau keterlambatan membuat rekomendasi lama stale dan memi | 2:7204 |
| CP7-34 | P06 | Kebutuhan size 28–30, 31–33 dan 34–36 direkonsiliasi dengan rincian size; surplus satu size tidak menutupi kekurangan size lain tanpa aturan | Kebutuhan size 28–30, 31–33 dan 34–36 direkonsiliasi dengan rincian size; surplus satu size tidak menutupi kekurangan size lain tanpa aturan | 2:7205 |
| CP7-35 | P02;P14;P17 | Menjalankan calculator, membuka popup, drill-down, mengubah filter dan mengekspor Tanya AI tidak mengubah ledger FG/WIP, HPP, jurnal, invoic | Menjalankan calculator, membuka popup, drill-down, mengubah filter dan mengekspor Tanya AI tidak mengubah ledger FG/WIP, HPP, jurnal, invoic | 2:7206 |

## RMD (23 kebutuhan)

| ID | Paket | Skenario kontrak | Expected (ringkas) | Sumber |
|---|---|---|---|---|
| RMD-T01 | P16 | Reminder manual create/edit/DONE/CANCELLED, reload dan pindah perangkat | Server menjadi sumber, legacy lifecycle tidak hilang, data tidak kembali ke seed | 2:3464 |
| RMD-T02 | P16;P02 | Viewer, unauthorized, null/inactive role dan assignee berbeda | Read/write/action scope benar; tombol dan RPC sama-sama menjaga izin | 2:3465 |
| RMD-T03 | P16 | Threshold 120, qty 121/120/119/0 | Comparator persis; boundary equality sesuai policy; nol benar-benar stok habis bukan missing | 2:3466 |
| RMD-T04 | P16 | Qty berulang di sekitar trigger/recovery | Tidak spam/flapping di luar policy; episode dan hysteresis dapat dijelaskan | 2:3467 |
| RMD-T05 | P16 | threshold 0, threshold null, enabled false, input negatif/NaN/format ambigu | Keadaan berbeda dan parsing fail-closed tanpa silent rounding/clamp | 2:3468 |
| RMD-T06 | P16;P13 | Query timeout, malformed, null, partial page, stok yang tidak terbaca | Tidak menulis healthy/resolve/0 palsu; kualitas data dan observasi terakhir tetap terlihat | 2:3469 |
| RMD-T07 | P16 | Override global/kategori/item/lokasi, versi overlap dan perubahan rule | Satu effective policy deterministik; preview sesuai evaluator; histori policy utuh | 2:3470 |
| RMD-T08 | P16;P09 | Stock total cukup tetapi gudang utama rendah; transfer antarlokasi | Alert scope tepat, total tidak double-count; tindakan transfer hanya dari stok yang eligible | 2:3471 |
| RMD-T09 | P16;P09 | Aksesori baru/bekas/karantina/rusak/customer-owned/pos | Ready quantity hanya sesuai policy; unknown value/condition tidak diam-diam dianggap layak | 2:3472 |
| RMD-T10 | P16;P09 | PCS/lusin/gross/pack serta meter/kg | Unit threshold/quantity konsisten; COUNT exact, dimensi decimal sah tidak dibulatkan menjadiPCS | 2:3473 |
| RMD-T11 | P16 | Evaluator dua worker atau run yang sama berulang | Satu incident aktif/episode, observasi tidak menggandakan pekerjaan | 2:3474 |
| RMD-T12 | P16 | ACK/snooze/markmanualDONE pada source otomatis | Perhatian dan fakta dipisah; shortage/invoice tidak selesai palsu; snooze tidak reset umur | 2:3475 |
| RMD-T13 | P16 | Kondisi pulih lalu muncul lagi; rule dinonaktifkan | Episode baru tertaut; disable bukan recovery; recurrence sesuai cooldown | 2:3476 |
| RMD-T14 | P16;P13 | Laundry UNKNOWN/ESTIMATED/AGREED/FREE, invoice partial/matched/payment | Pemicu dan resolusi per price/invoice/cost source benar, tidak membuat invoice atau harga fiktif | 2:3477 |
| RMD-T15 | P16;P09 | Return aksesori sisa baru/nota mandor/bongkaran, partial inspection/value pending | Tugas mengikuti source/condition; physical receipt tidak otomatis menyelesaikan valuation/credit | 2:3478 |
| RMD-T16 | P16;P02 | Backdate, waktu sistem, tanggal buku dan due date reminder | Waktu terpisah; jadwal tidak menggeser transaksi; as-of sesuai policy proyek | 2:3479 |
| RMD-T17 | P16;P13 | Invoice selesai tetapi HPP recost masih pending atau report BLOCKED | Tidak menampilkan nilai final/READY; alert biaya tetap sesuai cakupan yang belum selesai | 2:3480 |
| RMD-T27 | P16;P02 | Owner versus mandor/vendor, scope read berubah dan redacted totals | Tidak ada nama/angka/link di luar izin; global source capacity tetap conserved | 2:3490 |
| RMD-T32 | P17 | Snapshot prompt V1, catatan mirip instruksi, clipboard/popup gagal | Angka/scope/unknown utuh; note data tidak dieksekusi; no paid AI/no query-string prompt | 2:3495 |
| RMD-T33 | P16 | Double click, reload, envelope corrupt, commit success/refetch fail | Sesuai closure AUD-A01–A03/G15; tidak pakai fixture/UUID baru untuk menutupi state belum pasti | 2:3496 |
| RMD-T34 | P16 | Evaluate, open, ACK, snooze, send dan prompt export | Snapshot ledger bisnis sebelum/sesudah identik; hanya data monitoring/notification yang berubah sesuai izin | 2:3497 |
| RMD-T35 | P19;P16 | Banyak barang/penerima/pages, payload terpotong, outbox backlog | Query lengkap/pagination/index terukur; total dan detail tidak mislabeled; pekerjaan bounded | 2:3498 |
| RMD-T36 | P21;P16 | Upgrade/refusal/rollback/backup-restore, scheduler dan send watermark | Definisi/data/ACL/marker/source pin tepat; cleanup nyata; external send history tidak hilang/terulang | 2:3499 |

## UX32 (12 kebutuhan)

| ID | Paket | Skenario kontrak | Expected (ringkas) | Sumber |
|---|---|---|---|---|
| UX32-T01 | P14 | Entry Bagi/Buat Potongan dan Stok/Planner membuka hasil yang sama | Run/scenario/source konsisten; no second calculator; form belum disimpan aman | 2:2119 |
| UX32-T02 | P14 | Kategori/filter, default daftar tindakan, count kartu/SKU/batch | Kategori bukan urutan mutlak; no duplicate intent; cukup/berlebih dapat diakses; count tidak menjumlah unit berbeda | 2:2120 |
| UX32-T03 | P14;P06 | Ranking lintas kategori, tie, ETA unknown dan biaya pending | Alasan terbaca; urutan stabil; unknown tidak dianggap ringan; no hidden profit rank | 2:2121 |
| UX32-T04 | P14 | Satu batch60 untuk gapA42/B30 | Satu kartu sumber, alokasi42+18≤60, sisa12 bersyarat; alternatif tidak dijumlah | 2:2122 |
| UX32-T05 | P14;P19 | Filter merek, pagination/group terpotong, role terbatas | Kapasitas global tidak kembali penuh; total lengkap; sumber tersembunyi tidak bocor | 2:2123 |
| UX32-T06 | P14;P16 | Batch sama: telat fisik dan invoice pending; batch berbeda berpola sama | Intent berbeda tidak hilang; fisik pulih tidak menutup invoice; source berbeda tidak dilebur | 2:2124 |
| UX32-T07 | P14;P06 | Potongan baru berpola sama tetapi beda revisi/material/size/waktu | Hanya kompatibel dikelompokkan; child demand exact; no auto merge; rounding extra terlihat | 2:2125 |
| UX32-T08 | P14;P04 | Detail kecocokan tanpa final SKU, tarif laundry SKU, riwayat tahap | Label/asal benar; pricing bukan hasil final; no multistage doublecount/probabilitas palsu | 2:2126 |
| UX32-T09 | P08;P14 | Source berubah, partial/QC/reversal, dua user apply dan reload | Refresh/review eksplisit; latest-state/locks/idempotency domain; tidak menerapkan data lama | 2:2127 |
| UX32-T10 | P14;P08 | Open/filter/expand/sort/back/tautan vs susun draft/apply | Read tidak menulis ledger atau reservation; command eksplisit terpisah; no qty dari URL | 2:2128 |
| UX32-T11 | P14 | Desktop/HP/iPad, keyboard/fokus/back, form kotor, refetch gagal | Detail satu konteks, no popup stack; tidak lost input/stale success; pesan nyata bukan fixture | 2:2129 |
| UX32-T12 | P14;P15;P16 | Business Report/Reminder/detail SKU menampilkan sumber grup dan status berbeda | Angka sama pada basis sama; arsip vs current jelas; ACK tidak resolve; Stop tidak start baru | 2:2130 |

## WIP (12 kebutuhan)

| ID | Paket | Skenario kontrak | Expected (ringkas) | Sumber |
|---|---|---|---|---|
| WIP-T01 | P04;P06 | FG18/target 60 dan batch 60 kandidat; belum ada SKU final | Tidak langsung memberi perintah produksi42; tampilkan gap, kandidat, syarat dan tindakan cekWIP | 2:3505 |
| WIP-T02 | P08 | GapA42 + gapB30 berebut batch 60 | Skenario bersama maksimal60; contoh42+18 menyisakanB12; bukanA60+B60 | 2:3506 |
| WIP-T03 | P04 | Partial jahit→DO→receipt→QC→FG, rework/susulan/reversal | Sisa unik tetap satu per snapshot; tidak menjumlah counter historis/incoming yang sama | 2:3507 |
| WIP-T04 | P04 | Metadata pola/SKU kosong, histori lineage tersedia, referensi tarif laundry SKU | Bisa menilai kandidat bersyarat tanpa mengarang finalSKU; tariff reference tidak menetapkan output | 2:3508 |
| WIP-T05 | P04 | Pola sama tetapi size/revisi/material/warna/proses tidak cocok atau belum diketahui | Reject/PerluCek tepat; tidak dianggap pasti hanya karena nama sama | 2:3509 |
| WIP-T06 | P06 | WIP tiba terlambat/ETA unknown, actual stok sudah rendah | Tidak menutup gap tanggal awal; actual-low tetap fakta; saran percepat/cek bukan aman palsu | 2:3510 |
| WIP-T07 | P13;P15 | Qty fisik lengkap tetapi biaya laundry UNKNOWN/recost pending | Qty tetap dihitung sesuai sumber; margin tidak dipakai sebagai ranking final; pending terlihat | 2:3511 |
| WIP-T08 | P08 | Dua user apply rencana yang berbagi source, retry dan snapshot berubah | Satu penerapan sah; revalidate/lock/capacity dan request ID; no double order/source consumption | 2:3512 |
| WIP-T09 | P03 | SKU STOP/Tunda, nomor SKU sama beda merek | Tidak start otomatis, stok lama tetap dapat diproses sesuai izin; merek lain tidak ikut berubah | 2:3513 |
| WIP-T10 | P02 | Read-model parsial, row version invalid, source conflict | Tidak ada healthy/0 palsu; planner/reminder sama-sama fail-closed pada scope terdampak | 2:3514 |
| WIP-T11 | P04;P06 | Incoming sudah diterima, RM sudah di-issue, batch tampil di beberapa tahap | Tidak double netting/double demand; raw/accessory dan WIP tidak mengklaim sumber sama dua kali | 2:3515 |
| WIP-T12 | P14;P16 | Planner/popup/reminder/digest/filter membaca skenario sama | Snapshot/hasil konsisten dan redacted; membuka atau mengirim tidak memutasi ledger/reservasi | 2:3516 |