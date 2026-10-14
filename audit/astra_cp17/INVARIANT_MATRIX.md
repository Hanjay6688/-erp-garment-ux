# Matriks invariant — candidate0b7049d9

Bukti kelompok menunjuk CASE_LEDGER_FINAL dan Original, bukan sertifikasi setiap kombinasi input. Nomor INV mengikuti kontrak frozen bila disebut dalam finding; label deskriptif di bawah bukan invariant baru yang dibuat untuk mengganti kontrak.

| Invariant | Bukti sumber/oracle/eksekusi | Hasil dan batas |
|---|---|---|
| Riwayat baseline tidak diedit; identitas produk tepat |CP1_LEDGER_BYTE_CHECK; G-01 run38525347357; current ownership run38527771239; PRODUCT_PARITY |19 file cocok pemetaan;15 kategori cocok;51 command historis tidak direplay; platform ledger difference dijelaskan |
| Backup lama benar-benar dapat menjadi database pulih |CP2_ENCRYPTED_RECOVERY writer receipt; CP1_CP2_EVIDENCE_REVIEW |Pembukaan arsip149 anggota tercatat; DB restore belum dapat diverifikasi |
| Biaya absensi sekali; payroll settlement-only dan tanggal benar |PAY01–06; HPP01; f03-p12; sumber payroll settlement/installments/native accrual |Full/partial/final early payment melanggar FIN-01; kontrol sah PASS; duplicate Nota dan overlap-source ditolak pada kasus ini |
| PCS fisik tidak dibuat/hilang lewat unit/konversi |f03-p09/p10, cutting-model, fabric-physical, AR, P11_XC2, SKN22 |Oracle yang dijalankan cocok; lusin browser P11 carry candidate sama |
| Raw→WIP→FG→sale/return menjaga qty dan HPP |legacy BUSINESS/VALUES; p18-fullcycle; receipt/cutting/sales-return corrections; SKN22 |Angka independen final cocok dan jurnal balance; bukan seluruh jalur produksi |
| AR/AP/cash settle sekali; replay/refusal atomic |cash-installments/customer-refund/supplier-credit/payment corrections; AR28 races; own-money; SKN22 |Oracle lulus, kecuali tanggal payroll FIN-01; supplier A2 nondeterminism lama tetapOPEN accepted |
| Saldo awal tidak menggandakan fakta/settlement |AR146+replacement1+28race; IMPORTS31; SKN22 opening bank |PASS current replacement; oldzeroaccessory INCOMPLETE tetap; AR outer fixture limitationQ02 |
| Tanggal ekonomi/pengakuan/periodclose sesuai keputusan owner |AT16 AU15 temporal4/master6; BUSINESS calendar12; AS34/AO12/supplement5/C025 |C025PASS; oldHOLD/CE/INC utuh; Q02 outer committed-fixture tidak direlabel |
| Koreksi awal merekonsiliasi semua turunan |note/receipt/cutting/payment/misc/supplier-payment correction; independentSKN22 |Perhitungan/mutasi/refusal sesuai cases; correction tests tidak membenarkan FIN-01 |
| Planning/identity/netting tidak memberi stock/order palsu |pl-supply/model/schedule,pl5,p19-plan,own-plan,netting |Oracle PASS; PR44 author conflict disclosed; peer acceptance berasal Fable sebelumnya |
| Snapshot/report memiliki identitas, halaman lengkap, reader sesuai scope |own-stage,p19-report/ai,k2/k4/k6,SKN22 |Cases PASS kecuali accepted AS20-39 rawCE; tidak mengklaim semantic-corruption detector lengkap |
| Reminder membaca kewajiban live dan tidak menandai pesan terkirim palsu |p19-reminder/rule-lifecycle,SKN22 |PASS dengan sentfalse; external delivery/WA sebenarnya tidak diuji |
| Auth/publicboundary/version/idempotency/concurrency |F03browser, own-contract negatives, AR/temporal/master races; everycase snapshots |Scope percase diOriginal; admin fixture berbeda dari ordinarypublicactions; tidak semua kemungkinan role/user combination |
| Restore katalog lengkap/ownerACL/rows/locks |full_stack wrappers;31native;own;integration;ARracecloneOID;P21 |Q02temporal/ARouterfixture dan Q06staleprogress dipertahankan; P21same-meaning tidak byteexact seluruhkatalog |
| Release pascausage tidak rollbackdiam-diam |P21preuse rollback/reinstall/committeduse/postuserefusal/usedrestore |RehearsalPASS dengan bataspg_cron/defaultACL/reparse dan38clusterroles; production_go:false |
