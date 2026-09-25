# CP6-06 browser control diagnosis

## Unknown rev3 selesai — penyebab fixture terbukti, dua kasus tetap INCOMPLETE

Run **36103599807 / job107971184469**, audit **b2ada06c1a3a26fcfda83d421318b75a9b7f2a73**, tool9dd7bc2 / produka095a9d. LOG attempt1 SHA256 **9568ec0790adde587926edc36ec8c19d84121e92c237a1903aae8187a8cfe4f0**; rincian per kasus dan payload di `out/gpt_unknown_run_36103599807.json`.

- Laundry: actual Auth RPC20pcs, HTTP200; parser asli menolak **`ID Mandor bukan UUID valid.`**.
- QC: actual Auth RPC10pcs, HTTP200; parser asli menolak **`ID model QC bukan UUID valid.`**.
- ID fixture warisan `a1000000-0000-0000-0000-000000000001` / `a2000000-0000-0000-0000-000000000001` tidak memenuhi regex UUID frontend. Parser sourceSHA256 `f217cd5a2be8dd42262063733b47626cee841bad75391271b402ed6add167ccb`; hanya ditranspilasi, tidak diubah.
- Setelah read awal diputus, KPI0 + pesan error + transaksi terkunci teramati. **Kontrol sehat tidak sah; belum membuktikan bug state/refetch dan tidak mengubah status dua kasus menjadi PASS/COUNTEREXAMPLE.** CP6-06 tetap terbuka pada lingkup yang didukung bukti.
- Cleanup lulus:2Authusers, counts[0,0,0,0] pulih, console0, browserDB0, clone0, primary unchanged. Ordinary factory0kasus disengaja, bukan tambahan PASS.

LANGKAH BERIKUTNYA: bekukan diagnosis ini; siapkan fixture browser sah yang lebih dahulu lulus parser/healthy-render melalui Auth/HTTP asli, kemudian ulang hanya dua kasus unknown/recovery. Jangan melonggarkan validator produk atau memalsukan respons. Kandidat W11 dari Fable (pesan koneksi generik setelah parser error) perlu dipisahkan dari klaim kegagalan refetch. Perbarui tabel/handoff aktif dengan CP6-05 native confirmed dan kualifikasi CP6-06. CP6 HOLD · audit_complete=false · production_go=false.

