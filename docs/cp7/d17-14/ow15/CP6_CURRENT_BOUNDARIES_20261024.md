# CP6 current: batas penerus dan bukti yang masih diperlukan

Inventaris kualifikasi r6 berisi **116 path workflow**, sedangkan rencana menyebut sekitar117. Angka itu historis; jangan menganggapnya daftar run wajib otomatis pada kandidat terbaru. Seluruh path lama masih ada: True. Berkas JSON pendamping memuat SHA sumber dan daftar batas lengkap.

Peta R3 historis mempunyai37entry:14lulus pada kandidat lama,11penerus terpetakan,12batas tanpa penerus penuh. Itu tidak memberi kredit runtime pada kandidat24Oktober. Dua puluh satu kegagalan CP6 dan empat browser baseline yang dicatat rencana tetap dipertahankan; tidak disulap menjadi PASS karena ada adapter baru.

Qualifier current-legacy-ui-browser menjalankan31ID yang sudah ada dalam cp7_prefreeze_legacy_browser.mjs tanpa perubahan:29kasus lama yang dipertahankan ditambah dua P11 connected draft successors. Dua READINESS termasuk29itu. Run40061341301/head5681edbd telah PASS31/31; Original648018byte/SHAcbfd3ac9c94d3e810099b23fc3913b47379a44501c3522b33b29398637524918, Auth/DB bersih dan CP6/advisor/lima gate PASS. Receipt legacy-ui31-5681edbd-pass.json memberi bukti penulis untuk peta layar; ini bukan regresi seluruh arsip CP6 atau penerimaan independen.

Pensiun SALES_MANUAL_13 tetap mengikuti D13-9c/D13-12: auditor harus memutuskan kelengkapan pengganti. Dua kasus asli tetap ada di CP6 beku; hasil writer P11 sekalipun PASS tidak menggantikan keputusan tersebut.

| Workflow historis dengan batas terbuka | Bagian yang belum dibuktikan penuh oleh penerus |
|---|---|
| `cp6-ac-independent-audit.yml` | 55 predecessor cases and admission controls; AD family cases and detector controls; 20 Native5 AD maintenance schedules; AD rollback guards on the original (not re-pinned) file before the release chain |
| `cp6-ad-roll-opening-check.yml` | 7 admission checks on AE; AE two-session original-bug comparison; focused 30 and owner report 11 controls; 4 AF two-session schedules; 20 AF maintenance schedules; 8 rollback refusals on the original AF file |
| `cp6-af-independent-review.yml` | independent AF transaction checks (cp6_af_independent_review.py) |
| `cp6-ag-residual-review.yml` | 21 additional AG writer checks (cp6_ag_residual_review.py) |
| `cp6-ag-sale-reservation.yml` | AG admission checks; AG focused and report checks; 8 AG concurrent transactions; 20 AG maintenance schedules; AF counterexample artifact verification |
| `cp6-ah-independent-review.yml` | independent AH business cases (later folded into the AI focused set, which itself has no current runner) |
| `cp6-ah-return-allocation.yml` | original AG reference validation paths; AH admission, focused and report checks; 8 AH concurrent transactions; 20 AH maintenance schedules |
| `cp6-ai-independent-review.yml` | 12 two-session business schedules (concurrency phase); independent AH capture and restore comparison |
| `cp6-ai-work-source.yml` | AI admission checks; 99 focused + 36 report controls; 16 work/return two-session schedules; 20 AI maintenance schedules; original AH checks with two-allocation fixtures |
| `cp6-ap-flow.yml` | AP browser business cases (accessory edit 5->7 manual price, linked inverse, import edit/finalize); AP HTTP races (pocket period busy/stale retry, same-UUID finalize) |
| `cp6-final-boundary-audit.yml` | AM SQL trial and AN late-PO-draft selector qualification; two-session schedules (16 original, 12 work, 12 transfer, 4 import draft, 12 DRAFT BS/WIP); 20 AM/AN maintenance schedules; controlled midnight transaction; warehouse transfer crossflow; HTTP role/lifecycle oracle and disposable frontend qualification |
| `cp6-initial-import-review.yml` | proposed AP import RPC trial (cp6_initial_import_trial.py); scripts/check-production-recovery.mjs |

Current Native34, Native62, Auth8, Browser19, Browser invoice2, instalasi/restore dan cron mempunyai lingkup sendiri. Tidak satu pun dipakai sebagai pengganti otomatis dua belas baris di atas. Kandidat audit tetap beku; integrasi resmi/main tidak dimajukan; production_go=false.

## Pemetaan kasus current yang disiapkan 24 Oktober

`retained-cp6-case-coverage.json` membagi tepat135ID tanpa duplikat:
99focused dan36detector. Factory asli telah diperiksa: AI99memuat kontrol
AH12, lifecycleAI5, residualAG17, kontrolAH14, saleAF12, draftAG9 dan
AF/AE30. DetectorAI5+AH8+AG12+AF/AE11=36. Empat counterexample AG lama
sudah diganti oleh kontrol AH yang telah ada pada factory asli; mapping
empatnya dicatat, tidak dianggap empat kasus tambahan.

Race36menghindari penghitungan ulang AF4 yang diwarisi AG dan AH8 yang
diwarisi AI. Factory lintas proses asli berjumlah142=AE134+AG8. Seluruh
pemetaan ini adalah pemeriksaan statis dan belum menutup baris arsip.
FirstfailureAI135 di1e0c840f tetap28PASS/107INCOMPLETE pada kedua instalasi.
Kandidat perbaikan seed27ff04fa/run40074044695 dan Race361273950b/
run40073243436 masih aktif ketika catatan ini disusun.
