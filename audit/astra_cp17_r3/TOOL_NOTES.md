# Catatan identitas dan alat

- Produk dipasang dari checkout `b53b5acdf260b03ebac3474e9ae837fcef6f6eb1`, tree `32f54240a60e01ab8b1ffad7267d285a669be520`; run head pada GitHub adalah commit workflow auditor, dicatat terpisah pada RUN_REGISTER.
- Bundle gabungan yang benar-benar diuji mencetak SHA-256 `8312f615682d42209e38288585e367a4f5f46aeff71e13238e23dfecb794afd0` pada probe Astra; deklarasi dan exact-definition verification memasang sumber beku kandidat. Metadata `product_ref` lama di runner T3 merupakan referensi baseline harness, bukan pin checkout aplikasi. Identity gate eksplisit dan pemeriksaan source setelah run adalah bukti kandidatnya.
- Job risiko mewarisi nama “Astra 11 independent Native oracles”, tetapi RISK_MANIFEST dan runtime secara eksplisit berisi empat kasus: dua Native dan dua HTTP. Itu tidak dihitung sebelas.
- Artefak pagination mewarisi nama suffix `risk`. Identitas yang dipakai adalah run39053620397/artifact12108448537 dan isi `ASTRA_R3_AUDIT_PAGING.json`; berbeda dari run39053360685/artifact12109155266 yang berisi empat kasus risiko.
- Wrapper risiko/pagination memberi summary INCOMPLETE ketika ada COUNTEREXAMPLE, sementara seluruh kasus teramati dan error=null. Laporan mempertahankan status per kasus dan tidak menganggap summary tersebut sebagai error alat yang mengizinkan rerun.
- Tidak ada perubahan source probe atau expected setelah kasus mulai. R2 FG v2 merupakan oracle yang sudah dikualifikasi dan dikunci sebelum r3; empat file retained sekarang identik byte dengan lock r2.
- Uji browser Enteng menjawab host proyek menggunakan Auth/PostgREST sekali pakai. Loopback host mapping dan pembatas permintaan ada pada workflow/harness; tidak ada pemanggilan database hosted.
- Manifest dan arsip dibuat dari log asli. Perbaikan lokal pada skrip perakit evidence hanya menyelesaikan kunci metadata Python yang duplikat; tidak mengubah hasil runtime, source uji, ID kasus, expected, atau log mentah.
