# Pemeriksaan independen AY rev7.2 + AZ rev2 (`b110e54`) — repro (T1_FAMILY, bukan bukti rilis)

Pemeriksa: sub-agent read-only, database stub sekali pakai sendiri (`rev72r_*`). Skrip disalin apa adanya; `\ir` di dalamnya
menunjuk folder harness pemeriksa (ganti ke `../rev7-harness/scenarios/common_lot.sql` bila dijalankan dari repo).

| Temuan | Tingkat | Repro | Disposisi (rev7.3 / AZ rev2) |
| --- | --- | --- | --- |
| 1. Bagian kantong dibandingkan dengan versi sebelum statement, bukan dengan yang diposting sync terakhir | MAJOR | p3, p5, p6 | Per pool terhadap state lot (`pocket_by_pool`); harness r18 |
| 2. Satu tanggal kantong (maks akhir periode) untuk semua pool | MAJOR | p1, p2 | Tiap pool pada tanggal recost-nya; harness r18 |
| 3. Non-PO: baseline versi sebelum statement (dua recost dalam satu statement) | MAJOR | n1 | Baseline `opening_lot_hpp_gl_state.current_hpp`; uji `rev2-logic/nonpo_two_recosts` |
| 4a. Jurnal recost aksesori juga di jalur non-invoice/E tertutup | MAJOR (kebijakan) | kode | Dipertahankan: tanpa jurnal itu WIP PO bergeser di semua jalur (lihat handoff §26) |
| 4b. Jurnal recost aksesori tidak ikut dibatalkan bersama akrual | MINOR | kode | Dibatalkan di `reverse_qc`, `reverse_rework_completion`, `complete_initial_import_wip_v1` |
| 5. Lot VOIDED: bagian kantong tanpa tanggal | MINOR | p4 | Rata-rata perubahan per pool lot hidup; harness r19 |
| 6. Join `any(mids)` tanpa indeks | MINOR (kinerja) | perf72*.sql | `unnest` lateral |
| 7. Pengecek fixture batch terlalu longgar | MINOR (oracle) | kode | Mencocokkan pesan produk persis |
