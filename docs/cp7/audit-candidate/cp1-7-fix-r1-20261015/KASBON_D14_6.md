# Kasbon tunai (keputusan owner D14-6)

Keputusan owner (15 Okt 2026): "Ya, buatkan (Disarankan)". Ini juga jalan sah yang dimaksud D14-2: membayar sebelum
upah menjadi utang adalah kasbon, bukan pembayaran payroll.

## Alur

| Langkah | Apa yang terjadi | Jurnal |
|---|---|---|
| Beri kasbon (`GIVE`) | Nominal, tanggal (WIB, tidak di masa depan, tidak di periode tutup), rekening, alasan | Dr `CONTRACTOR_RECEIVABLE` (mandor) / Cr rekening, tanggal kasbon, lewat `erp.post_journal` Native. Bank tidak boleh minus pada tanggal itu atau sesudahnya (penjaga kas D14-3) |
| Potong dari payroll draf (`ALLOCATE`) | Sebagian/seluruh kasbon dipesan pada payroll draf mandor yang sama (0 = lepas). Dibatasi sisa kasbon dan pendapatan payroll | Belum ada jurnal. Baris potongan Native `CASH_ADVANCE` |
| Bayar payroll (perintah payroll biasa) | `post_payroll_payment` Native tanpa perubahan | Dr `CONTRACTOR_PAYABLE` / Cr `CONTRACTOR_RECEIVABLE` sebesar potongan; kas hanya gaji bersih |
| Batalkan kasbon (`CANCEL`) | Hanya bila tidak dipotong/dipesan di payroll yang masih hidup | `erp.reverse_journal` Native (kas kembali) |
| Payroll dibalik | Potongannya ikut mati; sisa kasbon kembali | Pembalik Native payroll |

## Delta Native yang dideklarasikan (dipulihkan persis saat uninstall)

1. Constraint `erp.payroll_deductions.payroll_cash_advance_source_check`: potongan `CASH_ADVANCE` boleh tanpa saldo awal;
   trigger tertunda `cp7_kasbon_deduction_linked` mewajibkan tautan kasbonnya. Pemulihan constraint asli gagal (memang harus)
   selama masih ada potongan kasbon.
2. `erp.guard_opening_cash_advance_deduction_v1()`: baris tanpa saldo awal diteruskan ke penjaga kasbon.
3. `erp.check_opening_cash_advance_payroll_v1(uuid)`: persetujuan/pembayaran payroll juga memeriksa potongan kasbon
   (tertaut, mandor sama, kasbon masih GIVEN, payroll tidak bertanggal sebelum kasbon, tidak melebihi kasbon).
4. `erp.run_v267_financial_truth_checks()` kode `AP_CASH_ADVANCE_SOURCE` (CRITICAL, DATABLE, memblok tutup buku):
   menerima potongan kasbon yang sah (`cp7_kasbon.linked_ok`).

Bentuk baris `erp.payroll_deductions` tidak berubah (tautan disimpan di `cp7_kasbon.deduction_links`), sehingga semua
pembaca yang memotret baris itu (makna payroll, cicilan) tetap sama. Penjaga privat: potongan kasbon hanya lewat
perintah kasbon (`CP7_KASBON_DEDUCTION_PRIVATE`), jurnal kasbon dan pembaliknya hanya lewat perintah kasbon
(`CP7_KASBON_JOURNAL_PRIVATE`). Pemeriksaan dampak ke cek Native lain: tidak ada daftar putih `source_type`, tidak ada
rekonsiliasi buku piutang mandor; `AP_CASH_ADVANCE_PAYROLL_JOURNAL`, `AP_CASH_ADVANCE_CAPACITY`, cek integritas kasbon
bahan, dan pembangun ulang draf payroll (hanya menghapus potongan bahan) cocok tanpa perubahan. Patch `run_v267`
mengubah hash yang dipin kapsul rollback CP6 20be; rollback CP6 menolak selama CP7 terpasang (diharapkan).

## Akses
OWNER/ADMIN + `finance.payroll.view`; menulis juga `finance.payroll.pay`. Idempoten per (aktor, request), token tinjauan
per mandor, kunci per mandor.

## Bukti
Kasus CP17: `CP17_KASBON_GIVE_DEDUCT_PAY`, `CP17_KASBON_LIMITS_REFUSED`, `CP17_KASBON_RELEASE_CANCEL_REPLAY`,
`CP17_HTTP_KASBON_GIVE`. Layar: `src/PayrollKasbonPanel.tsx` (+ uji DOM).

## Batas yang tersisa
- Navigasi sumber jurnal `CP7_KASBON` di buku besar menampilkan "sumber belum didukung" (tidak rusak).
- Urutan potong kasbon tunai vs kasbon bahan: kasbon tunai dipotong saat dipilih di draf; kasbon bahan dihitung dari
  sisa gaji saat draf dihitung ulang.
