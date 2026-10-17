# R3-08 — Pemetaan penerus workflow CP6 lama pada kandidat r2 `2e9d6a46`

Dari 22 workflow CP6 yang merah di receipt r2, 11 sudah punya penerus yang menjalankan kasus yang sama dan hasilnya
terbaca di log receipt yang sama, sedangkan 11 tetap menjadi batas karena sebagian isinya tidak dijalankan workflow mana
pun sekarang; dari 15 workflow lain yang ikut disentuh R2-08, 14 lulus di kandidat dan 1 tidak pernah dijalankan (juga
batas). Penjaga sejarah tidak dilonggarkan, tidak ada workflow yang dijalankan ulang untuk dokumen ini, dan status merah
asli tetap tercatat di run aslinya.

Data lengkap per workflow (galat pertama, langkah yang gagal, isi uji, penerus, bagian yang belum tercakup):
`R3_08_CP6_WORKFLOW_SUCCESSORS.json`. Berkas ini ringkasannya. Sumber temuan: laporan Astra r2 §5.

## 1. Ringkasan

| Status | Jumlah | Arti |
|---|---|---|
| Lulus di kandidat (`PASSES_ON_CANDIDATE`) | 14 | Workflow itu sendiri hijau di receipt r2 |
| Penerus terpetakan (`SUCCESSOR_MAPPED`) | 11 | Setiap kelompok uji yang dulu dijalankan punya pelari sekarang di receipt r2, dan hasilnya dibaca dari log |
| Batas tanpa penerus (`BOUNDARY_NO_SUCCESSOR`) | 12 | Ada bagian yang tidak dijalankan siapa pun sekarang. Bagian yang masih dijalankan dicatat di `partial_successor`, sisanya di `uncovered` |
| **Jumlah** | **37** | 22 merah + 14 hijau + 1 tidak dijalankan |

| Jenis kegagalan (`failure_kind`) | Jumlah | Penerus | Batas | Lulus |
|---|---|---|---|---|
| Penjaga cakupan sumber sejarah (`SOURCE_SCOPE_GUARD`) | 20 | 10 | 10 | — |
| · membandingkan daftar berkas yang berubah (`CHANGED_FILE_LIST`) | 11 | 9 | 2 | — |
| · menolak merge sesudah commit patokan (`NO_MERGE_AFTER_PIN`) | 9 | 1 | 8 | — |
| Artifact kedaluwarsa (`EXPIRED_ARTIFACT`) | 1 | — | 1 | — |
| Ada kasus INCOMPLETE (`INCOMPLETE_CASES`) | 1 | 1 | — | — |
| Lulus (`PASS`) | 14 | — | — | 14 |
| Lain: tidak dijalankan (`OTHER`) | 1 | — | 1 | — |
| **Jumlah** | **37** | **11** | **12** | **14** |

| Langkah bootstrap AC (`Restore exact AC runtime`, untuk G-01 langkah rebuild) di run r2 | Jumlah |
|---|---|
| Berjalan dan lulus | 19 (14 yang hijau, ditambah AS Independent AR Audit, AS Writer Qualification, AT Independent AS Audit, AU Independent AT Review, Auditor Scenario) |
| Tidak tercapai (run berhenti di penjaga atau artifact sebelum langkah itu) | 17 |
| Workflow tidak dijalankan | 1 |

## 2. Jawaban atas butir Astra §5

- **20 penjaga cakupan sejarah.** Semuanya tetap merah dengan galat yang sama. 11 membandingkan daftar berkas yang
  berubah sejak commit patokannya; di kandidat daftar itu berisi sekitar 7.700 berkas (`AT_SCOPE`, `AU_SCOPE`,
  `AS_SCOPE`, `AUDITOR_SCOPE`, `AS_PROBE_SOURCE_SCOPE`, dan daftar tanpa label). 9 menolak merge sesudah commit
  patokan: patokannya leluhur kandidat, dan sesudahnya ada 6 merge (`e43e0ed4` sampai `b3b15254`). Penjaga ini hanya
  bisa lulus di commit sejarahnya sendiri. Tidak ada yang diubah.
- **1 artifact kedaluwarsa.** CP6 AF Posted Child Family mengunduh artifact AE 10418502157:
  `gh: Artifact has expired (HTTP 410)`. Di belakangnya masih ada penjaga "one writer head": kepala cabang
  `competition/cp6-j-closure-20260911` harus sama dengan commit yang diuji, padahal kepala cabang itu `ca7f0955`. Jadi
  walau artifact masih ada, run di kandidat tetap akan berhenti.
- **CP6 Auditor Scenario** (run 38906744394): 166 PASS (native 104, race 26, HTTP 9, browser 27) dan 4 INCOMPLETE.
  Keempatnya punya penerus di receipt yang sama: (a) leg browser T3 dengan UI CP6 beku `e43e0ed4`: 31/31 PASS,
  termasuk keempat kasus itu; (b) CP7 Pre-freeze UI Regression (UI cabang ini dengan tumpukan CP7): pasangan READINESS
  PASS; pasangan `SALES_MANUAL_13` sudah dipensiunkan (`docs/cp7/RETIRED_CP6_SALES_MANUAL_13.md`) dan penggantinya
  `P11_DRAFT_BROWSER_DESKTOP` / `_MOBILE_RECOVERY` PASS. Empat INCOMPLETE tetap tercatat. Penyebabnya UI dan tumpukan
  yang tidak cocok, bukan oracle yang diganti.
- **37 bootstrap yang disentuh.** Hanya 19 yang terlihat menjalankan bootstrap AC sampai lulus di kandidat. 17 berhenti
  sebelum langkah itu, 1 tidak dijalankan. Jadi "37 disentuh" bukan "37 diterima"; angka yang terbukti 19.
- **Klaim yang didukung:** kasus AR 174, kasus asli 326 + AS 34, AT 16 + AU 15 dengan race-nya, dan siklus
  pasang/rollback 30 berkas paket AC..BF berjalan di kandidat (§4). **Klaim yang tidak didukung:** "regresi seluruh
  arsip CP6 lengkap". 12 workflow tetap batas. Bagian yang tidak punya pelari sekarang tercantum per workflow; sebagian
  besar berupa kasus fokus/detektor, jadwal dua sesi dan 20 jadwal pemeliharaan keluarga AD..AI, alur browser AP, dan uji
  HTTP peran di Final Boundary Audit.

## 3. Hasil mentah yang tidak semuanya PASS

- **CP6 T2 Combined Regression hijau, tetapi status mentahnya tidak semua lulus.** Fase temporal WRITER_PASS. Fase
  regression DISPOSITION_REQUIRED: 230/31/65 sama per kasus dengan hasil AU; dari 34 kasus AS, 25 PASS, 8 COUNTEREXAMPLE
  yang cocok dengan oracle tanggal yang disetujui owner 24 Sep (8/8 MATCH), 1 INCOMPLETE `ADJUSTMENT_DATE:False` yang
  cocok dengan oracle B; 4 kasus AO INCOMPLETE yang cocok dengan oracle B. Fase ar DISPOSITION_REQUIRED: 1 INCOMPLETE
  `ACCESSORY_CONNECTED_ZERO`, ditolak kebijakan harga gratis BC; kasus penggantinya PASS. Karena itu penerus utama untuk
  regresi kasus adalah CP6 AV Rev2 Qualification, yang ketiga fasenya WRITER_PASS.
- 12 kasus `DATE_POLICY_REVIEW_REQUIRED` di kelompok bisnis adalah HOLD sejarah yang dipertahankan, bukan PASS.
- "Lulus di kandidat" berarti gerbang workflow itu sendiri lulus. Probe T1 (AW..BD), S06 dan probe identitas AU bergerbang
  REVIEW_COMPLETE (pengamatan); isi per kasus di log probe itu tidak dibaca ulang di sini.
- Penerus pasang/rollback memakai berkas paket rilis T3. Pin penjaganya diambil ulang untuk baseline setara hosted
  (keputusan G-01 opsi b); ketegasan penjaganya sama. Rollback berkas migrasi asli AC..AV dibuktikan ditolak di rantai
  rilis.
- Kasus CROSS yang mengimpor ulang (DAY:*:IMPORT) mengharapkan penolakan batch versi AL
  (`cp6_v2620al_review.crossflow_case`), bukan teks penolakan AF yang lama.

## 4. Penerus yang dipakai

Semua run ada di receipt r2 kandidat `2e9d6a46`; hasilnya dibaca dari log job yang disebut.

| Kode | Workflow | Run / job | Yang terbaca di log |
|---|---|---|---|
| AV-T | `cp6-av-qualification.yml`, fase temporal | 38894906555 / 116952942805 | WRITER_PASS: AT 16/16, race 4/4, AU 15/15, race 6/6 |
| AV-R | `cp6-av-qualification.yml`, fase regression | 38894906555 / 116952942990 | WRITER_PASS_WITH_12_PRESERVED_HISTORICAL_HOLD: bisnis 179 PASS + 39 CONTROL_PASS + 12 HOLD, impor 31/31, nilai 65/65 (sama dengan hasil AU), kasus AS 34/34 |
| AV-Q | `cp6-av-qualification.yml`, fase qualify | 38894906555 / 116952943034 | WRITER_PASS: AR 146/146 (termasuk 10 kasus `*_ORIGINAL_PROBE`) + race 28/28; siklus paket AV PASS |
| T2-T | `cp6-t2-regression.yml`, fase temporal | 38894953291 / 116953095723 | WRITER_PASS: 16, 15, race 4 dan 6 |
| T2-R | `cp6-t2-regression.yml`, fase regression | 38894953291 / 116953096046 | DISPOSITION_REQUIRED (lihat §3) |
| T2-AR | `cp6-t2-regression.yml`, fase ar | 38894953291 / 116953096109 | DISPOSITION_REQUIRED: 145 PASS + 1 INCOMPLETE (ada kasus pengganti), race 28/28 |
| T3-I | `cp6-t3-release-package.yml`, install | 38894956452 / 116953107133 | 30/30 berkas AC..BF terpasang; runtime BF native 104, race 26, HTTP 9 |
| T3-B | `cp6-t3-release-package.yml`, browser (UI beku `e43e0ed4`) | 38894956452 / 116953107230 | Alur browser AU 10/10, browser BF 31/31 |
| T3-RB | `cp6-t3-rollback.yml` | 38894959114 / 116953114818 | 147/147: rollback dua siklus, pasang ulang sama, tolak sesudah dipakai, tolak urutan salah dan admisi terbuka |
| PF | `cp7-prefreeze-ui.yml` | 38895103214 / 116953583459 | 31 PASS, termasuk READINESS dan P11_DRAFT_BROWSER desktop/HP |
| AT-AS | `cp6-at-audit.yml` langkah 27 dan 29 (di dalam run merah itu sendiri) | 38894883219 / 116952866896 | Skrip AS yang sama (byte-identik) dari commit AS beku `8a170ce9`: kualifikasi 174 WRITER_PASS; regresi 326 + 34 WRITER_PASS_WITH_12_PRESERVED_HISTORICAL_HOLD |
| UX | `ci.yml` (Build UX) | 38894648562 / 116952099934 | 215 berkas uji lulus, termasuk 8 berkas uji impor/form yang dulu dijalankan Initial Import |

## 5. Per workflow

"Daftar" = penjaga daftar berkas yang berubah; "merge" = penjaga tolak merge sesudah commit patokan.

| Workflow (berkas) | Run r2 | Hasil r2 | Bootstrap AC | Status | Penerus, atau yang belum tercakup |
|---|---|---|---|---|---|
| `cp6-ac-independent-audit.yml` (AD Whole Family Qualification) | — | Tidak dijalankan: hanya pemicu push ke cabang kompetisi | Tidak dijalankan | Batas | Sebagian: T3-I, T3-RB (berkas AD). Belum: 55 kasus pendahulu, kasus keluarga dan detektor AD, 20 jadwal pemeliharaan |
| `cp6-ad-roll-opening-check.yml` (AF Posted Child Family) | 38894846530 | Merah: artifact AE kedaluwarsa (HTTP 410) | Tidak tercapai | Batas | Sebagian: Combined134 di CROSS:142 (AV-R, T2-R), T3-I, T3-RB. Belum: 7 cek admisi, perbandingan dua sesi AE, 30 fokus + 11 kontrol laporan, 4 jadwal dua sesi, 20 jadwal pemeliharaan |
| `cp6-af-independent-review.yml` | 38894849298 | Merah: merge | Tidak tercapai | Batas | Sebagian: T3-I, T3-RB. Belum: cek transaksi AF independen |
| `cp6-ag-residual-review.yml` | 38894851987 | Merah: merge | Tidak tercapai | Batas | Sebagian: T3-I, T3-RB. Belum: 21 cek tambahan AG |
| `cp6-ag-sale-reservation.yml` | 38894854683 | Merah: merge | Tidak tercapai | Batas | Sebagian: CROSS:142 (AV-R, T2-R), T3. Belum: admisi, fokus/laporan, 8 transaksi bersamaan, 20 jadwal pemeliharaan |
| `cp6-ah-independent-review.yml` | 38894857288 | Merah: merge | Tidak tercapai | Batas | Sebagian: T3. Belum: kasus bisnis AH independen |
| `cp6-ah-return-allocation.yml` | 38894860217 | Merah: merge | Tidak tercapai | Batas | Sebagian: CROSS:142, T3. Belum: jalur validasi referensi AG, admisi/fokus/laporan, 8 transaksi bersamaan, 20 jadwal |
| `cp6-ai-independent-review.yml` (AI-R2) | 38894862576 | Merah: merge | Tidak tercapai | Batas | Sebagian: WORK:23 (AV-R, T2-R), T3. Belum: 12 jadwal dua sesi, tangkap dan bandingkan AH |
| `cp6-ai-work-source.yml` | 38894865676 | Merah: merge | Tidak tercapai | Batas | Sebagian: 142 ekspektasi gabungan = CROSS:142 (AV-R, T2-R), T3. Belum: admisi, 99 fokus + 36 kontrol laporan, 16 jadwal dua sesi, 20 jadwal pemeliharaan |
| `cp6-ao-ap-package.yml` | 38894868681 | Merah: daftar | Tidak tercapai | Penerus | T3-I, T3-RB: pasang, rollback dua siklus, pasang ulang sama, tolak sesudah dipakai, tolak admisi terbuka (berkas paket dengan pin baru) |
| `cp6-ap-flow.yml` | 38894871775 | Merah: daftar | Tidak tercapai | Batas | Sebagian: T3-I, T3-RB, login Auth asli di T3-B. Belum: kasus bisnis browser AP dan race HTTP AP |
| `cp6-ar.yml` | 38894874885 | Merah: daftar | Tidak tercapai | Penerus | AV-Q (AR 174 WRITER_PASS), T2-AR, T3-I, T3-RB |
| `cp6-as-audit.yml` | 38894877443 | Merah: daftar (`AS_PROBE_SOURCE_SCOPE`) | Lulus | Penerus | Kasus AS 34 memanggil fungsi probe yang sama: AV-R 34/34, AT-AS 34/34; T2-R |
| `cp6-as-qualification.yml` | 38894879960 | Merah: daftar (`AS_SCOPE`) | Lulus | Penerus | AT-AS: skrip yang sama lulus penuh di receipt yang sama; AV-R, AV-Q, T3 |
| `cp6-at-audit.yml` | 38894883219 | Merah: daftar (`AUDITOR_SCOPE`) di langkah terakhir; langkah AS 174 dan 326 + 34 lulus | Lulus | Penerus | AT-AS (run itu sendiri); probe AT diteruskan oleh kasus AT 16 (AV-T, T2-T) |
| `cp6-at-qualification.yml` | 38894886372 | Merah: daftar (`AT_SCOPE`) | Tidak tercapai | Penerus | AV-T, T2-T, T3-B (skrip browser yang sama, 10 kasus), AV-Q, AV-R, T3 |
| `cp6-au-capture.yml` | 38894889379 | Hijau | Lulus | Lulus | — |
| `cp6-au-identity-review.yml` | 38894892139 | Hijau | Lulus | Lulus | — |
| `cp6-au-qualification.yml` | 38894895108 | Merah: daftar (`AU_SCOPE`) | Tidak tercapai | Penerus | AV-T, T2-T, T3-B, AV-Q, AV-R, T3 |
| `cp6-au-review.yml` | 38894897981 | Merah: daftar | Lulus | Penerus | AT 16 dan 4 kasus MASTER (bagian dari AU 15) di AV-T, T2-T |
| `cp6-auditor-scenario.yml` | 38906744394 (run 38894900810 hijau) | Merah: 166 PASS, 4 INCOMPLETE | Lulus | Penerus | T3-B (31/31 di UI beku), PF (READINESS dan pengganti `SALES_MANUAL_13`) |
| `cp6-av-capture.yml` | 38894903459 | Hijau | Lulus | Lulus | — |
| `cp6-aw-t1-probe.yml` | 38894909366 | Hijau | Lulus | Lulus | — |
| `cp6-ax-t1-probe.yml` | 38894912157 | Hijau | Lulus | Lulus | — |
| `cp6-ay-t1-probe.yml` | 38894915040 | Hijau | Lulus | Lulus | — |
| `cp6-az-t1-probe.yml` | 38894918406 | Hijau | Lulus | Lulus | — |
| `cp6-ba-t1-probe.yml` | 38894921801 | Hijau | Lulus | Lulus | — |
| `cp6-bb-t1-probe.yml` | 38894924607 | Hijau | Lulus | Lulus | — |
| `cp6-bc-t1-probe.yml` | 38894927735 | Hijau | Lulus | Lulus | — |
| `cp6-bd-t1-probe.yml` | 38894930970 | Hijau | Lulus | Lulus | — |
| `cp6-final-boundary-audit.yml` | 38894936507 | Merah: merge | Tidak tercapai | Batas | Sebagian: bisnis 230, impor 31, nilai 65 (AV-R, T2-R), T3. Belum: uji SQL AM, selector AN, jadwal dua sesi, 20 jadwal pemeliharaan, transaksi tengah malam, alur transfer gudang, uji HTTP peran. Env yang dikomit (`CP6_AM_TRIAL`/`CP6_AM_FULL` false) juga membuat langkah yang sama menolak |
| `cp6-g01-baseline.yml` | 38894938993 | Hijau | Lulus (langkah rebuild) | Lulus | — |
| `cp6-initial-import-review.yml` | 38894941618 | Merah: daftar | Tidak tercapai | Batas | Sebagian: kasus AO di T2-R, impor 31 (AV-R), 8 berkas uji form di UX, T3. Belum: uji usulan RPC impor AP (`cp6_initial_import_trial.py`) dan `check-production-recovery.mjs` |
| `cp6-opening-overlap.yml` | 38894944586 | Merah: daftar | Tidak tercapai | Penerus | 10 kasus `*_ORIGINAL_PROBE` di AV-Q (10/10 PASS: duplikat sekarang ditolak), T2-AR |
| `cp6-s06-close-probe.yml` | 38894947308 | Hijau | Lulus | Lulus | — |
| `cp6-successor-qualification.yml` | 38894950186 | Merah: merge | Tidak tercapai | Penerus | AV-Q, AV-R, T2-AR, T2-R |
| `cp6-t2-regression.yml` | 38894953291 | Hijau (status mentah dua fase DISPOSITION_REQUIRED, §3) | Lulus | Lulus | — |

## 6. Cara dokumen ini dibuat

- Daftar run: `../cp1-7-r2-20261016/CI_RECEIPT.json`. Langkah dan hasil job: API job GitHub Actions (hanya membaca).
  Galat pertama dan jumlah kasus: log job r2, hanya dibaca, disimpan sementara di luar repo dan tidak dikomit.
- Penerus hanya dicatat bila workflow sekarang di receipt yang sama menjalankan deklarasi kasus yang sama atau perilaku
  yang sama, dan lognya sudah dibaca. Modul kasus AR/AS/AT/AU dibandingkan byte demi byte antara commit beku
  (`8a170ce9`, `ca7f0955`) dan kandidat: identik, kecuali `cp6_au_browser_ui.mjs` (12 baris, kolom merek CP7); penerus
  browser memakai salinan beku `e43e0ed4`.
- Bukti cacat lama, yaitu contoh-penyangkal pada generasi sebelum perbaikan (misalnya probe overlap di AQ), tidak
  diulang. Itu bukti sejarah, bukan regresi kandidat.
- Tidak ada workflow yang dipicu atau diulang. Tidak ada penjaga, oracle atau berkas workflow yang diubah.
  `production_go:false`.
