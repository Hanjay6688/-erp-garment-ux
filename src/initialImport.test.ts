import { describe, expect, it } from 'vitest'
import { initialImportCatalog, initialImportTemplate, parseInitialImportCsv, MAX_IMPORT_ROWS, type InitialImportEntity } from './initialImport'

describe('file impor dari Excel', () => {
  it('preserves monetary decimal text, leading zeroes, quoted separators and multiline fields', () => {
    const rows = parseInitialImportCsv('\uFEFFKode pelanggan,Nama pelanggan,Alamat\r\n001,"Toko, Satu","Jalan A\r\nNomor ""7"""\r\n002,Toko Dua,Jalan B', 'CUSTOMER')
    expect(rows).toEqual([
      { source_row_no: 2, payload: { customer_code: '001', customer_name: 'Toko, Satu', address: 'Jalan A\r\nNomor "7"' } },
      { source_row_no: 4, payload: { customer_code: '002', customer_name: 'Toko Dua', address: 'Jalan B' } },
    ])
    expect(parseInitialImportCsv('Jenis saldo;Nominal;Kode total pembanding\nCASH_BANK;14.25;A', 'OPENING_BALANCE_ITEM')[0].payload.amount).toBe('14.25')
    expect(parseInitialImportCsv('Jenis saldo,Nominal,Kode total pembanding\nCASH_BANK,9007199254740993.01,A', 'OPENING_BALANCE_ITEM')[0].payload.amount).toBe('9007199254740993.01')
  })
  it.each(Object.keys(initialImportCatalog) as InitialImportEntity[])('exports every header for %s without losing fields', (entity) => {
    const fields = Object.keys(initialImportCatalog[entity].fields)
    const row = fields.map((_, i) => `"v${i}"`).join(',')
    expect(Object.keys(parseInitialImportCsv(initialImportTemplate(entity) + row, entity)[0].payload)).toEqual(fields)
  })
  it.each([
    'Kode pelanggan,Nama pelanggan\nA,"broken',
    'Kode pelanggan,Nama pelanggan\nA,"ok"surprise',
    'Kode pelanggan,Nama pelanggan\nA,un"quoted',
    'Kode pelanggan,Nama pelanggan\nA,Toko,extra',
    'Kode pelanggan,Nama pelanggan,customer_code\nA,Toko,A',
    'Kode pelanggan,Nama pelanggan,Kolom asing\nA,Toko,X',
    'Kode pelanggan\nA',
    'Kode pelanggan,Nama pelanggan\nA,\uFFFD',
  ])('rejects malformed or ambiguous input before upload: %s', (source) => {
    expect(() => parseInitialImportCsv(source, 'CUSTOMER')).toThrow()
  })
  it('handles empty lines and tab-separated Excel export with original row numbers', () => {
    expect(parseInitialImportCsv('\nsize_code\tsort_order\r\n\r\nM\t2\r\n', 'SIZE')).toEqual([{source_row_no: 4, payload: {size_code:'M',sort_order:'2'}}])
  })
  it('does not execute spreadsheet formula text', () => {
    expect(parseInitialImportCsv('Kode pelanggan,Nama pelanggan\n001,=1+1', 'CUSTOMER')[0].payload.customer_name).toBe('=1+1')
  })
  it('bounds rows without discarding overflow', () => {
    expect(() => parseInitialImportCsv('size_code\n' + 'M\n'.repeat(MAX_IMPORT_ROWS + 1), 'SIZE')).toThrow('Maksimal')
  })
})
