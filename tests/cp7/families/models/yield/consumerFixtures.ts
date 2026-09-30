import { guardYieldReview, yieldInputKey, type YieldContext, type YieldInput, type YieldReview } from '../../../../../scripts/cp7-src/models/cuttingYieldContract'

export const mixes = {
  small: ['28', '28', '29', '29', '30', '30'],
  unique: ['28', '29', '29', '29', '30', '30'],
  jumbo: ['31', '31', '32', '32', '33', '33'],
  all30: ['30', '30', '30', '30', '30', '30'],
} as const
export type MixChoice = keyof typeof mixes
export type YieldExample = 'NORMAL' | 'LOW' | 'HIGH' | 'SHORT_ROLL' | 'NARROW_BATCH' | 'INSUFFICIENT' | 'INCOMPLETE' | 'UNSEEN_COMBINATION' | 'ERROR'
// These are supplied UI cases, not trained predictions, expert benchmarks,
// observed factory records, or fitted/calibrated intervals.
const cases = {
  small: { lower: '90', upper: '110', actual: { NORMAL: '100', LOW: '70', HIGH: '125' } },
  unique: { lower: '84', upper: '104', actual: { NORMAL: '94', LOW: '65', HIGH: '115' } },
  jumbo: { lower: '70', upper: '90', actual: { NORMAL: '80', LOW: '55', HIGH: '105' } },
} as const
const withoutWidth = { small: { lower: '80', upper: '120' }, unique: { lower: '74', upper: '114' }, jumbo: { lower: '60', upper: '100' } } as const
export function yieldFixtureInput(mix: MixChoice, example: YieldExample, widthCm: string | null = null): YieldInput {
  const supplied = mix === 'all30' ? null : cases[mix]
  const actual = example === 'SHORT_ROLL' ? '80' : example === 'NARROW_BATCH' ? '94' : supplied && example in supplied.actual ? supplied.actual[example as 'NORMAL' | 'LOW' | 'HIGH'] : '100'
  return { rollId: 'fixture-yield-current-roll', rollRevision: 'fixture-r1', materialId: 'fixture-fabric-A',
    patternId: 'fixture-pattern-A', patternRevision: 'fixture-pattern-r1', consumed: { value: example === 'SHORT_ROLL' ? '80' : '100', unit: 'M' },
    usableWidthCm: widthCm, markerRevision: `fixture-layout-${mix}-r1`,
    sizeSlots: mixes[mix], observedCutPcs: example === 'INCOMPLETE' ? null : actual,
    outputComplete: example !== 'INCOMPLETE',
    materialFamily: { brandId: 'fixture-brand-A', millId: 'fixture-mill-A', behaviourBasis: 'FIXTURE_MATERIAL_HISTORY_NOT_VERIFIED' },
    measurements: { issuedDeclaredM: '100', issuedMeasuredM: example === 'INCOMPLETE' ? null : example === 'SHORT_ROLL' ? '80' : '100',
      remainingMeasuredM: example === 'INCOMPLETE' ? null : '0', familyWidthCm: '150', evidence: example === 'INCOMPLETE' ? 'UNVERIFIED' : 'FIXTURE_ONLY',
      refs: example === 'INCOMPLETE' ? [] : ['fixture-independent-length-measurement@r1', 'fixture-batch-width-measurement@r1', 'fixture-remnant-measurement@r1'] } }
}
export async function readYieldFixture(input: YieldInput, context: YieldContext, mix: MixChoice, example: YieldExample): Promise<YieldReview> {
  const base = { contract: 'f04.cutting-yield-preview.v1' as const, fixtureKind: 'SYNTHETIC_ONLY' as const,
    inputKey: yieldInputKey(input), context: { ...context }, modelVersion: 'fixture-supplied-range-not-trained', policyVersion: 'fixture-display-v1' }
  const messages = {
    INSUFFICIENT: 'Riwayat sebanding belum cukup atau validasi model belum lolos. Umur data satu tahun bukan syarat otomatis siap.',
    INCOMPLETE: 'Hasil potong final belum lengkap. Isian jumlah kosong tidak dianggap nol PCS. Lebar tetap opsional.',
    UNSEEN_COMBINATION: 'Kombinasi ukuran ini belum memiliki pembanding yang layak. Rentang campuran lain tidak dipinjam diam-diam.',
    ERROR: 'Contoh pembacaan analyzer gagal. Tidak ada rentang pengganti otomatis.',
  }
  if (example in messages) return { ...base, status: example as keyof typeof messages, reason: messages[example as keyof typeof messages] }
  if (mix === 'all30' || ((example === 'SHORT_ROLL' || example === 'NARROW_BATCH') && mix !== 'small')) return { ...base, status: 'UNSEEN_COMBINATION', reason: 'Contoh ini belum menyediakan pembanding untuk campuran dan kondisi terukur tersebut. Ukuran 30 semua tidak memakai range campuran 28/29/30.' }
  if (input.usableWidthCm !== null && input.usableWidthCm !== '150' && input.usableWidthCm !== '140') return { ...base, status: 'UNSEEN_COMBINATION', reason: 'Lebar ini belum tersedia dalam fixture tampilan. Model dari riwayat ERP belum disambungkan; tidak ada rentang rekaan.' }
  if (input.usableWidthCm === '140' && mix !== 'small') return { ...base, status: 'UNSEEN_COMBINATION', reason: 'Fixture belum menyediakan kombinasi ini pada lebar 140 cm. Tidak memakai rentang lebar lain.' }
  const noWidth = input.usableWidthCm === null
  const bounds = example === 'SHORT_ROLL' ? noWidth ? { lower: '64', upper: '96' } : { lower: '72', upper: '88' }
    : noWidth ? withoutWidth[mix] : input.usableWidthCm === '140' && mix === 'small' ? { lower: '84', upper: '104' } : cases[mix]
  const ready: YieldReview = { ...base, status: 'READY', assessment: example === 'SHORT_ROLL' || example === 'NARROW_BATCH' ? 'NORMAL' : example as 'NORMAL' | 'LOW' | 'HIGH',
    interval: { lower: bounds.lower, upper: bounds.upper, unit: 'PCS', kind: 'EMPIRICAL_REFERENCE', basis: noWidth ? 'WITHOUT_WIDTH' : 'WITH_RECORDED_WIDTH', qualification: 'FIXTURE_ONLY_NOT_CALIBRATED' },
    peers: Array.from({ length: 24 }, (_, index) => ({ rollId: `fixture-${mix}-peer-${index + 1}`, sourceRevision: 'fixture-r1' })),
    periodStart: '2026-03-01', periodEnd: '2026-09-01',
    reasons: [noWidth ? 'Pembanding contoh memakai bahan, revisi pola, panjang terpakai, marker dan frekuensi ukuran. Lebar tidak diisi; variasi batch belum dipisahkan.' : 'Pembanding contoh memakai bahan, revisi pola, lebar yang dicatat, panjang terpakai, marker dan frekuensi ukuran yang sama.',
      'Range dan jumlah pembanding adalah fixture tampilan; belum dihitung dari transaksi ERP atau divalidasi pada hasil baru.'],
    findings: example === 'SHORT_ROLL' ? ['Ada selisih panjang pada bukti ukur contoh: tercatat 100 M, tersedia fisik 80 M. Hasil dibandingkan dengan 80 M, bukan 100 M. Penyebab selisih panjang belum diketahui.']
      : noWidth ? ['Lebar belum tercatat. Hasil dibandingkan dengan kebiasaan bahan dan campuran yang diketahui; lebar, panjang sebenarnya dan penyebab selisih belum bisa dipastikan.']
      : example === 'NARROW_BATCH' && input.usableWidthCm === '140' ? ['Lebar batch yang diisi 140 cm; keluarga bahan pada contoh 150 cm. Rentang memakai lebar yang diisi, bukan label bahan. Ini pembeda input, belum bukti penyebab tunggal.']
      : example === 'LOW' ? ['Hasil tetap di bawah range untuk panjang tercatat dan lebar yang diisi. Dimensi yang ditulis belum membuktikan dimensi sebenarnya atau penyebab selisih.']
      : ['Status hasil sesuai rentang yang disediakan. Tidak menjadi bukti bahwa dimensi yang dicatat pasti benar.'],
    checks: ['Cocokkan meter terpakai dan sisa dengan pengukuran fisik; sisa hitungan saja belum bukti.',
      'Periksa cacat kain, scrap potong, recut, lebar efektif, marker dan salah pencatatan jumlah.',
      'Selisih belum menjelaskan penyebab. Kehilangan bahan perlu bukti rekonsiliasi dan pemeriksaan lapangan.',
      'Hasil yang lebih tinggi juga perlu dicek: ukuran, kelengkapan komponen, kualitas dan input meter.'] }
  return guardYieldReview(ready, input, context)
}
