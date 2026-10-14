# Keputusan owner kepada auditor Fable — 14 Oktober 2026 (putaran cp17, sesudah laporan v1.0 dikunci)

Label: OWNER_CONFIRMED_TO_AUDITOR (diberikan langsung di sesi Fable).

| No | Keputusan owner (verbatim) | Konsekuensi untuk audit |
|---|---|---|
| D14-1 | "gw kasi ijin akses 1-2" — dijawab pada pertanyaan cakupan Fable dengan dua pilihan: **"Baca-saja hosted Enteng"** dan **"Ambil arsip CP2 dari Drive"**. | Pengecualian tertulis atas larangan "tanpa SQL ke hosted" dan "tanpa Google Drive", **hanya** untuk verifikasi CP1/CP2: (a) query SELECT katalog baca-saja (tanpa baris data bisnis) ke Supabase Enteng `siimvrusnzxexizpyoib` lewat konektor yang sudah terpasang; (b) mengambil arsip CP2 terenkripsi + kuncinya dari Drive untuk restore di database sekali pakai di CI. Tidak ada tulis ke hosted, tidak ada pemasangan apa pun, tidak meminta kredensial, legacy `vlxdhpkjeevubjxexnfo` dan produksi tetap tidak disentuh. Hasil masuk sebagai addendum laporan cp17, tidak menimpa v1.0. |
