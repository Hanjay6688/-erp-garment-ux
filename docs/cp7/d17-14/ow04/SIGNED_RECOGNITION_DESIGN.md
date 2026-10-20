# OW04: rancangan yang lolos bantahan aritmetika, belum produk

Pin penilaian awal:754f387a04a6b81a8b750db24184444a41bec9df. Perbaikan WA sesudahnya6efdcd78 tidak mengubah kode settlement. Enam pemeriksa memberi penilaian awal sendiri sebelum saling bertukar bantahan; writer memeriksa sumber dan membuat model terpisah. Tidak ada audit independen, penerimaan produksi, atau eksekusi settlement Native di sini.

## Planner yang sedang diprototipekan

Sumber harus berupa event jurnal asli beserta inverse/neutral/effective restatement, dengan pasangan ekonomi/buku yang benar-benar tersimpan. Jangan memfilter hanya header dokumen POSTED: original berstatus REVERSED masih berkontribusi sampai jurnal lawannya. Uang muka yang sudah menjadi sales_payment termasuk P, bukan U kedua kali. Correction root->leaf dan replacement yang memakai tanggal jurnal reversal asal harus tetap terbawa.

Definisikan F(e,b)=max(0, funding(e,b)−net_invoice(e,b)). Setiap event masuk hanya bila tanggal ekonominya<=e DAN tanggal bukunya<=b. Net adalah bruto−retur pada kotak sumber itu; tidak termasuk penerbitan kredit. Untuk return baru, D=F_after−F_before atas SELURUH sumber terkait, bukan satu pembayaran atau retur saja. Komponen pengakuan adalah selisih campuran dua dimensi D pada semua titik perubahan tanggal. Jumlah komponen bersih sama dengan perubahan kredit terkini; penjumlahan baris/kolom mengembalikan kedua profil tanggal. Nilai sen tepat, komponen boleh positif/negatif. Tidak ada tanggal buku bebas yang dipilih pengguna.

`temporal_component_planner.py` memuat expected literal sebelum algoritme:10 kasus pada hasil FIRST, kemudian5 kasus tambahan pada EXTENDED. Hasil15 model cocok, termasuk satu penolakan source-net sebelum sumber penjualan tercatat. Ini bukan validasi bahwa sumber faktual lengkap, poster aman, atau Native berhasil; tidak ada function ERP yang diubah oleh model ini.

Setiap komponen wajib ditautkan ke sumber uang, jurnal/baris/hash dan empat corner values, serta versi kernel. Sebelum menambah kohor, pengakuan yang sudah ada harus cocok dengan F_before dan GL. Jangan menyerap korupsi sebelumnya menjadi kredit baru.

## Bantahan yang mengubah rancangan

- Pendanaan dapat melintas urutan buku setelah reopen:900@18/21 +100@19/19, return200@20/20 memerlukan200@20/21. Per-payment FIFO/max-date salah.
- Bahkan tanpa reversal, sale1000, prior return600, funding600@18/20 +400@19/19, new return200 memerlukan +200@18/20,+200@19/19,−200@19/20. Negatif itu penyesuaian pengakuan, bukan refund kas.
- K terkini0 tidak berarti rencana kosong: pembayaran1000@18 lalu inverse−1000@20, return200@19 memerlukan +200@19−200@20. Wajib ada kohor/history/account choice walau sisa dan refund aman kini0. Hanya komponen benar-benar kosong boleh jalur legacy tanpa pilihan settlement.
- Dua marginal tidak membuktikan satu pasangan tersedia. Pada kasus signed di atas D(18,19)=0 walau kedua marginal masing-masing200. Apply/refund harus melewati semua kotak tanggal berikutnya, termasuk kondisi terkini, bukan hanya dua saldo tersendiri atau saldo saat ini.
- Undo transaksi yang pernah dipakai tetap dihitung pada sejarah: APPLY200@20 lalu inverse@22/23 tidak mengizinkan refund21/21 atau22/22, walau saldo terkini200.
- Later return credit dapat bergantung pada prior return: sale1000/P900; Areturn200->I_A100, Breturn100->I_B100. Reverse A+I_A saja meninggalkan AR100 dan I_B100 tidak didukung. Dependency harus menampilkan B atau koordinasikan seluruh koreksinya; tidak boleh menyembunyikan uang.
- Jika SALE ekonomi18/buku20 lalu reopen dan RETURN ekonomi19, poster RETURN sendiri perlu lantai buku sumber SALE. Memperbaiki hanya jurnal kredit tidak cukup. Lantai sumber harus diterapkan oleh hook sempit dan terbukti, atau profil ditolak atomik; jurnal sumber asli tidak dipindah.

## Batas penulis dan integrasi yang wajib lengkap

Kohor immutable menyimpan mode pilihan, aktor/request/source-return/customer, liability account snapshot sah dan seluruh support vector. Initial net K boleh0, adjustment sesudahnya boleh net negatif; original K tidak ditulis ulang. I adalah NET pengakuan termasuk contras, bukan jumlah komponen positif atau sisa setelah dipakai/refund. Semua consumer/inverse merupakan event immutable tersendiri.

Poster privat menerima ID komponen server saja. Jumlah/akun/tanggal/baris diperoleh dari fakta tertutup dan context terikat PID/tx/actor/request/action/payload/sumber. Private copy Native post_journal harus hash-pinned, mempertahankan period SHARE, cent/balance/source checks, audit, cash triggers dan account_daily_balances; ubah hanya pemilihan tanggal buku yang dibuktikan sumber dan admission sempit. Poster menerima pasangan tepat hasil kernel; jangan mengambil maksimum tanggal semua funding di manifest (akan memindah komponen awal B yang sah). Jika resolver/period berubah sehingga pasangan rencana tidak lagi sah, batalkan dan hitung ulang SELURUH rencana, bukan menggeser atom satu-satu. Seluruh private inverse keluarga note/return correction ikut dikomposisikan dan diverifikasi tepat. Generic journal reverse tidak boleh melewati penulis pemilik fakta.

Urutan kunci nyata: request/CAS -> FG -> affected document rows terurut -> period SHARE -> CASH. Tidak ditemukan satu global-money DB lock; client recovery lock bukan DB serialization. Native payment perlu FG sebelum payment row. Itu juga harus dipasang SEBELUM batch lock pada outer PREPAYMENT20bb dan sebelum payment/header/advance locks pada helper20ba manage_initial_prepayment_v1. Menambah FG hanya di post_sales_payment meninggalkan deadlock nyata. Tidak ada CASH->FG.

Pembaca current E=P+U−I, invoice, history, prepayment target, receivables view, V253/V268 global/wrapper, close blockers, token/dependency/source navigation dan correction replay semuanya harus diubah bersama. Note replay returns-before-payments serta chain inverse payments-before-returns tidak cocok dengan graph baru. Koreksi boleh meminta undo dokumen dependent secara jelas; tidak boleh membuat efek parsial atau mengurangi nominal pembayaran sumber untuk menyamar sebagai refund.

UI quote SEMUA retur. Nonempty recognition plan memerlukan pilihan eksplisit dan akun kewajiban sah, termasuk K0. REFUND adalah full current server K dengan rekening/waktu fisik eksplisit serta sumber book floor yang terbukti; partial apply/refund sesudahnya berada di workspace kredit Native. Tidak memakai opening/import credit dengan batch buatan. Akun aktual harus aktif/postable LIABILITY/CREDIT, bukan kas/mapping/prepayment atau saldo tak terjelaskan; account reuse harus direkonsiliasi dengan lineage Native. Tidak mengarang expiry/default company account. UI harus membedakan P/U/I/E dan original payment tetap nominal aslinya.

## Checkpoint ini tidak menutup OW04

Belum ada Native tables/poster/hooks/API/UI kredit yang terpasang. Pure SQL kernel dan schema/poster sedang disiapkan sebagai usulan di luar kode aktif; jangan memasang salah satunya secara yatim. Native/browser/HTTP/race/fault, saldo keuangan dua basis, exact install/restore dan performa belum terbukti. P11_RETURN_PAID_REFUSAL lama tetap wajib negatif untuk payload yang tidak memilih settlement; calon kasus positif memakai pilihan eksplisit. production_go:false.

## Counter mutasi funding berikutnya

Sumber Native20ap dan CP7 payments belum mempunyai guard AR bertanggal umum. Sale1000/pay1000@18 lalu inverse−1000@20, return200@19 dengan kohor+20019−20020, lalu proposed payment800@18: current capP0+800<=net800 lolos, tetapi funding menjadi1800 sebelum retur. Meminta kernel menerbitkan+80018−80020 akan menyamarkan overfunding sebelum retur dan melampaui face200. Ini harus ditolak oleh sumber/authority, bukan disahkan aritmetika. Counter sumber diperiksa kedua pemeriksa, belum Native runtime.

Guard gross adalah syarat perlu, bukan pengganti planner: funding tidak boleh melebihi source recognized gross pada basis tanggal yang dibuktikan. Jangan menolak semua funding delta positif: pay500@18/inverse20, return200@19, lalu payment400@19 menghasilkan pengakuan sah kandidat+10019−10020 (funding900<=gross1000), meskiK kini0. Bila ordinary return belum mempunyai akun/kohor, penulis berikutnya perlu pilihan akun/pengakuan yang sah atau jalur undo yang jelas, bukan default tersembunyi. Kasus ini tetap bagian integrasi yang belum selesai.

Kernel SQL murni siap pada subfolder pure-kernel/:23 planning,12 capacity,17 malformed serta5 kontrol menghasilkan57 PASS di PGlite. Root menjalankan ulang salinan portabel; bukan posting Native atau bukti sumber/jurnal/permission. Akun, inverse pairing, source completeness, return attribution, tanggal sah, permintaan dan admission TIDAK dibuktikan kernel. Tidak ada fungsi SQL itu dalam bundle produk.

## Atribusi keluarga retur sesudah pemeriksaan silang

Setiap logical return family mendapat ordinal immutable di bawah FG, termasuk return yang mula-mula tidak menghasilkan kredit. Koreksi mempertahankan ordinal root. Target T_i = F(SALE+funding+keluarga<=i) − F(SALE+funding+keluarga<i). Perubahan berikutnya mem-post selisih target tepat per pasangan dikurangi SEMUA retained signed I, bukan originalK atau delta seluruh nota yang ditaruh pada satu kohor. Rekonsiliasi awal F(noReturns)=0 dan NET setiap keluarga<=0 di SELURUH joint prefix wajib. Ini aturan atribusi internal yang tidak mengubah pilihan owner; fakta sumber masih harus membuktikannya.

Counter independen: sale1000/funding900, R1=200 menghasilkan100 dan R2=100 menghasilkan100. Setelah memakai100 dari R1, inverse funding100 membuat target R1=0/R2=100. Saldo gabungan0 menyembunyikan defisit R1−100. Harus menolak atau undo/replay konsumennya secara owning compound, tidak meminjam R2 diam-diam. Original face tetap sejarah; E harus memakai signed adjusted I, bukan originalK yang menyebabkan AR palsu100.

Floor juga berlaku untuk SETIAP return, termasuk rencana kredit kosong. RootSALE17/buku20, corrected leaf17/buku17, rootRETURN19/buku22: replacement/family inverse harus mempertahankan book floor root22 yang dibuktikan lineage. Helper restate_reversal lama mem-post effective inverse di original economic melalui resolver saat ini; setelah reopen ia bisa membuat inverse terlihat SEBELUM original book22. Karena itu actual neutral/effective/restatement sources juga wajib dipasangkan, bukan hanya Native reversal header. Belum ada klaim runtime bahwa jalur baru aman.

Jurnal kredit yang dibatalkan melalui Native JOURNAL_REVERSAL mempunyai descendant yang generic reverse juga harus tolak. Proteksi source-name langsung saja tidak cukup; walk ancestry cycle-safe dan facts linkage wajib. Penyesuaian positif sesudahnya wajib review akun/settlement baru; niat REFUND awal tidak mengizinkan refund kedua otomatis.
