# Paket uji ulang r3 CP1–CP7 (perbaikan atas audit r2 `2e9d6a46`)

**Status: SEDANG DIKUALIFIKASI — kandidat belum dipatok. Bagian Kandidat diisi sesudah semua workflow berjalan pada satu
commit.**

Fable, Astra dan Sol menguji ulang kandidat r2 `2e9d6a46`. Penulis menyatukan ketiga laporan per akar masalah di
`CROSS_AUDIT.md` (R3-01 sampai R3-09), lalu memperbaiki semuanya di cabang `claude/r3-fixes-20261017` bersama keputusan
owner D16-1 sampai D16-5 (`docs/cp7/OWNER_DECISIONS_20261008.md`). Paket ini satu kandidat untuk ketiga auditor. Owner
yang mengirim: salin kotak di `HANDOFF_FABLE.md`, `HANDOFF_ASTRA.md` dan `HANDOFF_SOL.md` ke sesi masing-masing auditor.
Penulis tidak mengirim apa pun.

| Berkas | Isi |
|---|---|
| `README.md` | Status, kandidat, perbaikan per akar, butir yang sudah diketahui |
| `CROSS_AUDIT.md` | Audit silang ketiga laporan r2 dan rencana r3 (ditulis sebelum perbaikan) |
| `SCREEN_MAP.md` | 47 menu × 3 mode sesudah D16-1 dan D16-5, uji browser per layar |
| `R3_08_CP6_WORKFLOW_SUCCESSORS.md` / `.json` | Pemetaan kasus pengganti untuk workflow CP6 lama yang merah karena pemeriksa historis (R3-08) |
| `R3_09_RATE_CHOICE_DESIGN.md` | Rancangan pilihan tarif lama/baru (D16-2..D16-4) |
| `HANDOFF_FABLE.md`, `HANDOFF_ASTRA.md`, `HANDOFF_SOL.md` | Kotak yang disalin owner ke sesi masing-masing auditor |
| `CI_RECEIPT.json` | Semua run workflow dan job pada kandidat (dibuat sesudah kualifikasi) |
| `../../cp17/R3_WRITER_HANDOFF.md` | Serah-terima untuk penulis cadangan, termasuk log titik simpan (bukan untuk auditor) |
| `../../cp17/R3_INSTALL_TIME_CHECKS.md` | Pemeriksaan yang hanya bisa dilakukan di database Enteng saat pemasangan (CP7C), bukan sekarang |

## Kandidat

(Diisi sesudah kualifikasi: commit, tree, receipt, hasil CP17 per grup.)

## Perbaikan per akar

Kasus CP17 dideklarasikan sebelum dijalankan di `docs/cp7/cp17/CP17_FIXES.json` (bagian `findings` menjelaskan tiap akar
dalam bahasa Inggris) dan dijalankan workflow "CP7 CP17 Fixes". Jumlah kasus: 321 (Native 153, race 34, HTTP Auth nyata
24, browser 55, dan 55 kasus browser yang sama di build mode Enteng). Kasus gagal auditor dipakai dengan angka dan hasil
yang diharapkan auditor sendiri; penjaga lama tidak dilonggarkan.

| Akar | Temuan | Keputusan owner | Yang berubah | Uji |
|---|---|---|---|---|
| R3-01 nomor PO otomatis lewat 999 | ASTRA-R2-02, SOL-R2-001 | — | Tiga digit menjadi lebar minimum; kunci per tanggal, UUID dan atomik tetap. `scripts/cp7-src/cutting-correction/auto-po.sql` | Kasus Astra dan Sol apa adanya (998/999/1000 header, batas waktunya), 1001, 9999→10000, dua sesi di batas, UUID sama: `CP17_R3_01_*`, `CP17_RACE_R3_01_*` |
| R3-02 buka ulang PO sesudah pemakaian barang jadi dibatalkan | ASTRA-R2-01 | — | Hanya pemakaian yang masih aktif menghalangi; penghalang lain tetap. `po-reopen.sql` | Dua kasus Astra apa adanya (draf penjualan batal; penyesuaian barang jadi dibalik), kontrol pemakaian aktif, pemasukan lain tidak menutupi, satu dari dua draf batal, buka ulang lalu selesai lagi sama: `CP17_R3_02_*`, `CP17_RACE_R3_02_*` |
| R3-03 layar Enteng diselesaikan, bukan disembunyikan | Oracle Fable 1–5 | D16-1 | Tidak ada lagi menu HIDDEN di Enteng; 11 menu memakai komponen tersambung yang sama dengan mode uji; Susun Nota FG tersambung; lima layar baru membaca data nyata: Reminder, Pengaturan ERP, Audit Trail, Riwayat Pelanggan, Ringkasan Gudang (`scripts/cp7-src/{manual-reminders,erp-settings,audit,sales/customer-history,warehouse-summary}`, `src/Connected*Page.tsx`) | `src/screenActivation.test.ts` (47 menu, nol HIDDEN dan nol data contoh di Enteng); `CP17_R3_03_{REMINDERS,ERP_SETTINGS,AUDIT,HISTORY,WAREHOUSE}_*` Native, race, HTTP, browser desktop + HP dengan peran terbatas |
| R3-03 build mode Enteng diuji | Oracle Fable 2 dan 5 | D16-1 | Semua kasus browser CP17 berjalan lagi di build mode Enteng (`AUDITOR_UI_MODE=ENTENG`, id `_ENTENG`) terhadap salinan sekali pakai; alamat proyek Enteng dijawab API lokal, alamat lain diblokir | Grup `browser_enteng` (55 kasus) di workflow yang sama |
| R3-03 rantai lewat layar | Oracle Fable 3 | D16-1 | — (kasus baru) | `CP17_BROWSER_R3_03_CHAIN_SEWING_TO_CLOSE` (jahit → Nota → payroll → bayar → Kas & Bank → laporan → tutup buku, ADMIN tanpa tombol bayar/tutup), `_CHAIN_FG_TO_AR_ZERO` (HP: barang jadi → invoice → bayar → kas → piutang nol), `_GUARDS_REFUSE` (D14-2, D14-3/D15-1, D15-5 menolak dengan kalimat persis, tanpa perubahan) |
| R3-04 layar pool HPP absensi | Sol KNOWN-R2-POOL-UI, sisa ASTRA-C17-07 | D16-1 | "Pool HPP absensi" di HPP & Rekalkulasi: pratinjau, draf, aktifkan, batalkan, pool pengganti, hanya lewat penulis Native; token tinjauan, alasan, satu jawaban per permintaan, periode tertutup ditolak. `scripts/cp7-src/hpp-pool/pool.sql`, `src/AttendanceHppPoolPanel.tsx` | `CP17_R3_04_HPP_POOL_*` (10 Native), 3 race, 2 HTTP, browser desktop + HP |
| R3-05 langkah rantai tanpa uji layar | FABLE-016 sisa | — | — (kasus baru) | `CP17_BROWSER_R3_05_QC_FINAL_SKU_DESKTOP/_MOBILE` (peran lihat saja + OWNER posting, jawaban hilang lalu cek status dengan UUID lama), `_ACCESSORY_NOTE_TO_PAYROLL_DESKTOP` |
| R3-06 helper alert Laundry | FABLE-018 | — | Teks alert diambil tanpa menunggu elemen yang sudah hilang; oracle `BD_BROWSER:OWNER_POLICY_SET_AND_CLEAR` tidak diubah. `scripts/cp6_bd_browser.mjs` | Workflow BD browser |
| R3-07 alat receipt membaca semua halaman | E19a, Sol KNOWN-RECEIPT-FIRST100 | — | Paginasi run, job dan anotasi. `scripts/cp7_ci_receipt.py` (commit `0e9e6fbc`) | Diperiksa penulis: 116 run pada `2e9d6a46` (alat lama membaca 100) dan daftar tiruan 237 baris dalam tiga halaman; receipt r3 dibuat dengan alat di repo |
| R3-08 klaim regresi workflow CP6 lama | Astra §5 | — | Pemetaan kasus pengganti per workflow (bukan klaim regresi arsip lengkap) | `R3_08_CP6_WORKFLOW_SUCCESSORS.md` |
| R3-09 tarif lama atau baru saat jahit selesai | — | D16-2, D16-3, D16-4 | Layar jahit selesai menampilkan tarif terkunci PO dan tarif mandor yang berlaku, wajib pilih dengan alasan bila berbeda; tombol per PO "pakai tarif baru seterusnya"; hanya Owner/Admin. Delta Native terdeklarasi. `R3_09_RATE_CHOICE_DESIGN.md` | `CP17_R3_09_*`, race, HTTP, browser desktop + HP |
| D16-5 Laporan & Tutup Buku | — | D16-5 | Menu "Tutup Periode" digabung sebagai tab "Tutup Buku"; hak lihat laporan dan hak tutup buku tetap terpisah; riwayat tutup/buka dari baris audit Native; tautan lama membuka tab itu | `CP17_R3_03_PERIOD_*` (Native, HTTP, browser desktop + HP; ADMIN tanpa tab), workflow "CP7 P13 Period control" |

## Ditemukan penulis selama kualifikasi r3 (diperbaiki)

- **Layar kasbon:** sesudah server menolak kasbon, layar menambahkan "Refetch authoritative gagal; writer tetap terkunci"
  padahal pembacaan ulang berhasil (pembacaan yang kalah oleh pembacaan lebih baru dianggap gagal).
  `src/PayrollKasbonPanel.tsx`, uji DOM baru gagal sebelum dan lulus sesudah perbaikan. Best practice 18c.
- Data uji yang salah (bukan aplikasi), diperbaiki tanpa mengubah oracle: kode peran lebih panjang dari kolom Native
  (Ringkasan Gudang HTTP), pencari elemen yang menemukan dua landmark utama (Ringkasan Gudang browser), hari absensi
  kosong peninggalan fixture lain yang menghalangi tutup buku (rantai jahit → tutup; best practice 25e), dan kasus QC
  desktop yang memeriksa jawaban sebelum server selesai menjawab. Log gagal disimpan; rinciannya di log titik simpan
  `docs/cp7/cp17/R3_WRITER_HANDOFF.md`.

## Butir yang sudah diketahui penulis (bukan temuan auditor; boleh diuji)

- **Lapisan CP7 belum terpasang di Enteng** (CP7C ditahan, D13-9a). Layar tersambung di build Enteng memanggil RPC
  `erp_cp7_*` yang baru ada sesudah pemasangan itu. Uji build Enteng memakai salinan sekali pakai, tidak ke hosted.
  Pemeriksaan yang hanya bisa dilakukan di database Enteng: `docs/cp7/cp17/R3_INSTALL_TIME_CHECKS.md`.
- **Pembungkus publik CP4 pool HPP** (`public.erp_{preview,create,activate,cancel}_attendance_hpp_pool_v1`) masih bisa
  dipanggil pengguna login dan tidak memakai penolakan periode tertutup milik fasad baru. Dicatat untuk batch pencabutan
  CP7C bersama FABLE-012 (D14-9); `cp7_hpp_pool_bundle.verify` melaporkannya.
- **Ringkasan Gudang:** peringatan "kain di bawah stok minimum" butuh hak `master.fabric.view` (aturan katalog); GUDANG
  tidak melihatnya kecuali hak itu diberikan di Pengguna & Hak Akses.
- **Sensus lebar HP 47 menu** memakai build demo; layar tersambung diperiksa per uji browser HP yang melewatinya.
- **FABLE-012:** 82 penulis `erp` masih bisa dieksekusi `authenticated` lewat SQL, tidak terjangkau Data API; ditunda ke
  CP7C (D14-9).

## Larangan (sama dengan putaran sebelumnya)

Tidak boleh dimutasi: main, deployment Cloudflare, Supabase hosted Enteng (`siimvrusnzxexizpyoib`), legacy
ERP-Garment (`vlxdhpkjeevubjxexnfo`, read-only), production. Mode Enteng diuji dengan build lokal + backend sekali pakai,
bukan ke hosted. Tidak meminta password, token atau kunci di chat. `production_go:false`.
