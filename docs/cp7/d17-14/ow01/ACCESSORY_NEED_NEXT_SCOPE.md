# OW-01 tersisa — kebutuhan aksesori rencana ke WA

Review sumber pada produk4e3c98b3. Belum ada implementasi atau Native runtime
baru dari dokumen ini. D17-14 sudah memerintahkan semua pengingat ke WA;
jangan meminta izin forwarding lagi. Tujuh sumber kewajiban tambahan yang
sudah lulus65 kasus tetap dipertahankan.

## Fakta yang menentukan isi pesan

`planning/material-requirements.sql:7–80` menghitung kebutuhan kotor dari
gap bersyarat × BOM. Untuk BOM berisi, pemasangan nyata, sisa yang memang
dialokasikan dan tambahan dari luar **UNKNOWN**. Stok gudang, pengeluaran
aksesori dan snapshot biaya bukan bukti pemasangan atau alokasi target.
`staged_page_rows:338–356` memakai additional_external, sehingga kondisi
Native ini DATA_REVIEW. BOM kosong eksplisit memberi nol kebutuhan aksesori
saja, bukan nol kain atau bukti kesiapan produksi.

Karena itu jangan mengarang fixture positif "perlu membeli186" dari
gross186. Forwarding dapat mengirim **kebutuhan aksesori perlu diperiksa;
jumlah tambahan belum diketahui**, dengan status dan sumber review yang
jelas. Menciptakan otoritas pemasangan fisik baru bukan prasyarat diam-diam
untuk meneruskan pengingat yang memang sudah tampil.

## Jalur implementasi yang harus tersambung

| Lapisan | Sumber pada4e |
|---|---|
| Kondisi dan sumber snapshot | `reminders/staged-reminders.sql:174–176,338–356`; input saat ini hanya membawa additional_external, belum gross/installed/unused/reason. |
| Recheck kini | `staged_target_now:198–244`, `staged_verdict:528–580`; aksesori selalu ACCESSORY_NEED_NOT_RECHECKED_LIVE. |
| WA | `alerts/alerts.sql`: enum tabel84/106/121/128; collect468; urutan606; penutupan612/626; recheck sebelum kirim696/953/955/972/977; format740–760; bawaan1035; visibilitas1076; validasi1135. |
| UI/kontrak | `src/waContract.ts`: jenis19–28, label32–46, progres68/201, detail96/266, visibilitas353, format720/738; DOM ConnectedRemindersWa dan browser WA. |
| Bukti/bundle | `cp7_reminder_v2_bundle.py`, `cp7_alert_bundle.py`, `WA_FORWARD.json`, `cp7_wa_forward_cases.py`; tetap seluruh65 kasus lama. |

Seluruh path SQL di tabel relatif `scripts/cp7-src/`. Nomor baris adalah
pin4e, bukan kontrak pengganti hash sumber.

Pemeriksaan terkini harus mengikat root+model+size/versi produk tunggal,
kebijakan produksi/revisinya, profil perencanaan/revisi, jadwal pilihan/revisi,
dan tepat satu versi BOM berlaku beserta item/kuantitas/kategori aktif/satuan/
revisinya pada satu clock pemeriksaan. Memeriksa ACTIVE/KNOWN saja belum cukup.
Sumber capture `j.reference.material_source` tetap acuan snapshot immutable;
pemilihan versi kini dihitung ulang agar peralihan tanggal efektif tertangkap.

Kebutuhan yang turun, sumber tidak lengkap atau BOM/profil/jadwal berubah
menahan pengiriman snapshot lama dan meminta analisis baru. Stok/WIP yang
menutup gap juga diperiksa. Izin sumber diulang setelah menunggu; izin
gudang aksesori tidak ditambahkan bila tidak membaca stok gudang tersebut.
Kontrak DATA_REVIEW perlu disambungkan sampai policy, collector, formatter,
dedup dan recheck sebelum kirim, bukan mengganti verdict menjadi STILL_OPEN
hanya agar enum lama menerima pesan.

Penguncian mengikuti penulis Native yang nyata: shared master mengambil
FG_HPP_SALES_V2620C lalu BF:COMMERCIAL_SKUS (`cp6_bf_objects_master.sql:101–103`).
Kunci pengingat yang tidak dipakai penulis BOM bukan serialisasi sumber.
Jaga timeout, urutan sumber, izin terakhir dan episode jenis+target+kategori;
run baru saja tidak boleh menggandakan pengingat yang masih terbuka.
`ACCESSORY_AT_REORDER_POINT` tetap pengingat minimum gudang yang berbeda.

## Expected sebelum membuat pengujian baru

| Fixture | Expected |
|---|---|
| Gap93, BOM2 | Gross186 ASSUMED; pemasangan/sisa alokasi/tambahan eksternal UNKNOWN tanpa angka pembelian. |
| Terima80 lalu keluarkan80 | Tambahan eksternal tetap UNKNOWN; bukan106,20 atau0. |
| BOM tidak ada/tumpang tindih/kategori tidak aktif | UNKNOWN/perlu diperiksa; tidak ada angka pembelian palsu. |
| BOM kosong eksplisit | Nol kebutuhan aksesori saja. |
| BOM2→3 | Arsip186 tetap; sumber lama berubah dan kirim ditahan; analisis baru gross279. |
| Stok/WIP kini menutup gap | Tidak dikirim setelah pemeriksaan terkini yang sah. |

Fixture yang dapat dipakai: `cp7_material_need_cases.master/bom/prepared/`
`review_schedule`; `cp7_p19_staged_cases.staged_done/fetch`;
`cp7_p19_reminder_v2_cases.ready_set/conditions/recheck`.
Usulan empat diagnostik awal (belum ditulis/dijalankan):
ACCESSORY_NEED_NATIVE_186_EXTERNAL_UNKNOWN;
ACCESSORY_NEED_ISSUE80_NOT_INSTALLATION;
ACCESSORY_NEED_BOM_SUCCESSOR_STALES_WITHOUT_REWRITE;
ACCESSORY_NEED_MISSING_VS_EXPLICIT_EMPTY.
Kemudian tambah race perubahan BOM/izin saat menunggu, browser desktop/HP,
provider palsu, pesan UNKNOWN yang benar, dedup, kegagalan akhir dan restore.
Empat diagnostik sumber saja tidak menutup forwarding OW-01.
