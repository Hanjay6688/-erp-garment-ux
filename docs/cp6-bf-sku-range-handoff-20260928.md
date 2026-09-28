# BF — master SKU range dan tindak lanjut PR #29

Status: **NOT_READY / CP6 HOLD**. `production_go=false`, `audit_complete=false`.
Ini bukti writer, bukan penutupan auditor. Tidak ada perubahan production/UAT/legacy, deploy, atau merge main.

## Aturan owner yang dipertahankan

SKU adalah identitas komersial bersama. Harga jual, resep aksesori, dan pengaturan tarif jasa ditulis sekali per SKU. Produk fisik, stok, lot, penerima jasa, allocation penjualan, retur, dan sumber biaya tetap per ukuran. SKU khusus27 terpisah; produksi hanya32 tetap memakai SKU/rate range asal. Satu wave boleh memuat lebih dari satu SKU. Referensi tarif sebelum QC tidak menetapkan identitas FG final.

Perubahan31–33 menjadi31–34 membuat versi keanggotaan bertanggal secara atomik pada kedua kelompok. Tidak mengubah identitas fisik, memindah ledger lama, mengulang reservasi, atau menulis ulang transaksi posted. Price/BOM null berarti belum dikonfigurasi; BOM kosong berarti keputusan tanpa aksesori.

## Peta perubahan dan dampak tetangga

| Titik | Implementasi | Sambungan yang diperiksa |
|---|---|---|
| Master komersial | `bf_skus_v1`, versi bertanggal, anggota physical root, satu writer lock dan expected revision | Harga/BOM lama, konflik adopsi, perubahan anggota, request replay, hak keuangan |
| Harga/resep | Satu perubahan grup menghasilkan child version untuk setiap ukuran | Consumer lama tetap memakai exact root; tulis per ukuran diblokir; old posted history tetap |
| PO dan jasa jahit | Snapshot PO + komponen + versi SKU; kapasitas dan biaya dipisah per SKU dalam wave | Work completion, BS entitlement, rework, sumber HPP; tidak menggabungkan semua ukuran satu PO secara membabi buta |
| Laundry | PROCESS/COMPONENT/PACKAGE dengan override SKU atau dasar vendor, provenance disimpan | Coverage actual PCS/size, FREE/WAIVED, extra paket, receipt allocation, invoice variance dan HPP |
| Aksesori | Resep SKU dipakai per actual GOOD PCS; komitmen PO tetap dikunci | Rework memilih item actual, kompatibilitas resep PO legacy, anggota baru tidak mengganti resep PO lama |
| Ringkasan HPP | Nilai sisa lot / PCS sisa semua anggota SKU pada tanggal laporan | Filter lokasi/grade/tanggal konsisten, drill-down physical size/lot, status provisional; FIFO/COGS tidak diganti |
| UI master/HPP | Halaman connected, preflight konflik, transfer kelompok, pagination, permission masking, mutation recovery | Mobile, stale reads, replay sesudah izin dicabut, SKU tanpa economics |
| Cut/QC/FG/simulasi | Daftar ukuran nyata; merge berdasarkan label ukuran | Singleton27, 4 anggota, BS, nota FG, stock vectors; tidak memotong array menjadi3 |
| Impor | Resolver identitas fisik dipakai validator dan apply | Sales draft, titipan, historical pocket COGS, BS/rework; ambiguous ditolak sebelum posting |
| Recovery | Kapsul exact definition sebelum BF, verifikasi hash dan rollback hanya sebelum dipakai | Restore unique lama, constraints, fungsi, triggers; tidak menghapus keputusan setelah digunakan |

## Enam temuan PR #29

Dokumen asli dipertahankan di `docs/cp6-sku-range-audit-delta-writer-handoff-20260928.md`.

| Temuan | Revisi | Bukti yang dibutuhkan / batas |
|---|---|---|
| SR-01 helper mengasumsikan3 | Ukuran actual menjadi parameter; singleton12 dan4×3; pembagian5 ukuran meminta manual | Unit helper lulus; tidak menerima pembagian sisa otomatis tanpa aturan owner |
| SR-02 manual13 berubah akibat1,08lusin | Manual PCS mengosongkan helper; helper kosong no-op; label lusin + sisa PCS | Browser desktop/mobile PASS pada616f4ec; ini UI simulasi, bukan bukti posting sales connected |
| SR-03 OPEN_SALES_DRAFT SKU ambigu | Wajib resolve tepat satu physical product; tambahan size/brand/model/color atau product_id | Ambiguity, exact FK32/reservasi/replay dan stock atomic refusal PASS pada616f4ec |
| SR-04 custody/pocket COGS ambigu | Resolver yang sama; descriptive custody tanpa SKU tetap null | Exact FK32, reservation sekali, COGS32, titipan deskriptif dan replay PASS pada616f4ec; nullable custody tidak membolehkan COGS tanpa identitas |
| SR-05 rework memakai sibling pertama | Produk diturunkan dari BS source payload | Negative sibling-BOM dan positive source-BOM sampai completion serta nilai GOOD19,50 PASS pada616f4ec |
| SR-06 simulasi fixed triple/range string | Vektor dinamis dan matching actual size;27 tersedia | Unit/build lulus; connected master singleton/4 ukuran diuji, bukan seluruh simulasi secara otomatis |

## Bukti sementara dan riwayat koreksi

- Unit aplikasi pada `616f4ec`: `npx vitest run src` —52 file,573 test PASS. Pemanggilan awal tanpa scope juga memuat4 spec Playwright dengan runner yang salah; bukan bukti gagal produk dan tidak dihitung PASS.
- Build resmi lokal `npm run build` PASS; pemeriksaan source ownership, access catalog, CSS dan artifact scan ikut lewat.
- `fa942e9`: native30 PASS/1 INCOMPLETE, browser19 PASS. Fixture mixed-wave membuka ambiguity variabel SQL; diperbaiki.
- `2d26d2e`: native30 PASS/1 INCOMPLETE, browser19 PASS. Fixture memanggil fungsi private; diperbaiki ke facade authenticated v2.
- `32695e4`: verifikasi instalasi gagal karena registry verifier BE membandingkan nama dengan signature lengkap; diperbaiki. Verifikasi exact body BF tetap wajib.
- `d63db69`: native33 PASS/2 INCOMPLETE, browser20 PASS/1 INCOMPLETE. Replay impor memakai request baru (guard menolak dengan benar), laundry membaca record yang belum terisi, selector browser resep ambigu. Ketiganya diperbaiki pada `df4022c`.
- `df4022c`: run36371146417 native35 PASS, browser21 PASS, HTTP7 PASS, races18 PASS/2 INCOMPLETE; CodeQL4 bahasa PASS. Kedua race baru gagal setup nominal fixture tanpa dua desimal; guard produk benar. Fixture diperbaiki, dan UI kini menormalkan input nominal biasa menjadi teks tepat dua desimal tanpa floating point. Run ini membuktikan mixed-wave work/laundry/QC, exact import/replay, unused rollback dan used refusal. Bukan seluruh gap rework/recipe pin.

- `616f4ec95b3f78d134647332885af6288d3a992a`: run36371832655/job108769632784 — **native38 PASS, races20 PASS, HTTP7 PASS, browser23 PASS; tidak ada FAIL/INCOMPLETE**. Runtime self-test PASS. CodeQL run36371832642:4 job PASS. Build resmi lokal dan573 unit PASS.
- Bukti terstruktur: `docs/evidence/cp6-bf/df4022c.json` menyimpan kegagalan fixture sebelumnya; `docs/evidence/cp6-bf/616f4ec.json` menyimpan hasil kandidat akhir. Commit handoff berikutnya hanya dokumentasi/bukti, tidak mengubah source yang diuji.
- Bukti baru mencakup tarif hari ini saat versi masa depan ada, guard calon anggota yang belum diadopsi, resep nonkosong bersama, HPP weighted13 PCS dari3 ukuran dan laporan sebelum FG yang kosong. Dua race master membuktikan commit pertama menolak stale writer, sedangkan rollback pertama membolehkan writer kedua.

## Batas yang tidak boleh disamarkan

Belum audit data bisnis live; belum mengukur jumlah SKU lama yang konflik. HP fisik belum diuji. Halaman sales masih simulasi existing; perubahan helper tidak membuatnya menjadi posting connected. BF masih family development, belum paket release yang diterapkan. Setiap INCOMPLETE/FAIL wajib tetap tampak dalam evidence. Cost source work/laundry dua SKU dalam satu wave dan rework impor exact source telah PASS. Pengujian ini bukan bukti seluruh kombinasi recipe pin PO legacy, penambahan anggota pada PO yang sedang berjalan, dan rework bertarif SKU; kombinasi itu tetap perlu perluasan audit sebelum klaim BF menyeluruh.

Jalur celup ulang BE memiliki service attempt dan price source vendor/proses tersendiri. Jangan menganggap pengujian laundry normal sudah membuktikan override SKU untuk celup ulang; pemetaan sumber SKU/target perubahan identitas perlu ditelusuri tersendiri.

## Lokasi implementasi

Backend: `scripts/cp6_bf_objects_{master,rates,work,laundry,import,router}.sql`, builders BF, generated `supabase/dev/cp6_bf_t1_family.sql` dan rollbackT2. Jangan mengedit migration historis untuk menyembunyikan revisi.

UI: `ConnectedSkuMasterPage.tsx`, `SkuSettingsFields.tsx`, `SkuWaveReferences.tsx`, `ConnectedSkuHppPage.tsx`, modelSKU; konsumen dynamic size pada App, sales, QC, FG, BS, inventory conversion dan cutting.

Qualification: `scripts/cp6_bf_probe.py`, `cp6_bf_modes.py`, `cp6_bf_browser.mjs`, `cp6_bf_browser_fixture.py`. Semua database uji disposable; label WRITER_SCENARIO.
