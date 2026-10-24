# Butir selesai untuk diuji ulang

Daftar ini memuat butir yang sudah dinyatakan selesai, bukan checkpoint atau
hasil uji antara. Astra A kini memegang estafet Claude sebagai integrator. Bukti pada tabel adalah
penutupan awal masing-masing butir; [status current](../OPEN_WORK_D17_14_20261020.md)
memuat pengujian gabungan selanjutnya. Audit independen tetap terpisah.

| Butir | Hasil dan cakupan | Commit | Run/job |
|---|---|---|---|
| OW-01 WhatsApp |99/99 lulus, seluruh16 jenis ke provider palsu; pemasangan nyata tetap CP7C |9b323f13 |39463501158/118768676832 |
| OW-02 Proses di server |32/32 lulus, hasil tetap tersedia setelah browser ditutup |2ad56e14 |39420750772/118620792070 |
| OW-03 Kelipatan produksi |154/154 lulus, isian aplikasi dipakai analisis |878e0a9c |39423331714/118629536646 |
| OW-04 Retur transaksi lunas |Tujuh syarat22 Oktober terpenuhi; [bukti/batas](ow04/README.md), kesiapan laporan pada checkpoint awal BLOCKED→OW-08; current telah mempunyai bukti pemeriksa kredit sah/P21 |Produk36a6b880 (sumber8c437dbe); alat6e843f9b/793bb51f/bb752227/e2aeef46 |39734958661/119678374447;39741995021/119701210253;39746622801/119716563875,119716563804,119716563410 (hanya18HTTP/9browser);39748075152/119721445604;39749850579/119727373442;39761252503/119765697767 |
| OW-05 Koreksi mandor sesudah jahit |Upah/nota/payroll/HPP, seluruh PO, riwayat dan petunjuk pembalikan; [satu catatan bukti/batas](ow05/completion.json). Kualifikasi penulis; audit independen tetap terbuka |SQL e3a37d73, Native56830738; layar5e4b4c1c; Auth347a1baf; P219dde276f |Native28:39786776421/119851971167; Auth4:39792851198/119872918589; layar2:39797404450/119888156171; proses laundry/FG2:39797404458/119888156506; P21 lengkap13:39789070200/119859922468 |
