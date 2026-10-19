# Astra r5 — retest selesai, paket laporan final

Kandidat `17fa25075ba77f0853c3c16f504288ace03eec35`; writer `2766a9092f51f240267b9cbe1201d49a836fb490` tetap sama. Seluruh run terdaftar selesai. Ada 396 slot cakupan PASS dari 398 eksekusi (396 PASS + 2 INCOMPLETE awal AUDITOR_TOOL, dengan Q2 PASS untuk kedua kasus). Lihat RETEST_ASTRA_17fa2507.md, FINDINGS.json, CANONICAL_RESULTS.json dan REPORT_LOCK.json.

R5-01 tertutup; R5-02 lulus fungsi pada cakupan yang diuji. Finance 100 target: 1.883/1.952/2.192 detik; 300 target: 6.567/6.766/7.748 detik; 1000/5000 direct finance ditolak pada batas statement 8 detik. Staged operasional 5000 target selesai 58.958–75.807 detik. KNOWN-P19-DIRECT-LATENCY tetap S2 terbuka untuk cakupan keseluruhan.

Tidak ada perubahan produk/main/writer/hosted/deployment/PR atau pesan. Tidak ada rerun job; satu kualifikasi alat baru dengan expected tetap. Belum membaca hasil peserta r5 lain. Laporan dikunci oleh commit yang memuat REPORT_LOCK.json sebelum penyatuan. Retest selesai terpisah dari feature_complete/audit_complete/production_go; ketiganya untuk keseluruhan ERP tetap false. Pertahankan batas CP2, 12 legacy, A2, FABLE-012 deferred, preflight/non-superuser/shadow/production restore/iPad/WA live.
