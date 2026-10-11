# Regresi dengan oracle writer yang dijalankan Astra

Kandidat `d0b9e9c2`; runner audit sendiri. Ini bukti `INDEPENDENT_NATIVE_RERUN`, dengan `oracle_origin=WRITER_UNCHANGED`. Jumlah di bawah berasal dari baris hasil asli, bukan nama job. Smoke dan fase gladi tidak ditambahkan ke hitungan kasus produk.

| Suite | Kasus produk PASS/teramati | Smoke PASS/teramati | Status mentah | Artifact ID |
|---|---:|---:|---|---|
| CP7_P21_REHEARSAL.json | — | — | PASS; 6 fase | 11711605241 |
| CP7_P21_FULL_REHEARSAL.json | — | — | PASS; 9 fase | 11711310972 |
| CP7_K3_CLEANUP.json | 19/19 | 0/0 | PASS | 11711075073 |
| CP7_F05_NATIVE_ANALYSIS.json | 153/153 | 0/0 | PASS | 11710891365 |
| CP7_F04_NATIVE_MODELS.json | 32/32 | 0/0 | PASS | 11710656118 |
| CP7_F04_NATIVE_PLANS.json | 43/43 | 0/0 | PASS | 11710621337 |
| CP7_P19_REMINDER_V2.json | 16/16 | 0/0 | PASS | 11710570004 |
| CP7_K2_RETENTION.json | 10/10 | 0/0 | PASS | 11710485331 |
| CP7_P18_E01_BRIDGE.json | 9/9 | 0/0 | PASS | 11710369983 |
| CP7_FABRIC_RECIPE.json | 13/13 | 0/0 | PASS | 11710366096 |
| CP7_F04_NATIVE_SCHEDULE.json | 71/71 | 0/0 | PASS | 11710332293 |
| CP7_P18_FABRIC_RULE.json | 11/11 | 0/0 | PASS | 11710148566 |
| CP7_F04_NATIVE_NETTING.json | 83/83 | 0/0 | PASS | 11710107919 |
| CP7_RULE_LIFECYCLE.json | 16/16 | 0/0 | PASS | 11710103216 |
| CP7_FABRIC_PHYSICAL.json | 21/21 | 0/0 | PASS | 11709951506 |
| CP7_P19_PLAN_V2.json | 22/22 | 0/0 | PASS | 11709940566 |
| CP7_P19_SCALE.json | 5/5 | 0/0 | PASS | 11709928878 |
| CP7_F04_NATIVE_SUPPLY.json | 53/53 | 0/0 | PASS | 11709918903 |
| CP7_P19_REPORT_V2.json | 20/20 | 0/0 | PASS | 11709499530 |
| CP7_P19_TRANSPORT.json | 15/15 | 0/0 | PASS | 11709198499 |
| CP7_PL5_HISTORY_YIELD.json | 20/20 | 0/0 | PASS | 11709164105 |
| CP7_P19_STAGED.json | 14/14 | 0/0 | PASS | 11708919221 |
| CP7_P19_AI_V2.json | 9/9 | 0/0 | PASS | 11708843997 |

P21 dasar: enam fase. P21 penuh: sembilan fase, termasuk transaksi COMMITTED, penolakan rollback sesudah dipakai, backup terpakai → restore 559 tabel, lalu restore pra-pasang. Tidak mengklaim rollback sesudah dipakai tanpa kehilangan transaksi. `pg_restore` keluar 1 karena 19 kesalahan pg_cron yang dilaporkan satu per satu pada database tujuan terpisah; tidak ada error tak terjelaskan. Catalog dibandingkan secara semantik untuk perbedaan serialisasi/ACL yang dicatat.

P19: 48 pengukuran UI dalam empat kasus browser. Lulus fungsi/batas bukan berarti semua waktu ≤3 detik. Rincian waktu, penolakan yang jujur, buka DONE, dan pindah halaman ada di `evidence/SCALE_BROWSER_SUMMARY.json`.
