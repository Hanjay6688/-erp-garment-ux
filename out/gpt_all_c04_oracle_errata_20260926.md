# GPT — Errata oracle ALL-C04 (kain kantong), 26 September 2026
Status: KOREKSI ORACLE AUDITOR; bukan temuan produk BE.
CP6 HOLD · audit_complete=false · production_go=false.

## Berkas asal dan alasan
Oracle beku `out/r9_all_oracle.md:220–227` pada audit parent `857a597b063c90edc3efe6d645c78d4fcdd36543` dipertahankan apa adanya.
Baris 224 menyatakan pengeluaran historis tetap di luar WIP/FG dan menggambarkan alokasi sebagai pembagian expense. Jika diterapkan setelah alokasi periode disahkan, expected itu salah. Rujukan M:555–560 yang dipakai adalah bagian historis yang dikalahkan keputusan lebih baru di M:466–511; M:511 menyatakan penggantian itu secara eksplisit.

M:466–472 dan P:406–414 menetapkan: pengeluaran awal masuk biaya periode; opsi pengesahan alokasi memindahkannya ke WIP per PO, lalu HPP native meneruskannya ke FG/COGS. Tidak ada pengeluaran fisik kedua atau pengakuan biaya ganda. Oracle Fable `out/fable_all22_oracles_pre_code.md:507–520` sudah mengenali dampak HPP; itu membantu pemeriksaan silang, tetapi sumber otoritas tetap kontrak.

## Expected yang dikoreksi
1. Withdrawal tanpa alokasi: stok turun dan beban periode naik. Nilai belum otomatis masuk HPP.
2. Setelah alokasi sah: nilai keluar dari beban periode ke WIP/FG/COGS sesuai hasil jahit sah dan posisi barang. Denominator mencakup Afui; bukan absensi atau saldo kain per mandor.
3. Fixture angka kontrak M:476–485: biaya 11,25 dengan 5 pcs WIP/3 FG/2 sold menghasilkan 5,62/3,38/2,25. Koreksi sumber menjadi 15,00 menghasilkan 7,50/4,50/3,00. Ini komponen tambahan kain kantong, bukan seluruh HPP produksi.
4. Alokasi/cancel tidak menggerakkan kain gudang lagi. Cancel membalik perpindahan biaya dan menghitung ulang HPP; pembalikan pengeluaran adalah event berbeda.
5. Opening hanya memuat kain yang masih ada. Kain yang sudah ditarik tidak dimasukkan kembali ke stok. Nilai yang sudah masuk saldo awal WIP/FG/hasil periode tidak dialokasikan ulang.
6. Asal pengeluaran pra-cutover yang belum dialokasikan dan denominator periode lintas cutover harus direpresentasikan dengan fakta historis sah. Jangan membuat ulang transaksi lama, menghilangkan hasil jahit pra-cutover, atau mengganti periode sumber dengan periode baru semata agar cocok dengan adapter.
7. Sumber/denominator berubah, overlap, tanpa hasil jahit, replay dan inverse mengikuti guard sumber/cancel/recompute kontrak M:487–499. Ketidaklengkapan provenance harus diungkap, tidak disamarkan sebagai Rp0 atau PASS.

## Batas koreksi
- Anti-duplikasi stok, expense dan histori pada oracle lama tetap berlaku.
- Inti kebijakan alokasi HPP sudah diputus kontrak; tidak perlu meminta owner memilih lagi apakah alokasi boleh masuk HPP.
- Cara membawa sumber/denominator historis serta nilai yang sudah terkandung dalam opening masih harus dijelaskan dan diuji oleh adapter ALL-C04.
- Angka fixture lama (20 sisa + 5 sudah ditarik) dan fixture kontrak (20 awal − 5 = 15 sisa) bukan keadaan yang identik; jangan menyatukan keduanya tanpa menyatakan baseline.
- Tidak ada run BE/C04 baru, run ID, job ID, atau hasil beku yang diubah pada pekerjaan ini. Pemeriksaan dampak terhadap semua skenario executable lama belum dilakukan. Sesi yang akan menilai C04 wajib memeriksa expected lama sebelum rerun; ini bukan klaim bahwa semua hasil lama bebas dampak.
- Oracle Fable tidak diubah atau diterima seluruhnya melalui errata ini, khususnya tafsir periode historis vs periode baru perlu diuji terhadap provenance sebenarnya.

## Identitas
- Master SHA256: `f21ac70360915a1f1021b42a3918e862ca7d11cf88c1b90c5627b4490c69af07`.
- Perubahan SHA256: `92966cd6ed27e64123be6c52e2263bfbdb3db91c97f2e441c3bdc98589397676`.
- Produk/sumber writer yang dibaca: `7d33d84d0f93c54c43e7acd9d2df4d89d6d6f2e2`.
- Pembacaan UI pendukung: `src/ConnectedPocketFabricPage.tsx:148,173–195`; bukan pengganti oracle kontrak.
- Konsep integrasi: `out/gpt_be_concept_map_20260926.md`, BE-04 dan GBE-11/12.

## LANGKAH BERIKUTNYA
Pakai expected yang dikoreksi untuk menulis skenario ALL-C04. Pertahankan hasil lama; bila ada skenario/run lama memakai expected keliru, catat superseded/reason dan buat run baru, jangan melabel ulang hasil beku.
