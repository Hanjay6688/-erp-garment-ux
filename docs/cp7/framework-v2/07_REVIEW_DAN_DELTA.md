# Catatan review dan perubahan revisi2

**Pendapat: setuju arah framework writer. Lengkapi rincian sambungan sebelum kontrak implementasi dikunci.** Tidak perlu membuang framework atau membuat master baru dari nol. Revisi ini dibuat atas permintaan owner28 September dan tetap hanya framework.

| Bagian | Penilaian v1 | Perubahan v2 |
|---|---|---|
| Satu mesin, sumber fisik, unknown, empat waktu | Sudah kuat dan layak dipertahankan | Tetap; output per-target feasibility dan prioritas diperjelas |
| Tanya AI V1 | Sudah tercakup | Template prompt, izin, truncation, fallback terhubung ke case owner |
| Rekomendasi SKU/ukuran dan prioritas | Sudah ada aturan utama | Detail alokasi sumber→target, exact size, action grouping dan edge matching |
| Business Report | Sudah ada menu/template/arsip/metric dictionary | Contoh laporan nyata dan metric scope/periode dalam DTO |
| Reminder produksi/aksesori/AR/AP | Engine/episode generik ada; aturan rinci tersebar di master | Empat rule domain, contoh angka, subpacket dan test closure |
| WhatsApp | Seam CP7 dan runtime CP7C sudah disebut; master V2 lebih rinci | Kontrak lengkap schedule/binding/outbox/adapter/outcome dan kesiapan per tahap; bukan janji sudah terkirim |
| SKU/range terbaru BF | Framework memakai pin sebelum revisi BF | Commercial identity+physical exact member, membership history dan cohort demand |
| Timeline | Prosa sudah membedakan timing/BACKLOG/LOST_SALES | DTO menampung UNKNOWN, unmet/backlog, timing evidence dan gap intrahari |
| Validasi |313 cek persiapan v1 jujur, tetapi tidak membuktikan semantic guard umum | Negative contract probes dan contoh semantic checks; tidak mengaku parser ERP lengkap |
| Adaptive | Eligibility/no-leakage bagus; expected kernel/promotion masih umum | Contoh SES numerik dan positive promotion; tiap kernel terpilih tetap butuh oracle sendiri |
| Cara kerja | A+B/T1/T2/T3 dan satu writer sudah tepat |7 keluarga,10 subpacket,10 owner rows dan32 kasus tambahan yang dapat ditugaskan |

**Tidak ada bug runtime CP7 yang dibuktikan oleh review ini.** Probe v1 memeriksa JSON Schema, bukan endpoint/server. Schema memang tidak harus menanggung seluruh aturan bisnis sendiri; semantic validator wajib melengkapinya. P01 di v1 sudah menjadwalkan finalisasi. Revisi ini membantu writer menutup pekerjaan tersebut lebih awal.

Sumber asli dipertahankan di history/v1, termasuk status313 pemeriksaan yang menjadi bukti paket asal. Bab00–05 memuat aturan sebelumnya dengan pemberitahuan revisi aktif; bab06 mengikat sambungan baru. `registries/requirements.json` tetap271 kelompok warisan, `owner_delta.json` berisi10 kelompok owner yang overlap, `cases.json` berisi84 kontrak kasus **NOT_RUN**. Tidak ada penjumlahan sebagai jumlah fitur unik atau tes produk lulus.

Posisi reviewer setelah pembaruan: review terhadap v1 dibuat mandiri; v2 yang ditulis pada sesi ini adalah usulan rancangan dari reviewer. Validasi sendiri atas v2 bukan independent acceptance atas implementasi masa depan. Writer boleh memperbaiki keputusan teknis dengan delta beralasan dan coverage pengganti; kebutuhan owner dan gate bisnis tetap.

Batas: belum ada code produk, migrasi ERP, native/Auth/browser CP7, scheduler/WA provider, pesan real, atau penetapan biaya/recipient. CP6 HOLD tetap; accepted execution base null. P00 harus membaca hasil BD/BE/BF dan release/last check aktual. Paket ini tidak menyatakan temuan gratis/range sudah sembuh.
