# Handoff penajaman panduan audit — Astra — 3 Oktober 2026

Status: usulan dokumentasi sebelum putaran lomba. Tidak ada pengujian produk baru, pembekuan kandidat, perubahan kode produk, atau perubahan status penerimaan CP6/CP7 dalam pekerjaan ini.

## Sumber yang dipakai

| Sumber | Identitas |
|---|---|
| Panduan Opus | `31ee23f0cdde4ddb36c76f1089d356b9b8d8663c`, `docs/AUDIT_PANDUAN_PRO_MAX.md` |
| Panduan dengan tambahan Fable | `3da9498d64a354bff1886166d6b8d0a513172a27`, path yang sama |
| Klarifikasi Fable | Diteruskan owner di percakapan Astra pada 3 Oktober 2026: arti log lama, batas review kode, dan batas kesimpulan detektor |
| Protokol acuan | `docs/cp6-competition-mode-audit-protocol.md`, `docs/cp6-efficient-audit-rule.md`, dan `docs/cp7/framework-v2/04_BUKTI_DAN_ORACLE.md` pada commit Opus di atas |

Panduan Fable dibaca lengkap. Versi gabungan mempertahankan seluruh baris panduan Fable dalam urutan semula dan menambah penjelasan; ID lama tidak diganti. Sumber dari percakapan adalah klarifikasi yang diteruskan owner, bukan hasil audit produk oleh Astra.

## Yang ditambahkan dan alasannya

| Tambahan | Alasan / batas klaim |
|---|---|
| Penegasan §2.2/2.12 | Log peserta yang boleh dibaca sebelum audit hanya versi yang sudah ada sebelum commit beku. Laporan putaran aktif menunggu seluruh penyerahan terkunci. |
| Penegasan §2.9/12.8 | Review kode menutup klaim statis; perilaku runtime memerlukan eksekusi independen pada lapisan tersebut. |
| Penegasan §5.D | Kontrol negatif membuktikan jalur yang diuji; tidak menjanjikan semua kesalahan tertangkap. Penolakan tamper bukan bukti sensitivitas alarm. |
| SKN-24..29 | Sambungan matcher–allocator; FREE/WAIVED yang sah; batas angka/paginasi; koreksi yang selesai; riwayat SKU/range; hasil laporan, AI, dan reminder yang benar-benar digunakan. Ini kewajiban pemeriksaan, bukan enam temuan produk baru. |
| §16.1–16.2 | Pin produk, alat dan lingkungan terpisah; manifest ID kasus dan expected per dimensi; pisahkan asal oracle/fixture dari siapa yang menjalankan tes. |
| §16.3–16.4 | Jangan menerima sembarang error sebagai bukti guard; jangan salah menuduh produk saat fixture rusak; buktikan race, commit dengan balasan hilang, dan perubahan detektor secara nyata. |
| §16.5–16.6 | Inventaris eksplisit CP1–7, termasuk jalur koreksi sah; pisahkan fitur selesai, audit selesai, dan izin produksi; bedakan restore/rollback/reversal dan jaga arsip bukti. |
| §16.7 | Aturan berlaku sama, hasil dikunci sebelum saling membaca, penilaian per akar masalah terbukti, sengketa peserta yang merangkap penyatu tidak diputus sendiri, dan temuan sembuh tidak membebani writer ulang. |

Klarifikasi yang sengaja mempertahankan batas ketat:

- §1.2 versus §1.8 tidak menjadi izin akses hosted baru. Tanpa otorisasi owner yang menyelesaikan konflik, auditor tetap memakai disposable; penerimaan bukti baseline tetap harus memenuhi syaratnya.
- Satu rerun identik hanya sebelum kasus pertama (§1.9). Koreksi alat/reproduksi sengketa/uji perbaikan harus berupa kualifikasi terdokumentasi dengan alasan dan diff; hasil lama tetap ada. Tidak boleh mengganti expected/seed/nama kasus untuk mencari hijau.
- Penerimaan risiko owner tidak diberi label PASS. Penutupan checkpoint dan izin produksi tetap keputusan terpisah sesuai acuan paling baru.

## Cara mengambil revisi

Cabang `audit/cp7-audit-rules-astra-20261003` bertumpu pada commit Opus `31ee23f0...`, hanya membawa panduan gabungan, handoff, dua patch, dan receipt verifikasi. Cabang ini tidak membawa riwayat kode produk dari cabang audit Fable.

Pilih **satu** jalur patch, jangan keduanya:

| Kondisi panduan tujuan | Patch |
|---|---|
| Sudah sama persis dengan panduan Fable di `3da9498` | `out/astra_panduan_additions_20261003.patch` |
| Masih sama persis dengan panduan Opus di `31ee23f0` | `out/opus_fable_astra_panduan_20261003.patch` |

Contoh untuk panduan yang sudah memuat Fable:

```bash
git apply --check /path/ke/astra_panduan_additions_20261003.patch
git apply /path/ke/astra_panduan_additions_20261003.patch
```

Untuk baseline Opus, ganti nama patch pada kedua perintah dengan patch gabungan. Jalankan di checkout tujuan yang sudah diperiksa; bila panduan telah bergerak, cocokkan perubahan dahulu. Jangan memaksa patch atau menimpa suntingan baru. Draft PR juga dapat dipakai sebagai sumber review sebelum writer menggabungkan.

## Verifikasi dan batas hasil

Receipt: `out/astra_panduan_validation_20261003.json`.

Pemeriksaan yang dilakukan pada dokumen: kecocokan byte salinan sumber; seluruh baris Fable dipertahankan; ID definisi invarian/pola/skenario unik; kedua patch lolos `git apply --check`, menghasilkan berkas identik, dan dapat dibalik ke baseline persis. Pemeriksaan dilakukan dalam dua checkout dokumen sementara yang terpisah.

Ini verifikasi **patch dokumentasi lokal**, bukan `NATIVE_ACCEPTED`, bukti CI produk, atau penutupan gate produksi. Tidak ada workflow produk yang dijalankan atau database yang disentuh untuk penyuntingan panduan ini.

Sebelum lomba: writer menyatukan panduan; owner/penilai menetapkan aturan dan fasilitas yang sama; kemudian catat manifest pembekuan kandidat serta versi panduan. Bobot penilaian tetap milik owner/penilai, bukan ditentukan Astra sebagai peserta. Setiap peserta tetap menjalankan audit penuhnya sendiri.
