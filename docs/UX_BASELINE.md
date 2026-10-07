# UX baseline (tampilan lama)

Tampilan sebelum perapian UX tetap bisa dipakai kapan saja. Ada dua jalan:

## 1. Di aplikasi — tombol "Tampilan lama"

- Desktop: pojok kanan atas (sebelah badge DEMO) ada pilihan **Tampilan baru / Tampilan lama**.
- HP: buka menu (☰), pilihan yang sama ada di bawah kartu "Mode Demo".
- Pilihan disimpan di browser (`localStorage` key `erp-ux-tampilan`, nilai `baru` atau `lama`).
  Default untuk pengguna baru: **Tampilan baru**. Kalau storage diblokir, pilihan berlaku sampai tab ditutup.

Cara kerjanya: semua aturan visual baru ada di satu file, `src/ux-rapih.css`, dan
hanya berlaku saat `<html>` punya class `ux-rapih`. "Tampilan lama" cukup
menghapus class itu, jadi stylesheet lama tampil persis seperti sebelumnya.

Fitur baru (filter mandor di Laundry, SKU di Barang BS & Rework, aksi
"Jadikan SKU baru") tetap ada di kedua tampilan — yang berubah hanya gaya visual.

## 2. Di git — commit baseline

| | |
|---|---|
| Baseline commit | `557005e6674058f1e5e966b350cba05501e06182` |
| Isi | Merge PR #27: dark blue access management demo (origin/main, 22 Sep 2026) |
| Branch perapian | `claude/ux-rapih-main` |

Mengembalikan kode ke baseline (misalnya untuk build pembanding):

```bash
git checkout 557005e6674058f1e5e966b350cba05501e06182
npm ci && npm run build
```

Membuang layer baru secara permanen tanpa membuang fitur: hapus import
`./ux-rapih.css` di `src/main.tsx`, hapus `src/ux-rapih.css`,
`scripts/generate-ux-rapih.mjs`, dan script `gen:ux-rapih` / `check:ux-rapih`
di `package.json` (termasuk pemanggilannya di `prebuild`).

Screenshot sebelum/sesudah: `docs/ux/` (lihat `docs/UX_STANDARD.md`).
