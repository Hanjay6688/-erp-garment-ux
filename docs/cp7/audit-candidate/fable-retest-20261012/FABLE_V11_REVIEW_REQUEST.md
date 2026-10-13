# Permintaan tinjauan untuk laporan Fable v1.1 (owner 13 Okt 2026)

Owner: "Minta Fable meninjau bukti diagnosis dan gladi untuk laporan v1.1. Dua kasus CP6 yang disebut dipensiunkan
harus punya rujukan keputusan dan cakupan penggantinya."

## Paste block

> Kamu auditor Fable untuk CP7 ERP Garment (repo `Hanjay6688/-erp-garment-ux`, cabang `claude/new-session-deapao`),
> menyiapkan laporan uji ulang v1.1 atas kandidat `7a0b4a90` (register `audit/fable_cp7/OWNER_DECISIONS_TO_AUDITOR_20261013.md`
> commit `1a808bc9`). Tinjau bukti penulis berikut terhadap tabel bentuk bukti di register-mu:
> (1) diagnosis selisih akhir grup bayar supplier: `docs/cp7/evidence/fable-retest-20261012/GROUP_END_DIAGNOSIS.md`,
> log `01`–`07` dan `06_group_end_repeat_diagnosis_run38357098820.json` di folder yang sama; status tetap OPEN,
> kegagalan tidak terulang pada pengujian berikutnya, kecepatan mesin belum dapat disingkirkan;
> (2) gladi jadwal di salinan CI: `docs/cp7/evidence/fable-retest-20261012/SCHEDULE_REHEARSAL.md` dan log `08`;
> (3) dua kasus CP6 yang dipensiunkan (PRE-05): `docs/cp7/RETIRED_CP6_SALES_MANUAL_13.md`;
> (4) keputusan owner D13-1..D13-6 di `docs/cp7/OWNER_DECISIONS_20261008.md` (D13-1..3 disalin dari registermu; D13-4..6
> jawaban owner atas usulan backup). Alat uji yang berubah sesudah `7a0b4a90` terdaftar di
> `docs/cp7/audit-candidate/fable-retest-20261012/AUDITOR_RETEST.md` bagian "Perubahan sesudah kandidat"; kode produk
> tidak berubah kecuali alat backup malam `scripts/cp7_nightly_backup.py`, yang diperbaiki untuk temuan Astra
> ASR-OPS-01 (keluarga F-OPS-01-mu) di `85e17168` — paketnya `docs/cp7/audit-candidate/asr-ops-01-retest-20261013/`;
> boleh diuji silang. Keputusan owner yang sudah disahkan tidak dibuka ulang. Batas: jangan mengubah `main`,
> deployment Cloudflare, Supabase hosted Enteng (`siimvrusnzxexizpyoib`), legacy ERP-Garment
> (`vlxdhpkjeevubjxexnfo`, read-only) atau produksi; jangan push ke `claude/new-session-deapao`, `cp7/integration`
> atau cabang audit lama; jangan memasang jadwal pg_cron atau backup malam di database mana pun selain salinan sekali
> pakai; jangan mengirim pesan ke orang lain; jangan meminta password/token/kunci; jangan melonggarkan oracle/guard;
> simpan log gagal pertama. `production_go:false` tetap.

## Catatan penulis untuk peninjau

- Pesan commit `71594a0b` menulis "runner speed is ruled out". Kalimat itu tidak benar, dan dokumen sudah dibetulkan
  (`GROUP_END_DIAGNOSIS.md` bagian 4 butir 5). Pesan commit tidak diubah, karena riwayat commit tidak ditulis ulang.
- `CP7 Shell S0` merah di `5b8e9d74` (run 38355457365), karena uji diagnosis memuat `psycopg`. Hal ini diperbaiki di
  `5e96cbcf` (fungsi dipindah tanpa perubahan isi ke `scripts/cp6_auditor_difference.py`), lalu Shell S0 hijau.
- `CP6 Auditor Scenario` merah di push `5b8e9d74` dan `5e96cbcf`. Penyebabnya sama dengan yang tercatat sejak 2 Okt:
  READINESS ×2 karena RPC CP7 tidak ada di paket CP6 saja (F-UI-02), dan `SALES_MANUAL_13` ×2 yang menjadi pokok
  butir (3). Workflow ini bukan bagian dari 15 workflow kualifikasi.
