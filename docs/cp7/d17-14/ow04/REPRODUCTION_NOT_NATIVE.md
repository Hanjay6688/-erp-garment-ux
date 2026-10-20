# Reproduksi usulan OW04: tidak terpasang

Root mengarsipkan usulan kedua pemeriksa di bawah docs agar tidak hilang saat sesi terputus. Tidak ada file di sini diimpor oleh installer produk. Kedua SQL ledger-proposal sengaja berhenti dengan OW04_PROPOSAL_NOT_INSTALLABLE_WITHOUT_COMPLETE_FEATURE. Pure-kernel hanya aritmetika; tidak memberikan authority, sumber, akun atau tanggal buku.

Dari root repo, gunakan optional runtime PGlite sendiri:

```sh
OW04_PGLITE_MODULE=/absolute/path/to/pglite/dist/index.js node docs/cp7/d17-14/ow04/pure-kernel/oracle.mjs
OW04_PGLITE_MODULE=/absolute/path/to/pglite/dist/index.js node docs/cp7/d17-14/ow04/ordinal-sql-counter/check_expected.mjs
python docs/cp7/d17-14/ow04/ordinal-decimal-counter/ordinal_oracle.py
OW04_PGLITE_MODULE=/absolute/path/to/pglite/dist/index.js node docs/cp7/d17-14/ow04/ledger-proposal/check_helpers.mjs
python docs/cp7/d17-14/ow04/ledger-proposal/03_native_copy_transform.py --static-check .
```

Hasil root:57 kontrol pure kernel,8 fixture ordinal SQL,15 fixture ordinal Decimal/330 pemeriksaan,26 scalar/DDL/ancestry ledger dan3 transform sumber. Scope masing-masing tertulis di JSON. Bukan Native, validasi source collector, izin, post journal, concurrency atau keuangan produk. Hasil awal agen disimpan sebagai AGENT_ORIGINAL_* dan first-run logs; runner menulis RESULT baru pada reproduksi berikutnya. FIRST_* kegagalan pengembangan tetap dipertahankan. EXPECTED literal/hash tidak diubah.

Portabilitas root hanya mengganti lokasi optional runtime dan path sibling pure-kernel. FINAL_RECEIPT ledger mengunci file SQL/transform/README asli agen, bukan mengklaim driver portabel byte-identik. README usulan awal menyebut direktori eksternal ../kernel; di arsip ini padanannya ../pure-kernel. Ketidaklengkapan authority/collector/causal floor/ADJUSTMENT/closure dan integrasi pembaca/koreksi tetap blocker implementasi OW04.
