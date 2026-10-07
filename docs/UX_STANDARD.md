# UX standard — "Tampilan baru" (UX rapih)

Satu standar visual untuk seluruh ERP demo. Semua aturan ada di
`src/ux-rapih.css` dan hanya aktif saat `<html class="ux-rapih">`
(tombol **Tampilan baru / Tampilan lama**, lihat `docs/UX_BASELINE.md`).
Tema dark-blue tetap; yang berubah: ukuran huruf, kontras, pemisahan kotak,
hierarki tombol, dan dropdown.

## 1. Tipografi — satu skala

| Token | Ukuran | Dipakai untuk |
|---|---|---|
| `--fs-xs` | 12px | label huruf besar (eyebrow), chip, metadata — **ukuran terkecil** |
| `--fs-sm` | 13px | teks bantu, isi kontrol (`--text-control`) |
| `--fs-base` | 14px | isi tabel/kartu, angka per baris |
| `--fs-md` | 16px | judul kecil, angka penting |
| `--fs-lg` | 20px | judul panel (h2) |
| `--fs-xl` | 24px | angka KPI kecil, judul kartu besar |
| (display) | ≥ 28px / `clamp()` | judul halaman (h1) dan angka KPI utama — dibiarkan seperti desain asal |

- Font: `--font-sans` = Inter → Segoe UI → Roboto → Helvetica Neue → Arial → sans-serif
  (serif Georgia di halaman Pola/HPP ikut diganti). Kode/ID: `--font-mono`.
- Berat huruf hanya **400 / 600 / 700** (dulu ada 15 variasi 530–900).
- Line-height teks ≤ 16px: **1.4–1.5**; teks ≥ 20px: minimal 1.15.
- Angka: `font-variant-numeric: tabular-nums` di seluruh aplikasi (kolom angka lurus).
- **Tidak ada teks di bawah 12px.** Sebelumnya ada ±1.500 deklarasi 6–11px.

Penerapan: `scripts/generate-ux-rapih.mjs` membaca semua stylesheet dan
menulis "mirror" setiap deklarasi `font-size / font / line-height /
font-weight / font-family` di bawah `.ux-rapih`, nilai dibulatkan ke skala di
atas (px < 28 → langkah terdekat, minimal 12px). Mirror memakai urutan
bundle yang sama dan +1 class specificity, sehingga aturan yang menang tetap
sama — hanya nilainya yang dirapikan. `npm run build` gagal
(`check:ux-rapih`) kalau ada CSS baru yang belum di-mirror: jalankan
`npm run gen:ux-rapih`.

## 2. Warna & kontras

Rasio dihitung dengan rumus WCAG 2.x.

| Token | Nilai | Pasangan | Kontras |
|---|---|---|---|
| `--page-bg` | `#0a0c14` | — | — |
| `--card-bg` | `#131a2c` | kartu di atas page | 1.13 (dibantu border + shadow) |
| `--card-bg-inset` | `#19223a` | kotak dalam kartu / input | — |
| `--card-border` | `#2f3b5a` | garis kartu di atas card-bg | 1.56 (garis dekoratif) |
| `--card-border-strong` | `#44527c` | border tombol sekunder / menu | 2.26 |
| `--text-strong` | `#f3f5fb` | di card-bg / page-bg | **15.9 / 17.9** |
| `--text-soft` | `#d3d9e6` | di card-bg | **12.2** |
| `--text-muted` | `#a7b0c4` | di card-bg / inset | **7.96 / 7.25** |
| `--accent` | `#8fa0ff` | di card-bg | **7.13** |
| eyebrow | `#a3b0ff` | di page-bg | **9.49** |
| tombol primary | `#fff` di `#5466e4 → #4152cc` | | **4.78 – 6.36** |
| tombol sekunder | `#e2e7f5` di card-bg | | **14.0** |
| tombol nonaktif | `#9aa4bf` di `#232b45` | (dikecualikan WCAG) | 5.61 |
| placeholder | `#8f99b2` di inset | | **5.53** |
| status Good / Warn / BS | `#93e2c2` / `#f3cd8c` / `#ff9fae` | di card-bg | **11.5 / 11.5 / 9.1** |

Teks abu-abu lama (mis. `#6f7d91`, `#68758a`, 2.8–4.4 : 1) otomatis diangkat:
generator me-mirror deklarasi `color`, warna mid-tone dengan kontras 1.8–4.7
terhadap kartu terang `#212a42` dinaikkan kecerahannya (hue tetap) sampai
≥ 4.7 : 1. Teks hampir hitam (untuk chip/avatar terang) tidak disentuh.

## 3. Kartu, spasi, pemisahan kotak

- Kartu (`.panel` dan kartu halaman): `--card-bg` satu tingkat lebih terang
  dari page, **border 1px `--card-border`**, radius `--card-radius` 16px,
  shadow `--card-shadow`.
- Kotak di dalam kartu memakai `--card-bg-inset` atau border yang sama;
  garis pemisah yang tadinya hampir tak terlihat (`rgba(255,255,255,.05)`,
  `#2c3543`, …) dinaikkan otomatis (+0.08 alpha / campur 22% ke `#aab6e0`).
- Jarak antar kartu dan antar section: **16px** (`--space-card-gap`);
  grid KPI/dashboard ikut 16px.
- Setiap kelompok punya judul di atasnya (eyebrow 12px huruf besar + judul).
- Label di atas nilainya (mis. "MANDOR" di atas nama mandor, bukan
  menempel: "MANDORMandor Afat" sudah diperbaiki).

## 4. Tombol

| Jenis | Tampilan | Pakai untuk |
|---|---|---|
| Primary `.primary-btn` | isi biru `#5466e4→#4152cc`, teks putih **700**, border `#7f90ff`, min 40px | satu aksi utama per area (Simpan, Review, Catat) |
| Secondary `.soft-btn` | transparan, border `#44527c`, teks `#e2e7f5` 600, min 38px | Batal, Kembali, Simpan draft |
| Nonaktif | `#232b45`, teks `#9aa4bf`, tanpa shadow | kondisi belum lengkap |
| Fokus keyboard | outline 2px `--accent` | semua tombol, input, select |

## 5. Form & pesan

- Label huruf besar 12px di atas input; input punya border yang terlihat dan
  ring fokus.
- Field wajib diberi "· WAJIB" di label; contoh isi di placeholder
  (mis. "Contoh: 73001-B").
- Error validasi muncul di bawah field (`role="alert"`, merah muda `#ff9fae`),
  aksi berisiko memakai **langkah konfirmasi** (lihat "Jadikan SKU baru").
- Empty state selalu menyebut apa yang bisa dilakukan
  ("Coba ganti laundry, mandor, Pola, atau kata pencarian.").
- Ringkasan yang terfilter memberi tahu filternya
  ("Ringkasan & daftar difilter untuk Mandor Asep" + tombol reset).

## 6. Dropdown

- `color-scheme: dark` di root dan setiap `<select>`.
- `<option>`/`<optgroup>` **selalu** punya `background-color` dan `color`
  eksplisit (`--menu-bg #161e33` / `--menu-text #eef1f8`, 14.65 : 1). Ini
  wajib karena Chromium di Windows menggambar popup option dengan latar putih
  bawaan OS: warna teks terang yang diwarisi dari select menjadi
  putih-di-atas-putih.
- Terpilih: `#33427a` + putih (9.54 : 1). Hover menu custom: `#26325a` + putih
  (12.45 : 1). Nonaktif: `#8e98b0` di `#161e33` (5.73 : 1).
- Menu custom (filter sheet, EnterpriseSelect, submenu navigasi) memakai token
  yang sama.

## 7. Hasil audit (Playwright, build demo, 46 halaman × desktop 1440px + HP 390px)

Skrip audit membuka setiap submenu di mode DEMO dan mengukur keadaan awal halaman.

| Ukuran | Tampilan lama | Tampilan baru |
|---|---|---|
| Teks bertabrakan (kotak teks saling menimpa) | 15 | **0** |
| Teks terpotong tanpa ellipsis | 0 | **0** |
| Elemen teks < 12px (kombinasi elemen/ukuran) | 3.700 | **0** |
| Teks kontras < 4.5 : 1 (besar < 3 : 1) | 2.090 | **0** |
| Halaman dengan scroll horizontal | 2 (QC, HPP di HP) | **0** |
| Dropdown: select/option/menu dicek | 822 aktif + 17 nonaktif | 827 aktif + 17 nonaktif |
| Dropdown di bawah 4.5 : 1 | **213** (min 1.11 : 1, option putih-di-putih) | **0** (min 5.5 : 1) |

Catatan jujur: option native diukur dengan asumsi popup Windows berlatar
putih bila option tidak punya latar sendiri; teks dari `::before`
(`data-label`) dan dialog yang belum dibuka tidak ikut terukur otomatis — yang
penting (QC per size, form "Jadikan SKU baru", filter sheet) dicek manual
lewat screenshot.

## 8. Mood board

![Palet, skala huruf, tombol, menu](ux/palette.png)

## 9. Sebelum / sesudah

| Halaman | Sebelum | Sesudah |
|---|---|---|
| Laundry (filter mandor: Mandor Afat) | ![](ux/before-laundry-desktop.jpg) | ![](ux/after-laundry-desktop.jpg) |
| Barang BS & Rework (SKU di tiap baris) | ![](ux/before-bs-rework-desktop.jpg) | ![](ux/after-bs-rework-desktop.jpg) |
| WIP & Sewing | ![](ux/before-wip-sewing-desktop.jpg) | ![](ux/after-wip-sewing-desktop.jpg) |
| Dropdown filter (custom) | ![](ux/before-dropdown-filter.png) | ![](ux/after-dropdown-filter.png) |
| `<option>` di popup putih ala Windows | ![](ux/before-dropdown-native-options.png) | ![](ux/after-dropdown-native-options.png) |

Form baru "Jadikan SKU baru": ![](ux/after-bs-sku-baru-desktop.jpg)

Gambar di atas dikompres (JPEG lebar 1000px). Set lengkap resolusi penuh
(desktop 1440px + HP 390px, termasuk Dashboard dan Pembelian & Penerimaan,
32 file) dibuat ulang lokal di `docs/ux/full/` — folder itu di-`.gitignore`
supaya repo tidak membengkak.

## 10. Merawat standar ini

- Tambah/ubah CSS seperti biasa di file komponen, lalu `npm run gen:ux-rapih`.
  `prebuild` menjalankan `check:ux-rapih` dan gagal kalau mirror basi.
- Aturan tangan (kartu, tombol, dropdown, perbaikan tabrakan) ada di bagian
  "3. Hand-written" `src/ux-rapih.css`; selalu diawali `.ux-rapih`.
- Teks baru: pakai token (`var(--fs-sm)`, `var(--text-muted)`), jangan px < 12.
