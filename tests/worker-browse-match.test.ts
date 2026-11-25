import { describe, expect, it } from 'vitest'
import { browseMatchPieces } from '../worker-demo/src/browseMatch'

describe('pencarian jumlah pcs', () => {
  it('mencocokkan jumlah dan identitas dokumen dalam kueri yang sama', () => {
    expect(browseMatchPieces('114', [114], 'Zodiak Jumbo')).toBe(true)
    expect(browseMatchPieces('zodiak 114 PCS', [114], 'Zodiak Jumbo')).toBe(true)
    expect(browseMatchPieces('1.480potong Mandor Afui', [1480], 'Mandor Afui')).toBe(true)
    expect(browseMatchPieces('44 pcs', [244], 'Batch 44')).toBe(false)
    expect(browseMatchPieces('44', [244], 'Batch 44')).toBe(true)
    expect(browseMatchPieces('NAA261123006', [20], 'NAA-261123-006')).toBe(true)
  })

  it('memakai tanda ketika dicantumkan dan nilai absolut jika kueri tanpa tanda', () => {
    expect(browseMatchPieces('−1.200 pcs', [-1200], 'Keluar gudang')).toBe(true)
    expect(browseMatchPieces('1.200 pcs', [-1200], 'Keluar gudang')).toBe(true)
    expect(browseMatchPieces('+1.200 pcs', [-1200], 'Keluar gudang')).toBe(false)
    expect(browseMatchPieces('-1.200 pcs', [1200], 'Masuk gudang')).toBe(false)
    expect(browseMatchPieces('114 pcs', [], '114 meter')).toBe(false)
  })
})
