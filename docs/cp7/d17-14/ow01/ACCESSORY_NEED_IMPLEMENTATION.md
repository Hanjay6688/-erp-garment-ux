# Expected sebelum implementasi — WA kebutuhan aksesori

Basef412e61b. D17-14 sudah memberi izin seluruh jenis pengingat. Putaran
ini memakai enam pemeriksa Sol Max tanpa edit produk; writer utama integrator.
Penilaian awal dicatat sendiri sebelum counterexchange. Ini review internal.

Kontrak: kondisi tetap DATA_REVIEW dan local preview SOURCE_REVIEW_REQUIRED.
Recheck yang membuktikan sumber lengkap dan belum berubah dapat memberi
REVIEW_REQUIRED_NOW, dengan wa_notice_eligibility terpisah: kebijakan lengkap
dan enabled secara eksplisit, target override utuh, threshold_status
NOT_EVALUATED_UNKNOWN. Tidak ada klaim ambang jumlah sudah tercapai.
WA memakai quiet/repeat/pacing sendiri; quiet/cooldown policy pratinjau lokal
bukan pengaturan kirim WA. Perbedaan awal pemeriksa diselesaikan lewat
rule-policy150 serta alerts590/934, bukan voting.

Detail raw tertutup: run_id,data_as_of,checked_at,label,target_key,category_key,
category_name,state,verdict,gross_state,gross_qty,unit,installed_state,
installed_proven,unused_allocated_state,unused_allocated_proven,
additional_external_state,additional_external,threshold_status,reason.
Tiga fakta physical coverage tetap UNKNOWN/null. Gross KNOWN/ASSUMED positif
adalah kebutuhan BOM, bukan pembelian; UNKNOWN selalu null. Missing/ambiguous
BOM lengkap dapat diberitahukan dengan UNKNOWN_BOM dan alasan khusus;
pembacaan gagal/tidak lengkap/akses dicabut tidak dapat menjadi izin kirim.
BOM kosong eksplisit tidak dikirim. Subjek jenis+target+kategori tetap sama
antar run; refresh atau sumber basi tidak membuat episode/instant baru.

Live source satu snapshot STABLE dan clock setelah tunggu terakhir,
membandingkan target/BOM/kategori/profil/jadwal/policy dan sisa kebutuhan.
FG/BF bukan klaim membekukan seluruh WIP; notice adalah advisory diperiksa
pada checked_at, bukan otorisasi pembelian/produksi. Shared master locks dan
row kategori mengikuti penulis sebenarnya, tanpa memberi privilege UPDATE
ERP ke pembaca. Sumber berubah ditahan, arsip tidak ditulis ulang.

Golden: gap93×BOM2 gross186 ASSUMED, tambahan UNKNOWN; receive/issue80
tidak membuktikan installation; BOM2→3 menahan arsip lama dan analisis baru
gross279; known-empty nol tidak dikirim; target disabled/covered, izin dicabut,
policy kosong/disabled dan hasil provider UNKNOWN tidak dikirim ulang.
Native65 lama tetap. Tambahan direncanakan12 (Native6/race3/HTTP1/browser2)
menjadi77; ID final harus dicatat sebelum dijalankan. Kasus fake-provider
harus membaca receipt provider, bukan hanya antrean pg_net.

Frontend expected di waAccessoryNeed.test.ts ditulis sebelum produk:
notice angka tidak diketahui, gross hanya BOM, missing/ambiguous/category
truthful, payload angka JS/null/UNKNOWN/subject/party tak cocok ditolak.
