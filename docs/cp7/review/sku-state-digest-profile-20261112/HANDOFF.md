# CP7 | Profil CPU dan usulan patch digest SKU v1

12 November 2026 WIB. Acuan patch `e4eaaecebad1f0ba11ab1542b5df89a6423a8a1e` / tree `ead4c59721d1fc1dc608a9f803dbaf2a076abbdd`. `package.py` yang mengukur digest identik pada `a1652a8` dan `e4eaaec`. Bukti B disiapkan untuk penerapan oleh A.

## Pengukuran

15 fase `SKU_COMPLETE_PARENT_STATE_DIGEST` pada run `43105533441` memakan **77 menit 0,403 detik** waktu dinding dan **75 menit 55,312 detik** CPU. Masing-masing fase mengapit pemanggilan encoder digest. Porsi CPU mencapai 98,6%. `package.py` pada run itu sudah memakai cache string versi pertama A. [Job asli](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/43105533441/job/130807755829) · [30 catatan awal/akhir fase](A165_DIGEST_PHASES.json)

| Muatan replay | Median CPU acuan → patch | Pengurangan CPU |
| --- | --- | --- |
| Katalog asli Native27, 22 kelompok, before/after berbagi objek | 1,077 → 0,646 detik | 40,0% |
| Katalog asli Native27 dan proyeksi 22 kelompok dari A165 | 0,937 → 0,714 detik | 23,8% |
| Katalog asli A165, 25 kelompok, dengan induk bertingkat | 1,973 → 1,437 detik | 27,2% |
| Total 15 pasangan, waktu dinding | 22,303 → 14,922 detik | 33,1% |

Setiap pasangan menjalankan dua implementasi pada objek input yang sama. Urutan acuan/patch dibalik bergantian. CPU patch lebih rendah di 15/15 pasangan dan SHA-256 sama di 15/15 pasangan. Profil `cProfile` pada katalog A165 mencatat panggilan Python dan C turun dari 5.065.670 ke 2.912.560, terutama pada flush, jalur daftar skalar dan pengodean nilai berulang. [Hasil per pasangan dan profil](REPLAY_RESULT.json)

Muatan katalog berasal dari dua arsip asli yang SHA-256 dan seluruh CRC-nya lulus, 139 + 170 anggota. Pembungkus state dibuat untuk replay dengan tiga tag binding produksi. Job historis mencatat waktu 15 panggilan, sedangkan seluruh 15 preimage in-memory tidak disimpan di artefak. Ukuran muatan dan waktu runner gabungan baru perlu diukur pada kandidat yang A integrasikan. [A165 Original 13902367418](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/43105533441/artifacts/13902367418) · [Native27 Original 13031164777](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/41167734749/artifacts/13031164777)

## Patch dan bukti kesetaraan

- Buffer byte tetap dialirkan ke SHA-256. Ambang flush diperiksa pada batas nilai. Kunci tetap diurutkan menurut byte kanonis v1. Deteksi daftar skalar memakai tipe eksak.
- Cache hanya untuk `str` dan `int` eksak selama satu digest. Batas cache teks 24 MiB byte terenkode dengan maksimum 65.536 entri. Cache int paling banyak 2.048 entri dengan maksimum 64 byte per nilai. Hash keseluruhan tetap dihitung pada setiap pemanggilan.
- Tiga preimage dicocokkan byte demi byte terhadap `state_value` + JSON kanonis, termasuk campuran tipe, Unicode, ambang buffer dan kapasitas cache, serta perubahan state bertingkat. Lima penolakan input cocok jenis dan pesannya. Enam tes yang sudah ada lulus, termasuk tiga binding dan penjagaan otoritas installer.
- Diff hanya berisi encoder di `package.py` dan pin berkas tersebut di `SOURCE.json`. `git apply --check` lulus pada arsip tepat E4EA. Pemanggilan binding, observasi 15 fase, SQL produk dan alur pemasangan tetap menggunakan sumber E4EA.

Patch [SKU_STATE_DIGEST_V1_CPU.patch](SKU_STATE_DIGEST_V1_CPU.patch). Di salinan kandidat A, cocokkan preimage `package.py` SHA-256 `4e21d65e1bed0a802c47567f8d285cc0f3081dcb82d7b6d2f5a9ada3e4f5810d` dan pin `SOURCE.json` sebelum penerapan selektif. Postimage `package.py` SHA-256 `574e909d7bb77865b4306322e007de5b6e83cfc28a8d6e19432e0fcd100e597a`.

```bash
git show e4eaaecebad1f0ba11ab1542b5df89a6423a8a1e:scripts/current-sku-automatic-composite-preparation/package.py > /tmp/sku-digest-baseline.py
git apply --check /path/to/SKU_STATE_DIGEST_V1_CPU.patch
git apply /path/to/SKU_STATE_DIGEST_V1_CPU.patch
python -B /path/to/replay_digest.py /tmp/sku-digest-baseline.py \
  scripts/current-sku-automatic-composite-preparation/package.py \
  /path/to/a165-original.zip /path/to/native27-original.zip /tmp/sku-digest-replay.json
cd scripts/current-sku-automatic-composite-preparation
python -B -m unittest -v test_qualification.CompleteStateBindingControls test_qualification.InstallAuthorityControls
```

## Prasyarat jalur berikutnya

Prasyarat Global yang sudah diperiksa A dipakai ulang. Katalog diagnostik A165 cocok pada 208 baris otoritas dengan nol selisih. Aktor, izin efektif, data uji dan periode perlu dicocokkan terhadap salinan gabungan dari artefak SKU terminal yang diterima. Kasus invoice susulan supplier dan inverse yang sudah ada di rencana Native25 tetap di run A. Celah supplier, kas dan aksesori di luar matriks itu perlu ditentukan dari bukti terminal sebelum memakai driver berikutnya. [Pemeriksaan otoritas A](https://github.com/Hanjay6688/-erp-garment-ux/blob/efea94b835a08c971681d3288e2bc12c64a580b1/docs/cp7/review/shutdown-20261111/sku-43132617378/A165_ACTUAL_AUTHORITY_DIAGNOSTIC.json)
