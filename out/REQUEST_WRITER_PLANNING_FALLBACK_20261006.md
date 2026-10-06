# Permintaan untuk penulis CP7 — parameter perencanaan global sebagai asumsi berlabel (6 Okt 2026)

Konteks: status F04 mencatat `unknown_inputs: NO_DEFAULT_YIELD_TIMES_OTHER_LOAD_OR_UNIT_TIME`. Selama parameter per SKU kosong, semua kartu rekomendasi berbunyi "perlu cek data". Owner menyetujui jalan tengah berikut, **dengan batas yang ketat**.

Yang diminta:
1. Satu layar "Parameter perencanaan global" (owner/admin): lead time produksi (hari), masa review (hari), buffer (hari jual). Nilai awal `PENDING_POLICY_VALUE`; owner mengisinya sendiri. Nilai ini **asumsi yang disetujui owner**, bukan hasil hitung, dan dipakai hanya bila nilai per SKU/ukuran kosong.
2. Baseline demand per SKU/ukuran dari riwayat penjualan yang ada (grup C), dengan ambang jumlah observasi minimum yang tertulis; di bawah ambang → baseline sederhana + label `RIWAYAT_TIPIS`, bukan angka pasti (grup D fallback).
3. Setiap kartu yang memakai salah satu fallback menampilkan label sumbernya ("lead time: asumsi global disetujui owner tgl …"; "demand: riwayat tipis"), dan `oracle_origin`/`fixture_origin` pada kasus ujinya menyebut fallback itu.

Batas yang tidak boleh dilanggar (INV-R01, R09, L03, POL01–02; §16.5):
- Fallback **tidak** mengubah WIP ambigu, yield pola yang belum diketahui, kapasitas tidak diketahui, atau riwayat tipis menjadi angka pasti. Yang belum pasti tetap "perlu cek data" / rentang, hanya targetnya yang boleh dihitung dari asumsi global.
- Tidak ada angka bawaan dari penulis (termasuk contoh kontrak 7/3/2, yang kontraknya sendiri bilang bukan parameter operasional). Kosong = pending, bukan nol.
- Kebutuhan kain tetap "belum pasti" sampai yield per pola terkualifikasi; rekomendasi potong keluar dalam PCS.
- Mengubah parameter global tidak menulis ulang snapshot rencana/laporan lama; snapshot baru dengan versi parameter tercatat (INV-T04, L02).

Bukti yang diminta: kasus native untuk (a) kosong → pending, (b) terisi → target dihitung + label, (c) per-SKU mengalahkan global, (d) riwayat tipis → label, (e) yield unknown tetap unknown walau parameter global terisi; plus satu kasus browser desktop/HP yang menunjukkan labelnya. Bukan prioritas di atas P19/P18; boleh dijadwalkan setelahnya.
