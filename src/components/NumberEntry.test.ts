import { describe, expect, it } from 'vitest'
import { pastedPieceCounts } from './NumberEntry'

describe('paste pcs dari spreadsheet', () => {
  it('menerima titik ribuan dan mempertahankan posisi sel kosong', () => {
    expect(pastedPieceCounts('1.234\t\t80\n0\t2.000.000\t9')).toEqual([[1234, 0, 80], [0, 2000000, 9]])
  })

  it.each(['1,25', '1,234.56', '1.23', '-7', '25 pcs', '9007199254740992'])(
    'menolak seluruh tabel jika satu sel tidak sah (%s)', entry => {
      expect(pastedPieceCounts('10\t20\n30\t' + entry)).toBeNull()
    },
  )
})
