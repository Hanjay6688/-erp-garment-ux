# Rerun mandiri atas suite writer

Run 37876648313: **33/33 job PASS**. Semua ID yang diproyeksikan diperiksa, bukan warna job saja. **1256 eksekusi kasus PASS**, termasuk 6 kontrol tambahan dan kasus pendahulu yang diulang antarvarian payroll. Dua gladi P21 mempunyai 6 dan 9 fase dan tidak dimasukkan sebagai kasus bisnis. Asal oracle tetap writer.

| Suite | Eksekusi PASS | Expected / observed dalam laporan | Batas |
|---|---:|---|---|
|analysis152|153|153 / 153||
|attention284|289|286 / 286|+3 kontrol di luar budget utama|
|cp7-p21-full-rehearsal|—|— / —|9 fase gladi|
|cp7-p21-rehearsal|—|— / —|6 fase gladi|
|fabric-physical21|21|21 / 21||
|fabric-rule11|11|11 / 11||
|fabric13-successor|13|13 / 13||
|k2-retention-10|10|10 / 10||
|k3-cleanup-17|17|17 / 17||
|model|32|32 / 32||
|netting|83|83 / 83||
|note_correction|43|40 / 40|+3 kontrol di luar budget utama|
|p13_finance|12|12 / 12||
|p18-e01-9|9|9 / 9||
|p18_full_cycle|2|1 / 2|; metadata expected basi, lihatF05|
|p19-ai-v2-9|9|9 / 9||
|p19-plan-v2-18|18|18 / 18||
|p19-reminder-v2-16|16|16 / 16||
|p19-report-v2-20|20|20 / 20||
|p19-scale5|5|5 / 5||
|p19-staged12|14|14 / 14||
|p19-transport11|15|15 / 15||
|payroll--attendance-write|80|None / None||
|payroll--payroll-review|42|None / None||
|payroll--roster|63|None / None||
|pl5-history-yield-20|20|20 / 20||
|plan39|43|43 / 43||
|receipt_correction|43|43 / 43||
|rule-lifecycle16|16|16 / 16||
|schedule|71|70 / 71|; metadata expected basi, lihatF05|
|supplier_payment_correction|23|23 / 23||
|supplier_payment_create|10|10 / 10||
|supply|53|53 / 53||

Semua group Native yang menyatakan boundary restore lolos; semua database_remaining yang dilaporkan0, tidak ada missing case atau cleanup failure. Catalog/restore P21 diperiksa pada witness lengkap. `REGRESSION_RESULTS.json` menyimpan seluruh case ID dan subgroup. Angka ini tidak termasuk1.722unit test,6browser shell, atau kasus oracle mandiri.
