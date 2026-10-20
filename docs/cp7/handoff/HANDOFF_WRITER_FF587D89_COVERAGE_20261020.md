# Writer berlanjut: 86 PASS belum memenuhi seluruh OW-01

Cabang `astra/d17-14-20261020`, HEAD `ff587d89d110d871c084770629beb8f508503b55`, tree `96d2cbe0bd3c8591792fc1ee98bb924aa4b04e54`. Produk identik dengan `b7fc541c` / tree `f047ceb7`; commit ff587 hanya memperbaiki oracle dan menyimpan bukti. Kandidat audit `55c885d1` / tree `80622a93` tetap beku. Hosted Enteng, main, dan WA nyata tidak disentuh. `production_go:false`.

Owner mengizinkan enam helper untuk saling memeriksa. Root tetap satu-satunya integrator produk; tidak ada sub-turunan. Ini review internal writer, bukan audit eksternal. Jangan berhenti hanya karena catatan ini disimpan.

## Bukti baru

- WA run `39453357551`, job `118733713404`: **86/86 PASS**, source SHA `59eb4d1a3f898dc37fc63a677781043be3faf008c038dd61d6a49ce8beb1d0fe`, restore dan advisor gate true. Smoke job `118733712737` PASS. Seluruh ID lama dipertahankan.
- First result b7: 83 PASS / 3 INCOMPLETE, tetap tersimpan. Dua browser gagal pada asumsi raw string `186` padahal kontrak menerima `186.000000`. Nilai, raw equality dengan snapshot, UNKNOWN fisik, tampilan 186, unit, dan provider text tidak dilonggarkan.
- Oracle Native menghitung live `RESOLVED_NOW` sebagai aturan mati. Diagnostic baru benar-benar mengobservasi row DATA_REVIEW / missing BOM yang sudah ditutup FG/WIP; bukan dugaan BOM kosong. Exact tuple DONE/checked/open/off sekarang 3/1/1.
- E01 b7: 4/4 PASS, termasuk AR175 dan pemulihan database; source SHA `a7305cfc...`.
- P19 b7: K4 32, staged 15, report 20, plan 22 PASS; semuanya restore/advisor true. Tidak ada klaim workflow keseluruhan atau SLA. Transport job `118721611968` gagal sebelum tes karena port 54322 terpakai; first failure tersimpan dan belum dijalankan ulang.

Receipt terpisah ada di `docs/cp7/d17-14/ow01/`.

## OW-01 tetap terbuka: celah bukti per jenis

Root dan dua helper membaca cakupan sendiri sebelum bertukar hasil. Dari 16 jenis termasuk manual, receipt provider palsu yang benar-benar dikirim setelah commit baru eksplisit untuk FABRIC_BELOW_MINIMUM, ACCESSORY_NEED, dan MANUAL_REMINDER. Tiga belas jenis lain baru terbukti pada antrean, collector, atau browser pengaturan/formula.

Label historis `fake_message=true` di `cp7_wa_obligation_cases` tidak membuktikan HTTP. Beberapa closure juga mengubah bisnis lagi setelah assertion antrean dalam transaksi yang sama. Root memperjelas label keluaran menjadi bukti antrean dan `provider_delivery_proven_here:false`; assertion bisnis tidak diubah. Hasil lama tetap sah dalam cakupannya.

Expected tambahan: `ow01/PER_KIND_PROVIDER_EXPECTED.md`. Lead `ow01_race_counter` menyiapkan proposal di `/workspace/scratch/9442228ed2dc/ow01-proposals/all-kinds/`; helper UI menyiapkan fixture map independen dan dependencies ikut memeriksa. Root memasang proposal setelah review.

Target 99 = 55 Native / 30 races / 5 HTTP / 9 browser, dengan seluruh 86 ID lama. Tiap jenis memakai copy sekali pakai dan penulis sumber yang diterima. Bekukan sumber dan detail; send; periksa sumber sebelum commit; commit tanpa mutasi bisnis susulan; jalankan real pg_net worker ke fake CallMeBot; cocokkan nomor, key_ok, body, HTTP200 dan ACCEPTED; tick ulang tidak boleh menggandakan dispatch atau receipt. Pulihkan worker dan periksa cleanup. Tidak memakai provider answer, render, atau row bisnis sintetis untuk menutup kriteria ini.

FABRIC_NEED positif memakai `physical.bound`, staged analysis dan policy publik dengan sumber 176 ASSUMED yang sudah dipakai suite reminder. Jangan menulis angka 176 ke sumber atau menjalankan `receipt_of` setelah snapshot sebelum kirim. Actor analisis dan policy harus sama dengan actor WA.

## OW-04: usulan belum dipasang

Enam helper mengerjakan collector/member facts, ordinal kernel, current reader/materialization, typed request/admission, fixture Native, serta UI wire. Lokasi kerja: `/workspace/scratch/9442228ed2dc/ow04-proposals/`. Root telah mengulang ordinal 41 executable + 1 external control, capability reader 12 synthetic, UI 40 synthetic dan strict TypeScript. Hasil itu bukan Native posting, otoritas, atau feature completion.

Counter independen membongkar tujuh acceptance holes dalam collector awal: inverse hilang, AR1100 untuk dokumen1000, tanggal sumber berubah, serta registration salah root/jurnal. First counters dan perbaikannya tersimpan. Member verifier STABLE kini mengikat assignment NEW_POST, root, item/replay lineage, actual original journal atau NO_JOURNAL. Protected registration writer dan qualification legacy BASE masih diperlukan; jangan mengarang urutan retur lama.

Materialized reader harus menghitung semua signed I yang benar-benar memiliki part/jurnal, termasuk adjustment. Planned I tidak boleh dianggap actual. Data-complete marker dapat dibaca sebelum outer response dan bukan bukti otoritas. Final deferred closure tetap harus membuktikan provenance operasi, receipt, header/status dan tidak ada scope tersisa; hak aktif diperiksa owning command sebelum receipt, bukan JWT di COMMIT. Sepuluh private inverse copies harus memakai komposisi guard yang sama. Collector BASE belum menggantikan incoming U atau profil kredit lengkap.

### Bantahan tanggal yang belum boleh diabaikan

Aturan universal causal floor NOT NULL ternyata terlalu ketat. Public AX menerima owner_unit_value0 dengan alasan; latest BD dapat mem-post free SALE/HPP0 tanpa jurnal; AH dapat mem-post free RETURN/HPP0 tanpa jurnal. Native peer juga menelusuri genuine OPENING0 → free SALE → accepted recost10 → return0: jurnal RETURN HPP-only DrFG10/CrCOGS10 muncul, sementara SALE journal sebelumnya tetap absen. FG/COGS 50/50 menjadi 60/40.

Karena itu `PROVEN_ABSENT` harus membuktikan ketiadaan **prior causal SALE/RETURN book floor**, bukan membuat tanggal atau selalu mensyaratkan projected RETURN NO_JOURNAL. Jika ada ancestor journal, floor wajib dibuktikan. Jika benar-benar absen, Native HPP-only poster memakai lawful resolver miliknya dengan proof yang lengkap dan tanpa credit component. UI 40/40 masih mempunyai universal READY-floor yang diketahui belum mencakup kasus ini; jangan integrasikan asersi itu tanpa exception bertipe dan counter positifnya.

Timing juga penting: AH sudah mengubah return menjadi POSTED di317, sebelum journal di414. Paired poster di tengah proses tidak boleh memanggil completed `return_fact` yang mengharapkan jurnal HPP sudah ada. Seal **prior** causal proof di `native_return_enter` saat own row masih DRAFT, dari SALE dan bound existing ancestors. Exclusion hanya untuk own sealed projection; bukan daftar bebas dari caller. Completed fact helper baru dipanggil setelah actual journal atau NO_JOURNAL yang terbukti. Projection SHA berbeda dari actual manifest dan projection-to-actual proof SHA.

Recost10→0 memberi counter lain: original sale allocation dapat tetap HPP10, sedangkan return baru memakai current HPP0 dan tidak membuat jurnal. Jangan mensyaratkan original allocation HPP0 untuk RETURN NO_JOURNAL. Tetap buktikan exact lineage/qty, frozen RETURN item/movement0, dan actual journal absence. SALE absence memiliki pembuktiannya sendiri.

### Besaran dan Kas & Bank

Supplied-vector counter root menghasilkan +M, +M, −2M dengan current K0; M=999999999999999999.99. Satu journal numeric(20,2) tidak muat 2M, tetapi part [−M,−M] tepat. Kedua positive-pair future capacities nol: atom positif bukan kredit yang boleh direfund. Ini aritmetika murni, bukan bukti Native inverse-date authority. Jangan menambah aggregate cap atau membulatkan melalui Number.

Query Kas & Bank sudah membaca jurnal new source dan menampilkan kedua tanggal. Resolver navigasinya belum mengenali refund source baru; perlu owning adapter dengan hak akses, bukan fake expense atau BB batch. Native cash credit-line trigger memeriksa minima ekonomi dan buku secara terpisah di bawah CP7_CASH|COA. Original payment facts dan journal harus tetap identik.

## Langkah kerja

1. Integrasikan dan qualify 13 provider receipts; simpan first result jika gagal. Pertahankan semua 86 kasus serta oracle angka, sumber, UNKNOWN, privasi dan akses.
2. Simpan proposal/counter yang mahal direproduksi sebagai paket inert di repo, dengan hash dan instruksi portabel. Jangan memasang modul setengah jadi. Codec Native fact SHA tetap raw; proof SHA canonical adalah protokol terpisah.
3. Teruskan integrasi atomik OW-04 beserta Native/HTTP/browser/race/fault/restore dan pengukuran yang relevan. OW-05 sampai OW-16 serta OW-15 tetap mengikuti register; jangan ditutup dengan jumlah PASS internal.
4. Bukti skala lama 5000 target 79–105 detik dan finance DEFERRED bukan SLA atau hasil baru. Tidak ada feature_complete, audit_complete atau production_go dari checkpoint ini.

## Integrasi tambahan setelah handoff awal

Root telah mengintegrasikan13 kasus transport pada scripts/cp7_wa_all_kinds_transport_cases.py (SHA29b45d3ca5c4dba23ba0a931e26bcdde1ce6964467eee5e921df941bbe7fd945). Count99=55/30/5/9 dan seluruh86 ID lama tetap persis; import dan registration tanpa koneksi lulus. Expected, first static counters, source review dan hasil lokal ada di ow01/all-kinds. Ini belum hasil Native baru; kandidat berikut harus dipantau sampai actual provider receipts13jenis dan restore gate terbukti. Product src/SQL/bundle tetap identik dengan b7fc541c.
