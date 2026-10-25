# Kontrak integrasi A untuk caller frozen publik B — 26 Oktober 2026 WIB

VENI. VIDI. VICI. ERP. — I CONQUERED ERP.
Reliable data adalah dewa. Keuangan termasuk laporan, stok, dan HPP adalah raja.

A tetap pemilik keuangan/stok/HPP/laporan, composer, pemulihan dan integrasi
akhir. B tetap pemilik caller/tampilan produksi dan perencanaan. Dokumen ini
menunjukkan sumber A yang disiapkan saat B membaca baseline A lama f898a71f;
bukan permintaan mengubah scope atau mengadopsi default sebelum bukti lengkap.

## Versi dan bukti yang tepat

- Composer publik A: `scripts/cp7_current_frozen_public_installation.py`,
  dua RPC pada `scripts/cp7_current_frozen_public/bridge.sql` dan `render.py`.
- Kandidat sumber Native52: **6dceb3d3530a2144217047360613808af3249e4a**,
  branch `astra-a/d17-14-frozen-public-native52-20261026`,
  run40234978669/job121294499742. Saat penulisan masih berjalan; bukan PASS.
- Pendahulu private finance: **a3088e214f5babc46e4016734cce11925acd34d8**,
  actual Native45 PASS45/45,24metrik resmi,3602target dan pemulihan penuh.
  Bukti ini tidak memberi kredit HTTP/browser/pabrik publik.
- Auth3/races7, cron1, used restore8/42kontrol, browser6 dan transport28 disiapkan di branch
  `astra-a/d17-14-frozen-public-followups-prepared-20261026`,
  **55e1e317a52f4838e3d1f34a7beea7cc64c41403**. Kelimanya belum SOURCE-bound
  atau dieksekusi; wajib menerima complete Original Native52 yang tepat dahulu.

Versi resmi/main/hosted/default tetap terpisah. `production_go=false`,
`independent_acceptance=false`, status formal keseluruhan5/16.

## Caller publik yang disediakan A

| Tujuan | RPC | Muatan dan batas |
|---|---|---|
| Operasional frozen v2 | `erp_cp7_request_bounded_staged_analysis_v2` | `p_query` kueri operasional resmi dan `p_request` UUID. Finance DEFERRED; tidak membuat capture uang. |
| Frozen v2 dengan angka resmi | `erp_cp7_request_bounded_frozen_finance_analysis_v2` | `p_query` kueri resmi ditambah `finance_mode: 'STAGED'` secara eksplisit; `p_request` UUID. Finance resmi dan referensi frozen disegel bersama. |
| Status/step/pages | RPC staged resmi yang sudah ada | `erp_cp7_get_staged_analysis_v1`, `erp_cp7_step_staged_analysis_v1`, `erp_cp7_read_staged_analysis_pages_v1`. Tidak menulis mesin status alternatif. |

Query operasional terdiri dari `from_date`, `through_date`, `group_mode` sesuai
parser resmi. Jangan mengarang nama mode atau menerima kolom tambahan.
Fasad finance menolak finance_mode yang hilang, DEFERRED, tipe salah atau kueri
asing. UUID yang sama boleh mengulang payload/metode yang sama; lintas metode
operasional/finance atau perubahan payload ditolak. Jawaban hilang harus memakai
UUID dan muatan asli, bukan membuat permintaan baru.

Kedua fasad hanya diberikan kepada authenticated melalui owner yang sempit.
Hak terkini diperiksa setelah lock dan saat replay; foreign/anon/revoked tetap
ditolak. Jangan memanggil schema privat dari browser, memakai service_role,
mengganti actor, memberikan grant uji kepada alur nyata atau melonggarkan8detik.

## Pengikatan dan tampilan hasil

Mode STAGED berada di referensi sebelum segel pertama. Reference/capture/result
harus cocok pada actor, request/job UUID, query, sumber, periode, as_of WIB,
capture/read instant dan mode. Reference frozen v2 dan producer hash dari server
dipertahankan utuh; bukan reference v1 yang diberi label baru.

Operasional boleh selesai dan halaman dapat dibaca ketika finance masih RUNNING.
Original operasional tetap `financial_source=null`; hasil resmi terpisah pada
finance sidecar. READY tidak mengubah halaman/segel operasional yang sudah terbit.
Capture harus tunggal,24metrik/section tepat ke laporan resmi dan signature buku
independen cocok. UNKNOWN tidak memiliki angka buatan. Izin dicabut menyembunyikan
progress/result tetapi tidak mengubah capture historis.

Tidak ada tick/jadwal percepatan dari browser. Cron aktual disiapkan terpisah;
langkah capture SQL pada pengujian Native/Auth tidak diklaim cron atau HTTP.

## Perubahan B terbaru yang dibaca, belum diadopsi A

B **e2ef3a9eeeaae93a861bfabee7c52f01ee8a5e13** memperbaiki pengikatan instant
di `src/nativeAnalysisFinanceSidecar.ts` dengan helper strict microsecond
`nativePlanInstant.ts`. Bukti lokal B:75tes/4file dan TypeScript; perubahan ini
tidak mengubah rumus uang/SQL. Raw clock dan equivalent offset dipertahankan;
selisih satu microsecond, tanggal tidak sah dan24:00 ditolak. A masih mempunyai
parser lama pada kandidat6d; jangan memberi kredit perbaikan B kepada kandidat itu.

Adopsi caller baru harus membawa dependency/parser B versi tepat, bukti Original
sesuai sumber, pemeriksaan klien dan alur aktual. B telah memisahkan Auth pilihan/
quantity yang sudah lulus dari checked cutting SAVE, pabrik/finance dan integrasi
A yang masih terbuka. Sumber B tidak ditulis oleh A pada checkpoint ini.

Saat integrasi akhir, uji UI/caller yang memakai kedua RPC di atas dengan source
yang sama, termasuk replay, akses dicabut, microseconds, status keuangan resmi,
restoration dan seluruh halaman. Regresi layar kebijakan/model/target lama pada
composer baru bukan bukti caller finance frozen baru sudah terhubung.
