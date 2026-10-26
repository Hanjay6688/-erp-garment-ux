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
  run40234978669/job121294499742. Complete Original12618120246 aktual
  PASS52/52;3677pin/2prasyarat,24metrik/3602target/fullrestore diperiksa.
- Pendahulu private finance: **a3088e214f5babc46e4016734cce11925acd34d8**,
  actual Native45 PASS45/45,24metrik resmi,3602target dan pemulihan penuh.
  Bukti ini tidak memberi kredit HTTP/browser/pabrik publik.
- Auth3/races7, cron1, used restore8/42kontrol, browser6 dan transport28 disiapkan di branch
  `astra-a/d17-14-frozen-public-followups-prepared-20261026`,
  **71e15908972cd10b0b889988faa8d7d7d1ad3e40**. Kelimanya sudah SOURCE-bound
  pada Original Native52, full admission PASS, dan berjalan pada run40251589438,
  40251591911,40251594620,40251596793,40251598775. Belum kredit runtime.

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
mengganti actor atau memberikan grant uji kepada alur nyata. D17-18 mengizinkan
total analisis besar lebih dari8detik dengan progres nyata. Transaksi/lock
tetap berbatas; batas tiap tahap ditetapkan lewat pengukuran, bukan dinaikkan
otomatis. Operasi harian tetap cepat; sumber dan hasil wajib tetap benar.

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

## Hasil pembacaan B4826a666/f843e4ce dan rencana adapter integrator

B dibaca sampai koordinasi211/head2c39dd09. Caller nativeFrozenQuantity.ts
memakai endpoint operasional v2 pada request, resume dan pembacaan ulang DONE,
termasuk ketika finance_mode STAGED. A dengan sengaja menolak mode tersebut
pada endpoint operasional; caller harus memilih endpoint finance v2 untuk
ketiga jalur itu. UUID/payload/mode tersimpan harus tetap sama pada retry/reload.

Bridge opsional B cp7_frozen_finance_bridge tidak dipasang di atas A terkini:
namespace reader sudah ada pada komposisi A; predecessor fungsi berbeda;
penambahan penanda STAGED sesudah source seal tidak sama dengan kontrak A yang
menyegel penanda sebelum hash. Ini benturan komposisi, bukan alasan mengganti
rumus atau melemahkan guard. Integrator menyiapkan adapter terisolasi A untuk
caller B, mengambil parser waktu nativePlanInstant dan sidecar secara utuh,
serta menjaga backend A dan seluruh bukti lama. Perubahan B-owned integrasi
dicatat lebih dulu di KOORDINASI; cabang dan source asli B tetap utuh.

B melaporkan quantityAuth2/art12618667843 dan controlledBrowser4/art12619095649.
A belum intake kedua Original; controlled browser bukan full package Native.
Tidak ada klaim UI finance baru, factoryPASS, default adoption atau produksi.

## Kandidat caller integrator sudah disiapkan

63d098a0f1a6cc5c4bb78059b7fd2138eda5cf41 pada branch
astra-a/d17-14-frozen-finance-ui-prepared-20261026 menyimpan77berkas caller B
f843e4ce byte-exact dalam namespace integrator. Dua import client panel terarah
ke adapter A; AuthProvider/AuthGate asli tetap.125tes/9file,TypeScript,54modul
build dan17kontrol negatif lokal lulus. Backend qualified A utuh, B tidak ditulis.
DEFERRED eksplisit diterjemahkan menjadi ketiadaan mode pada payload operasional
saja; permintaan tersimpan tidak diubah. STAGED selalu ke financeRPC, termasuk
reopen dan validasi DONE. Tidak ada fallback ke endpoint lain saat gagal.

Suite2layar memakai dua clone penuh terpisah. Desktop meminta laporan resmi
READY pada baseline segar tanpa menambah pekerjaan produksi belum selesai;
bila baseline belum READY, tes gagal dengan alasan asli. HP memakai fixture
posted yang Native52 buktikan BLOCKED dan menuntut angka tetap tersembunyi.
Capture selesai/READY tidak berarti readiness laporan READY.24metrik dan sumber
buku tetap dibandingkan; kemajuan capture SQL tidak diklaim cron atau HTTP.

Finance10 pada71e15908 sudah aktual PASS Auth3/races7, Original12622347557,
3692pin/2prasyarat dan lima packagegate/pemulihan penuh diperiksa. SOURCE UI2
terikat3797pin/dua Original pada aec3feadb56d201e206fa8da8ef5b0014410e663.
Fulladmission tanpaDB lulus; run40257369843/job121361997486 benar-benar berjalan.
Belum bukti kelulusan login/layar baru, factory, analog/cutting B terkini atau
default adoption. Kandidat ini mempertahankan backend dan oracle waktunya;
tidak diberi kredit telemetry D17-18 yang sedang dikembangkan terpisah.

## D17-18: integrasi progres nyata dan waktu tunggu

Keputusan owner lengkap ada pada
../../handoff/HANDOFF_ANALISIS_BESAR_PROGRES_20261026.md. Total8detik tidak lagi
universal untuk pekerjaan besar; tidak ada kenaikan timeout dalam perubahan
sumber di checkpoint ini. Kegagalan pabrik belum diketahui sebabnya dan tetap
diselidiki melalui observer aktual, bukan dianggap timeout.

Persiapan A b048d3fd pada branch astra-a/d17-18-honest-progress-prepared-20261026
menambahkan proyeksi status gabungan dan endpoint telemetry opt-in. Kontrak
scripts/cp7_current_analysis_progress/TELEMETRY_CONTRACT.md dikoordinasikan di
KOORDINASI. Status lama tetap utuh di envelope baru; source B asli tidak ditulis.
Progres memakai unit nyata, total yang belum final tidak diberi persen,
persen tahap tidak dirata-ratakan menjadi keseluruhan. CaptureREADY dengan
reportBLOCKED/LIMITED tetap belum lengkap; waktu tidak menambah progres.

15tesklien baru lulus. Reader PostgreSQL terisolasi9kasus/run40256681136/
Original12622567639 lulus termasuk lockbackend lain dan redaksi hak; pengukuran
fixture kecil2.713ms bukan klaim kecepatan pabrik. Dependensi Auth/status
controlled, bukan actualAuth/fullERP. Composer/inverse penuh, kualifikasi
skala besar, pemasangan layar, deteksi macet serta pemulihan masih terbuka.
