## 8. Kelas keparahan

| Tingkat | Arti | Contoh |
|---|---|---|
| **S0 – Bahaya bangkrut** | Angka uang, stok, HPP, laporan, atau rekomendasi **salah tanpa ketahuan**, atau data rusak permanen | Utang tercatat lebih kecil diam-diam, HPP salah di laporan laba, rekomendasi produksi dari data basi |
| **S1 – Salah tapi tertangkap** | Angka salah tetapi pengaman atau cek integritas menolak atau menandainya; atau alur penting macet tanpa jalan keluar | Command ditolak karena bug; koreksi tidak bisa dilakukan |
| **S2 – Fungsi atau UX** | Tidak merusak angka, tetapi menyesatkan atau mempersulit | Pesan tidak jelas, tombol sulit ditemukan |
| **S3 – Dokumen atau bukti** | Klaim dokumen tidak sesuai bukti; bukti basi | Jumlah kasus di dokumen tidak sesuai manifest |

Kalau ragu, pilih yang lebih tinggi. **Semua S0 dan S1 harus selesai** sebelum gerbang §12.

Hasil non-PASS yang **bukan** cacat produk tetap ditulis, dengan klasifikasi eksplisit: `AUDITOR_TOOL` (POLA-16), `SUPERSEDED_BY_OWNER_RULE` (POLA-17), `ACCEPTED_BY_DECISION` (INV-POL05), `INFRA_RACE_RERUN_PASSED` (POLA-20, satu rerun), `GUARD_BY_DESIGN` (penjaga skenario yang memang harus merah). Tanpa klasifikasi, hasil merah dihitung sebagai temuan.

---

## 9. Format laporan auditor

```
# AUDIT <AUDITOR> — commit <sha> tree <sha> — <tanggal>
Lingkungan: <PostgreSQL/Node/browser/OS>
Perintah yang dijalankan: <daftar>

## Ringkasan
S0: n, S1: n, S2: n, S3: n — invarian PASS/FAIL/INCOMPLETE: …

## Temuan
### <AUDITOR>-001 — <judul satu kalimat>
- Keparahan: S0/S1/S2/S3
- Invarian/pola: INV-…, POLA-…
- Lokasi: path:baris (semua lokasi terkait)
- Rantai dampak: dokumen → … → laporan/layar
- Skenario yang membuatnya rusak: langkah demi langkah, dengan angka
- Bukti: TERBUKTI (perintah + output, run CI) / DUGAAN (alasan dari kode) / BELUM DIVERIFIKASI
- Tingkat bukti: STATIC/LOCAL/NATIVE_QUALIFIED
- Usulan perbaikan + uji yang harus ditambahkan (gagal sebelum, lulus sesudah)

## Matriks invarian
INV-U01 … INV-N02: PASS/FAIL/INCOMPLETE + bukti singkat

## Yang belum saya periksa (wajib)
Daftar berkas/modul/skenario yang tidak sempat atau tidak bisa diperiksa, beserta alasannya.

## Hasil merah yang bukan temuan (wajib)
Setiap FAIL/INCOMPLETE/COUNTEREXAMPLE yang tidak dihitung temuan: run, kasus, klasifikasi §8, alasan satu kalimat.

## Label asal-bukti per klaim (wajib)
Tabel klaim → label §2.9 → run/commit. Klaim tanpa label dianggap REUSED_WRITER_EVIDENCE.

## Pertanyaan untuk owner, masing-masing dengan rekomendasi auditor (wajib)
Tidak ada pertanyaan tanpa jawaban yang disarankan dan alasannya; owner cukup menjawab "ya" atau mengoreksi. Pertanyaan yang jawabannya sudah ada di register keputusan tidak boleh muncul di sini.

## Ringkasan untuk owner (bahasa sehari-hari, ≤ 10 kalimat)
Apa yang lolos, apa yang tidak, apa yang belum diperiksa siapa pun, dan apa yang harus owner putuskan.

## Fokus tambahan yang menurut saya paling berisiko
```

---

## 10. Aturan penyatuan (oleh Fable)
