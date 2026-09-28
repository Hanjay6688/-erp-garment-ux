// Expert references inform candidate methods, not factory facts or enabled policy.
export const benchmarks = [
  {
    title: 'Mulai dari metode ramalan sederhana',
    proposal: 'Rata-rata dan nilai terakhir menjadi pembanding. Metode baru dipakai hanya setelah evaluasi menunjukkan perbaikan.',
    limit: 'Belum ada model yang dipilih untuk usaha ini; histori penjualan yang sah tetap diperlukan.',
    source: 'Hyndman & Athanasopoulos · FPP3 §5.2',
    url: 'https://otexts.com/fpp3/simple-methods.html',
  },
  {
    title: 'Uji ramalan sesuai urutan waktu',
    proposal: 'Gunakan evaluasi bergulir dengan horizon yang sesuai keputusan produksi. Data masa depan tidak masuk pelatihan masa lalu.',
    limit: 'Jumlah histori dan fold mengikuti data yang tersedia; tidak mengaktifkan model dari contoh saja.',
    source: 'Hyndman & Athanasopoulos · FPP3 §5.10',
    url: 'https://otexts.com/fpp3/tscv.html',
  },
  {
    title: 'Bandingkan target layanan sebagai skenario',
    proposal: '90%, 95%, dan 99% dapat menjadi skenario pembanding cycle service level, seperti variasi pada latihan MIT.',
    limit: 'Ini peluang tanpa kehabisan dalam satu siklus, bukan persentase unit terpenuhi. Tidak ada target yang aktif; bukan standar wajib garment.',
    source: 'Chris Caplice · MIT ESD.260, kuliah 11, slide 13/18/20',
    url: 'https://ocw.mit.edu/courses/esd-260j-logistics-systems-fall-2006/resources/lect11/',
  },
  {
    title: 'Safety stock mengikuti risiko dan lead time',
    proposal: 'Pertimbangkan ramalan, kesalahan ramalan, waktu pengadaan/produksi dan target layanan. Pisahkan buffer hari dan metode statistik.',
    limit: 'Angka lead time, kapasitas dan target layanan belum diisi. Kontrak kalender dan kapasitas CP7 tetap harus diperiksa.',
    source: 'SAP · Extended Safety Stock Planning',
    url: 'https://help.sap.com/saphelp_snc70/helpdata/en/62/96cb530898214be10000000a174cb4/content.htm',
  },
  {
    title: 'SKU jarang laku perlu penilaian tersendiri',
    proposal: 'Metode untuk permintaan berselang menjadi kandidat evaluasi. Hasil Croston biasa tidak otomatis menyediakan interval prediksi.',
    limit: 'Jangan mengarang confidence atau menyamakan stok kosong dengan permintaan nol.',
    source: 'Hyndman & Athanasopoulos · FPP3 §13.2',
    url: 'https://otexts.com/fpp3/counts.html',
  },
  {
    title: 'Status WA harus mengikuti bukti pengiriman',
    proposal: 'Pisahkan antre, terkirim ke kanal, diterima dan dibaca; status berubah melalui bukti provider.',
    limit: 'Twilio hanya referensi pembanding. Provider, penerima, jadwal dan biaya belum dipilih.',
    source: 'Twilio · Track outbound message status',
    url: 'https://www.twilio.com/docs/messaging/guides/track-outbound-message-status',
  },
] as const
