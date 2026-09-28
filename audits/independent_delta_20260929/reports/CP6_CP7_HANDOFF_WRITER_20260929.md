# Handoff gabungan untuk writer — CP6/CP7, 29 September 2026

CP6: `cce68d37083ac2d477f559e3192c7bc8d459aebf`.
CP7: `6465825d0f8a865f28264626a4e0af818d66967e` (PR #31).

**Tidak ada bug CP6 baru yang terbukti pada retest perubahan. Satu tindakan perbaikan aktif ada di CP7.** Jangan membuka ulang temuan yang telah selesai hanya karena laporan audit lama masih memuatnya.

## Tindakan aktif: CP7-DELTA-01

`projectShell` pada `src/cp7/workspace.ts` hanya membuang `metrics` ketika hak contoh bukan OWNER. Perbandingan biaya dalam `analysis.plan_comparisons` tetap dikembalikan kepada OPERATIONS.

Input sah: perbandingan `metric_id=COST`, `planned` dan `actual` berupa KNOWN, unit IDR, nilai `987654321.09`, dengan referensi sumber. Input lulus schema lengkap serta coherence guard. Proyeksi OPERATIONS masih mengandung nominal itu. Ini gagal pada eksekusi lokal dan CI.

Perbaiki proyeksi berbasis kewenangan secara menyeluruh sebelum penyambungan data asli. Pertahankan data operasional yang boleh dilihat. Pastikan laporan, prompt Tanya AI, dan preview pengingat memakai proyeksi yang sudah disaring. Saat integrasi backend dibuat, filter klien ini tidak menggantikan otorisasi backend.

Kriteria selesai:

1. Probe independen yang sama lulus tanpa melonggarkan kontrak/oracle.
2. OWNER tetap memperoleh nilai sesuai haknya; OPERATIONS tidak memperoleh nilai keuangan terlarang, termasuk di objek analisis yang dikembalikan; DENIED kosong.
3. Proyeksi tidak memutasi sumber dan perubahan akses tidak meninggalkan keluaran lama.
4. Tes terkait tetap lulus; cukup retest jalur terpengaruh, tidak perlu mengulang seluruh CP6 bila produk CP6 tidak berubah.

Prioritas: sebelum integrasi data asli. Cangkang masih sintetis dan contoh bawaan belum mengisi perbandingan biaya; belum ada bukti kebocoran data asli atau nominal ini tampil pada layar. Temuan ini tidak dibebankan sebagai blocker CP6.

## Bagian yang sudah tertutup dalam lingkup pemeriksaan

- Tes baru auditor CP6: 11 native + 1 Auth/HTTP PASS. Kredit retur kain/aksesori, alokasi ulang/replay/inverse, tanggal pembayaran, event append-only, batas waktu SKU, harga vendor FREE/WAIVED/UNKNOWN, helper privat terpilih, HPP historis/invoice/inverse, serta izin baca sumber kredit.
- Cross-check writer: paket 30 berkas AC..BF, rangkaian range/rework, paket runtime 90/22/8/27, 10 browser AU tambahan, rollback147, BC45, BD41, build, dan CodeQL. Bukti writer tetap diberi label cross-check.
- CP7: build PASS; 34 tes fokus lama PASS; 6 browser desktop/HP PASS; 6 dari 7 probe baru PASS. Satu probe gagal adalah CP7-DELTA-01 di atas.
- Tidak perlu keputusan owner baru untuk tarif vendor atau fleksibilitas kredit. Kesalahan fixture auditor pada HPP telah diperbaiki auditor dan retest PASS; itu bukan pekerjaan produk writer.

## Batas penerimaan, bukan tiket perbaikan otomatis

Pertahankan keterangan terpisah untuk R03 (wave terpisah pada dua referensi ukuran sama), R10 (layar penjualan masih simulasi), dan R14 (Grade B berisi belum dibuktikan). Jangan mengklaim kemampuan yang belum diuji. Jangan juga memperluas lingkup CP6 sendiri tanpa dasar keputusan owner.

Izin owner untuk cangkang CP7 tetap berlaku. Integrasi operasional belum dibuktikan oleh tes sintetis. Head CP7 lebih lama dari paket CP6; pemeriksaan merge teks bersih, tetapi gabungan aplikasi belum diuji sebagai kandidat integrasi. Setelah nanti digabungkan, jalankan pemeriksaan kontrak/akses yang terdampak pada SHA gabungan yang dibekukan.

Audit perubahan selesai. Tidak ada merge, deployment, akses production, atau perubahan kode produk oleh auditor. `production_go` tidak diberikan oleh handoff ini.

## Bukti untuk reproduksi

- Branch auditor: `audit/cp6-policy-cp7-delta-20260929`.
- [Run awal CP6](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36456038419): 10 native + 1 Auth PASS; satu fixture INCOMPLETE tetap tercatat.
- [Retest HPP + CP7](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36457111605): HPP PASS; browser6 PASS; artefak kontrak CP7 menyimpan 6 PASS/1 FAIL. Status job hijau tidak menghapus kegagalan kontrak yang sengaja ditahan agar browser tetap diuji.
- Commit audit `d3106cdf1f3ec524125f07fb900aeef219550105`, direktori `audits/independent_delta_20260929`: oracle, native probe, CP7 test, dan contoh perbandingan biaya yang sah.
- Laporan pendamping: `CP6_CP7_AUDIT_DELTA_20260929.md`.
- Paket bukti pendamping: `CP6_CP7_AUDIT_EVIDENCE_20260929.zip`.
