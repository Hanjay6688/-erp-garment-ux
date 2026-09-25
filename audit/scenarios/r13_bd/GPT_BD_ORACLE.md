# GPT BD — oracle dibekukan sebelum review implementasi BD

Tanggal: 26 Sep 2026 WIB. Status: ORACLE_FROZEN, RUN_NOT_DISPATCHED.
Sumber normatif: Master Pulih (M) dan keputusan owner D06 mengenai CR laundry dalam CP6; rujukan rinci pada oracle pra-kode `out/r9_lau_oracle.md` dan `out/fable_all22_oracles_pre_code.md`. Jika tafsirnya tidak cukup jelas, hasil wajib HOLD, bukan disesuaikan dengan kode.

## GBD-01 — Harga disengaja UNKNOWN berbeda dari galat resolver

M:4347,4351,4145–4152,4475 (LAU-T09/T13). Dua pengiriman setara pada vendor, proses, sumber, dan jumlah 10 PCS. Pada A, harga sengaja diberi status UNKNOWN lewat jalur yang sah: terima fakta fisik tepat satu kali; simpan kewajiban UNKNOWN terhubung ke sumber, tanpa membuat tarif 0, biaya/AP/jurnal 0 atau HPP final; tutup periode yang terpengaruh ditolak. Pada B, resolver tarif gagal/ambigu: tolak pengiriman secara atomik, tanpa fisik maupun finansial baru. Mengulangi request yang sama tidak menggandakan A; B baru boleh berhasil sesudah resolver pulih dan pengguna menerima hasil yang sah. Bila kebijakan owner belum diset, penolakan fail-closed adalah hasil benar untuk aksi yang bergantung padanya.

## GBD-02 — Invoice parsial 40/60 serta dua pengiriman dalam satu invoice

M:4354–4356,3736,4218–4222,4477 (LAU-T16/T17/T18). Konfigurasi sintetis uji hanya di klon: vendor A mengirim 100 PCS dan 20 PCS pada dua sumber berbeda, masing-masing punya harga dan versi terpin. Invoice I1 menagih 40 PCS dari sumber pertama; sisa tagih sumber itu 60 PCS, fisik tetap 100. Invoice I2 boleh mengalokasikan 60 PCS sisa plus 20 PCS sumber kedua; satu sumber dapat beberapa invoice dan satu invoice beberapa sumber. Menagih lagi salah satu cakupan yang habis dengan request ID lain, melebihi kuantitas, atau mengaitkan sumber vendor B harus ditolak atomik. Jumlah alokasi, saldo AP, dan jurnal harus sama tepat sesuai basis dan aturan sen yang dikonfigurasi; estimate lama direkonsiliasi sebagai delta, tidak dijumlah dua kali sebagai biaya. Jika LAU-DEC01/02/06 atau akun varians yang diperlukan masih PENDING, posting invoice ditolak sementara draft dan fakta fisik tetap benar. Tidak ada angka tarif nyata yang boleh dikarang.

## GBD-03 — W05 cutover laundry: fisik, klaim, dan credit

M:4207,4210 dan ALL W05 (oracle pra-kode). Sebelum cutover vendor memegang 10 PCS; 2 sudah kembali, 1 MISSING belum settle, 7 masih ditangani normal; ada payable 30,00. Impor tidak boleh membuat 10 PCS WIP normal dan tidak boleh menganggap 1 MISSING pulih. Setelah credit klaim 5,00, riwayat penerimaan fisik tidak hilang; sisa payable selain cakupan klaim tidak dibatalkan. Kembalinya 7 PCS menyelesaikan WIP normal sekali; inverse credit mengembalikan payable dan status klaim semula tanpa menggandakan fisik. Status **NEEDS_OWNER_INPUT** untuk representasi claim/custody lama yang tidak dinyatakan eksplisit di M; sebelum keputusan tertulis, nilai structural invariant ini, tetapi jangan beri ACCEPT penuh pada ALL-W05.

## Batas metode dan keterpaparan

Oracle ini ditulis sebelum membaca kode BD SQL atau probe detail BD. Sebelumnya auditor sudah melihat **daftar ID dan status PASS 15 kasus T1 writer** di log run 36180413118. Itu keterpaparan cakupan, dicatat sebagai kontaminasi pemilihan kasus; tidak memakai nilai harapan dari probe writer. Verifikasi native harus menggunakan fixture dan assert auditor sendiri, tidak memanggil verdict writer sebagai oracle. Label wajib AUDITOR_SCENARIO dan database disposable, dengan identitas head dan hash berkas dipin.

## LANGKAH BERIKUTNYA

Tulis `gpt_bd_independent.py` dan manifest hash setelah membaca hanya helper API yang dibutuhkan; implementasikan GBD-01 dahulu, GBD-02 setelah rute invoice ada, dan GBD-03 setelah owner menetapkan representasi claim lama. Jalankan satu workflow audit untuk family BD pada head produk final; catat setiap NO_ROUTE/INCOMPLETE tanpa mengubah oracle ini.
