# Validasi revisi2

Jalankan `python3 verification/validate_framework.py` dari root paket setelah menyediakan `jsonschema==4.25.1` pada environment terisolasi. Tidak menghubungi ERP atau provider. Receipt aktual berada di framework_validation.json.

`semantic_contract.py` adalah contoh guard persiapan untuk COUNT, edge/capacity, timeline mode, Stop dan beberapa referensi. Bukan parser/runtime produksi lengkap. Propagation unknown, seluruh rumus netting, permission, freshness, race, side effects dan transport masih memerlukan bukti native/Auth/HTTP/browser nanti.

TypeScript: `tsc --noEmit --skipLibCheck --target es2022 contracts/backbone.ts contracts/notification.ts`. AnalysisResult dihasilkan dari schema v2; pemeriksaan compiler tidak menggantikan semantic rules.

Semua84 kontrak kasus ERP tetap NOT_RUN. Sepuluh owner rows beririsan dengan271 kelompok lama. Jumlah cek offline tidak boleh diklaim sebagai tes ERP yang lulus. Contoh kernel angka yang disediakan baru SES; tiap kernel yang dipilih wajib mempunyai oracle sendiri sebelum P07 accepted.

History/v1 menyimpan framework asli, kontrak, dan laporan313 pemeriksaan milik paket asal. Probe original schema dapat diulang dengan `python3 review/probe_v1_contract.py`; hasil ditulis ke review/V1_PROBE_REPLAY.json. Ini batas schema, bukan vonis runtime ERP.

SHA256SUMS melindungi paket hasil akhir. Rerun yang mengubah receipt/artifact perlu dicatat sebagai delta dan menghasilkan checksum baru; jangan menyamarkan perubahan bukti.
