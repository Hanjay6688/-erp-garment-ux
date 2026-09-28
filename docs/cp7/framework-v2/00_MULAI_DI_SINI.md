# CP7 — Paket persiapan yang dapat langsung diturunkan

> **Revisi2 aktif:** baca `06_RUSUK_KEBUTUHAN_OWNER.md` terlebih dahulu. Kontrak AnalysisResult v2 menggantikan bentuk v1; pin/head dan receipt v1 di bab ini adalah sejarah persiapan, bukan accepted base. WA readiness dibawa ke CP7; aktivasi live tetap punya gate tersendiri.

Edisi 28 September 2026 WIB · FRAMEWORK_REVISED_V2 · CP7_IMPLEMENTATION_NOT_STARTED.

Paket ini mengubah kontrak lama menjadi rancangan teknis, paket kerja, expected hasil, dan aturan kolaborasi. Tidak mengubah kontrak bisnis atau mengesahkan CP6. Tidak ada runtime ERP, database, branch produk, atau deployment yang ditulis oleh penyusunan paket ini.

## Titik berangkat

- Repo: `Hanjay6688/-erp-garment-ux`; writer `claude/new-session-deapao` pada `2c2fd5e8e0df5f8ada44402c93f70dbaf0fbbb5b`; tree `20826407e5f98f798b1650f520300e85aebbd2eb`.
- Produk BE yang diuji writer: `73dc4055685e3f6bbefcd4c61bce1e60dcce26e3`. Commit akhir di atas adalah handoff/paket, bukan tes produk baru.
- CP6 HOLD. BE siap audit independen dengan disposisi T2 historis; BD diaudit terpisah. Paket ini tidak mengaku tahu hasil akhir audit itu.
- `main=557005e6674058f1e5e966b350cba05501e06182`; `competition/cp6-j-closure-20260911=ca7f09556397801c50a2277bdb65b1bf019f9a05`.
- `production_go=false`; tidak ada izin memasang CP7 dari dokumen ini. Implementasi baru dimulai setelah CP6 sah dan mandat CP7 diberikan.
- Pengecekan remote membuktikan push yang terlihat pada waktu pemeriksaan; tidak membuktikan editor lokal di chat lain berhenti. Push writer yang tidak dikenal: berhenti menulis dan kabari Hansen.

## Baca secukupnya, lalu kerja dari paket yang ditugaskan

1. `01_KONTRAK_DAN_INTEGRASI.md`: cakupan asli, sumber otoritas, jembatan semua CP, kondisi kode saat ini.
2. `02_BACKBONE_TEKNIS.md`: keputusan arsitektur, data, algoritme, RPC dan batas domain.
3. `03_KOLABORASI_DAN_PAKET_KERJA.md`: urutan paket, kepemilikan, aturan Claude/GPT, anggaran audit dan estafet.
4. `04_BUKTI_DAN_ORACLE.md`: angka contoh yang sudah dihitung, skenario lintas modul, gate dan invalidasi bukti.
5. `05_RUNBOOK_MULAI_CP7.md`: langkah persis setelah gate terbuka, instruksi writer/reviewer, keputusan yang benar-benar masih terbuka.
6. `registries/requirements.json` dan `requirements.csv`: setiap ID asli, sumber, scope, paket, bukti, dan status. Bukan sekumpulan ceklis kosong.
7. `registries/work_packets.json`, `cases.json`, `source_inventory.json`, `decisions.json`: data yang bisa dipakai runner/penerus tanpa menebak dari chat.
8. `contracts/analysis.schema.json`, `analysis.example.json`, `backbone.ts`: kontrak rancangan dan contoh konkret; tidak dipasang di ERP.

## Empat prinsip yang menentukan bentuk CP7

**Satu mesin, enam pemakai.** Stok, Planner, panel Buat/Bagi Potongan, Business Report, Reminder dan Tanya AI memakai hasil analisis yang sama. Formula bisnis tidak hidup sendiri di JSX.

**Sumber fisik sebelum kecanggihan ramalan.** Satu batch yang berpindah jahit–laundry–QC–FG tetap barang yang sama. FG aktual, WIP terarah, kandidat, barang bermasalah dan data unknown mempunyai arti berbeda.

**Sambungan transaksi termasuk scope.** CP7 juga menyambungkan sales/invoice/return/payment, attendance/payroll/Nota, FG handoff, HPP/finance/close/reporting yang masih belum connected. Planner bagus dengan sumber demo belum memenuhi CP7.

**Bukti mengikuti risiko perubahan.** T1 membuktikan keluarga; T2 membuktikan kandidat stabil; T3 membuktikan paket rilis dari baseline yang sesuai. Review independen tetap wajib. Tidak ada ritual rilis penuh pada setiap perubahan kartu; tidak ada tes keselamatan dihapus supaya cepat hijau.

## Langkah pertama ketika benar-benar mulai

Mulai **P00**, bukan langsung membuat halaman. Verifikasi ulang CP6 accepted head/schema/runtime, audit BD/BE dan disposisi lama; pastikan satu writer; isi receipt baseline; buktikan sumber dan jalur yang akan dibaca. Sesudah itu **P01** mengunci kontrak dan **P02** membangun snapshot coherent. Kartu tugas lengkap ada dalam registry. Status baseline saat ini adalah bukti persiapan, bukan accepted base untuk eksekusi nanti.

## Arti “lengkap”

Lengkap terhadap kontrak CP7 rev3, BR V3.1, UX32, WIP/Reminder dan kewajiban integrasi yang ditemukan, dengan seluruh kelompok warisan dipetakan. Bukan janji zero bug, bukan klaim seluruh percakapan telah diambil, dan bukan hasil audit implementasi CP7. Setiap perubahan kontrak setelah tanggal paket ini wajib menghasilkan delta kecil yang jelas; jangan membuat master baru berisi salinan ribuan baris berulang.
