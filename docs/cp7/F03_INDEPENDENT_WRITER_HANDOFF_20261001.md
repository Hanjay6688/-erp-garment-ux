# Handoff audit independen F03

Putusan: **INDEPENDENT_ACCEPTED_F03_CONTRACT_SCOPE** untuk P09–P13 dan
sambungan yang tercatat dalam matriks audit. Tidak ada blocker produk atau
eksekusi wajib yang belum selesai dalam matriks tersebut.

Tes baru auditor **26 lokal +23 runtime lulus**. Cross-check yang dijalankan
auditor **502 lulus +3 smoke terpisah**, termasuk browser akhir8/8. Tidak ada
patch produk yang diminta dari hasil audit ini. Full CP7 dan produksi belum GO.

Kandidat produk: `eb6b8682e97e94c95f89d431ab81974c54ddcbaf`.
Bundle F03: `6df48df8bbf7113636ce504b2f1f894b43a6444f803ba71a0007c18b32f6907c`.
Semua pengujian memakai data sintetis/database sekali pakai. Tidak ada patch
produk, perubahan branch writer, deploy atau perubahan database utama.

## Bukti dan temuan yang dipisahkan

- **Tes baru auditor:**26 kontrak lokal;23 native/race/Auth/browser. Expected
  uang, jumlah, hak akses dan pemulihan ditulis terpisah. Rincian di
  [laporan audit](F03_INDEPENDENT_AUDIT_20261001.md).
- **Cross-check auditor:** suite writer dijalankan ulang pada stack F03 yang
  dibekukan, termasuk446 transaksi,3 smoke,40 sambungan produksi/biaya/browser,
  14 retur gabungan/konteks privat dan2 sambungan planner. Angka ini adalah
  eksekusi yang beririsan, bukan jumlah kebutuhan unik.
- **Kesalahan alat uji auditor:** tanggal mustahil ditolak dengan kode native
  yang benar; tes browser terlalu cepat mengecek callback; batch browser
  terhalang benturan port. Semua receipt awal tetap disimpan. Ini tidak menjadi
  tiket bug produk. Lihat [errata](F03_INDEPENDENT_PROBE_ERRATA_20261001.md).

## Arahan integrasi

Tautkan putusan dan [receipt lengkap](evidence/f03-independent-20261001/runtime/INDEX.json) ini ke status aktif F03
tanpa mengubah hasil historis. Tidak perlu mengulang pekerjaan yang sudah
terbukti aman atau membuat patch produk hanya karena nama commit berubah.

Perubahan berikutnya yang menyentuh writer transaksi, schema, izin, kunci,
tanggal bisnis, sumber HPP atau pemulihan harus diuji sesuai jalur terdampak.
F04/F05 terbaru tidak otomatis diterima oleh laporan F03 ini.

P18–P21, pencocokan desain demo, skala/resiliensi, paket rilis/cutover dan
persetujuan produksi tetap merupakan gate akhir CP7. Batas retur invoice baru
yang sudah lunas tetap berlaku; refund yang diuji punya hak kredit sumber lama
yang sah. Jangan membuat kebijakan kredit baru dari hasil uji ini.

`production_go=false`. CP6 yang sudah diterima dalam cakupannya tidak dibuka
ulang oleh handoff ini.
