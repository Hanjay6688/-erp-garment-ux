// @vitest-environment jsdom

import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import FinancePages, { type FinanceView } from './FinancePages'
import { payables, payrollNotes } from './financeData'

let container: HTMLDivElement
let root: Root
beforeEach(() => {
  ;(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true
  container = document.createElement('div'); document.body.appendChild(container); root = createRoot(container)
})
afterEach(() => { act(() => root.unmount()); container.remove() })
const render = (view: FinanceView) => act(async () => { root.render(<FinancePages view={view} onNavigate={vi.fn()} onSalesPayment={vi.fn()} onAttendance={vi.fn()} />) })
const text = () => container.textContent!.replace(/\s+/g, ' ')
// Report rows render "Rp 406.100.000"; negative rows add a leading minus that is not part of the value.
const rows = () => Object.fromEntries([...container.querySelectorAll('.biz-report-rows article')].map(a => [
  a.querySelector('span')!.firstChild!.textContent!.trim(), Number(a.querySelector('strong')!.textContent!.replace(/\D/g, '')),
]))
const open = (amount: number, paid: number) => Math.max(0, amount - paid)

describe('finance demo uses one set of August operands', () => {
  it('shows gross profit as net sales minus COGS on the card, chart and footer', async () => {
    await render('finance-overview')
    expect(text()).toContain('LABA KOTOR AGURp133,2 jt32,8% dari penjualan bersih · provisional')
    expect(text()).toContain('Laba kotor Agustus Rp133,2 jt (penjualan bersih − HPP)')
    expect(text()).not.toContain('Rp141 jt'); expect(text()).not.toContain('34,1%')
    const august = [...container.querySelectorAll('.biz-chart article')].find(a => a.querySelector('span')?.textContent === 'Agu')!
    expect(parseFloat((august.querySelector('i.sales') as HTMLElement).style.height)).toBeCloseTo(406.1 / 4.6, 6)
    expect(parseFloat((august.querySelector('i.hpp') as HTMLElement).style.height)).toBeCloseTo(272.9 / 4.6, 6)
    expect(text()).toContain('Penjualan neto')
  })
  it('counts open GRNI from the payable records the AP workspace shows', async () => {
    await render('finance-overview')
    const grni = payables.filter(p => p.kind === 'MATERIAL_GRNI' && open(p.amount, p.paid) > 0)
    const total = grni.reduce((sum, p) => sum + open(p.amount, p.paid), 0)
    expect(grni.length).toBeGreaterThan(0)
    expect(text()).toContain(`${grni.length} GRNI belum menjadi invoice final`)
    expect(text()).toContain(`Rp${(total / 1_000_000).toLocaleString('id-ID', { maximumFractionDigits: 1 })} jt masih memakai benchmark / estimate`)
  })
  it('reconciles Laba Rugi and Posisi Keuangan with the same operands', async () => {
    await render('finance-reports')
    const pl = rows()
    expect(pl['Penjualan bersih']).toBe(406_100_000)
    expect(pl['Penjualan bersih']).toBe(pl['Penjualan bruto'] - pl['Retur & potongan penjualan'])
    expect(pl['Total HPP']).toBe(272_900_000)
    expect(pl['Total HPP']).toBe(pl['HPP bahan & aksesori'] + pl['HPP tenaga kerja & komisi'] + pl['HPP laundry, rework & konversi'])
    expect(pl['Laba kotor']).toBe(133_200_000)
    expect(pl['Laba kotor']).toBe(pl['Penjualan bersih'] - pl['Total HPP'])
    expect((pl['Laba kotor'] / pl['Penjualan bersih'] * 100).toFixed(1)).toBe('32.8')
    await act(async () => { [...container.querySelectorAll('button')].find(b => b.textContent === 'Posisi Keuangan')!.click() })
    const pos = rows()
    const supplier = payables.filter(p => p.kind !== 'MATERIAL_GRNI').reduce((s, p) => s + open(p.amount, p.paid), 0)
    const grni = payables.filter(p => p.kind === 'MATERIAL_GRNI').reduce((s, p) => s + open(p.amount, p.paid), 0)
    const payroll = payrollNotes.filter(n => !['PAID', 'REVERSED'].includes(n.status)).reduce((s, n) => s + n.netPayable, 0)
    expect([pos['Hutang supplier & vendor'], pos['GRNI sementara'], pos['Payroll payable']]).toEqual([supplier, grni, payroll])
    expect(pos['Total liabilitas']).toBe(supplier + grni + payroll)
    expect(pos['Laba periode berjalan']).toBe(pl['Laba bersih sebelum pajak'])
    expect(pos['Total liabilitas'] + pos['Modal & laba ditahan'] + pos['Laba periode berjalan']).toBe(pos['Total aset'])
    expect(pos['Total liabilitas & ekuitas']).toBe(pos['Total aset'])
  })
})
