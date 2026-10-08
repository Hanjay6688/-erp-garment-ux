# Mulai audit independen P20 — CP7 (sesi terpisah)

Dokumen ini untuk **auditor di sesi terpisah**, bukan writer. Owner 8 Okt: "Audit harus memeriksa sendiri seluruh
cakupan, bukan cuma mengulang temuan penulis. Penulis tetap boleh membantu reproduksi dan perbaikan, tetapi tidak
memberi penerimaan independen."

## Paste block untuk membuka sesi auditor

> Kamu auditor independen P20 untuk CP7 ERP Garment (repo `Hanjay6688/-erp-garment-ux`). Kandidat beku = head
> `cp7/integration` yang tercatat di `docs/cp7/audit-candidate/final-20261008/FREEZE_RECEIPT.json` (cek SHA di sana;
> jangan memakai HEAD lain). Baca dulu `docs/AUDIT_PANDUAN_PRO_MAX.md` lengkap, lalu
> `docs/cp7/audit-candidate/final-20261008/README.md` dan dokumen ini. Periksa sendiri seluruh cakupan di bawah:
> susun kasus dan oracle-mu sendiri dari kontrak dan keputusan owner, jalankan di database sekali pakai/CI, dan
> laporkan temuan dengan bukti. Hasil writer hanya titik awal, bukan bukti lulus. Batas: jangan mengubah `main`,
> deployment Cloudflare, Supabase hosted Enteng (`siimvrusnzxexizpyoib`), legacy ERP-Garment
> (`vlxdhpkjeevubjxexnfo`, read-only) atau produksi; jangan push ke `claude/new-session-deapao` atau
> `cp7/integration`; jangan mengirim pesan ke orang lain; jangan meminta password/token/kunci; jangan melonggarkan
> oracle/guard; simpan log gagal pertama. Keputusan owner yang sudah disahkan tidak dibuka ulang.
> `production_go:false` tetap.

## Cakupan yang wajib diperiksa sendiri

Urutan otoritas dan aturan: `docs/AUDIT_PANDUAN_PRO_MAX.md` §0.1. Kontrak: `docs/cp7/framework-v2/01_KONTRAK_DAN_INTEGRASI.md`,
`04_BUKTI_DAN_ORACLE.md`, `06_RUSUK_KEBUTUHAN_OWNER.md`; keputusan owner: `docs/cp6-d11-kebijakan-dan-gbd03.md`,
`docs/contracts/ERP_ADDENDUM_OWNER_DECISIONS_CP6_2026-09-25*.md`, `docs/cp7/OWNER_DECISIONS_20261008.md`.

| Area | Pertanyaan audit minimal |
|---|---|
| Akses dan pemulihan | Hak diperiksa ulang setelah kunci; UUID disimpan sebelum tulis; lintas tab/rute; satu transaksi untuk koreksi/pembalikan; tidak ada jalur langsung Native yang bisa dieksekusi `authenticated` di luar fasad. |
| Keuangan dan laporan | Decimal eksak; laba = pendapatan − HPP − beban; jurnal/neraca seimbang; UNKNOWN tidak menjadi 0; keuangan dimuat saat perlu dan "tidak dimuat" ≠ nol; tanggal ekonomi/WIB. |
| AP/pembelian/bahan | GRNI, invoice terlambat, kredit/retur/pembayaran tanpa hitung ganda; koreksi penerimaan/nota/pembayaran supplier; AP-5. |
| AR/penjualan | Cadangan draf sekali; retur parsial menjaga lot/HPP; koreksi harga baris yang sudah diretur. |
| Stok/HPP/produksi | Konservasi PCS/biaya; root fisik vs SKU komersial; koreksi biaya kronologis; PL-8 bukti grup habis terikat versi sumber. |
| Payroll | Kode pekerja, absensi vs upah, BS/kompensasi, saldo negatif; aturan Afui tidak dikarang. |
| Perencanaan/model | Cutoff as-known; baseline/netting/jadwal/kain/aksesori; yield tidak pernah 100% (PL-5 B **belum** diimplementasikan dan harus tetap PENDING). |
| Analisis 5.000 target | Kontrak §10 `p19/P19_STAGED_5000_20261007.md`: satu acuan, paritas header+halaman ↔ analisis jalur tunggal, identity_hash, batas 8 dtk/unit dan 8.000.000 byte/halaman, 5.001 ditolak, pause/reload UUID sama, buka DONE tanpa hitung ulang, downstream staged dinyatakan tidak tersedia. |
| Pengingat/AI | Hanya dari hasil lengkap terverifikasi; sumber basi ditandai. |
| UI | 48 rute, 111 izin; mode demo/terhubung jelas; pesan penolakan; tanpa angka palsu saat gagal muat. |
| P21 (gladi) | `scripts/cp7_p21_full_rehearsal_probe.py` + `FULL_COMPOSITION_P21.sql.gz`: pasang/rollback/pasang ulang, pakai di-commit, backup terpakai → restore, rollback = restore pra-pasang; klasifikasi beda katalog (re-parse G-01, ACL = `acldefault`) benar-benar sama makna. Ini gladi, bukan pemasangan. |

## Bukti writer yang tersedia (untuk diuji ulang, bukan diterima begitu saja)

- `docs/cp7/P20_P21_PAKET_CABANG_CLAUDE.md` §1–§15, `docs/cp7/SELF_CHECK_FORMULAS_20261006.md`.
- `docs/cp7/evidence/gpt-staged-5000-20261008/` (Original, receipt, kegagalan pertama), `docs/cp7/evidence/p21-full-20261008/`.
- Paket sumber `../staged-5000-20261008/SOURCE_MANIFEST.json` + `SOURCE_DELTA.json`.

## Hasil yang diminta

1. Daftar temuan: ID, area, keparahan (blocker/major/minor), langkah reproduksi, bukti (log/run/Original), dampak ke angka/stok/HPP/laporan.
2. Vonis per area: LULUS / GAGAL / BELUM DIPERIKSA, dengan alasan. Area yang tidak diperiksa tidak boleh ditulis lulus.
3. Vonis akhir kandidat dan syaratnya. Hanya auditor yang boleh menulis penerimaan independen.

Writer boleh dimintai reproduksi atau perbaikan; perbaikan writer menjadi kandidat baru yang harus diperiksa ulang.
