import { describe, expect, it } from 'vitest'
import { emptySkuSettings, skuGroupChanges, type SkuGroup } from './skuMaster'
import { parseSkuHpp, skuMoney } from './skuHpp'
const group = (id: string, sizes: string[]): SkuGroup => ({ id, sku: id, revision: '1', brand_id: 'brand', brand_name: 'Vivo', model_id: 'model', model_name: 'Classic', color_name: 'Blue', effective_from: '2026-09-28T00:00:00Z', members: sizes.map(s => ({ id: s, size_id: s, size: s })), settings: emptySkuSettings() })
describe('commercial SKU joins preserve physical identities', () => {
  it('moves size34 atomically and retains35/36 plus their original rates', () => {
    const source = group('34-36', ['34','35','36']); source.settings!.price = '195000'
    const target = group('31-33', ['31','32','33','34'])
    const changes = skuGroupChanges(target, [source], ['31','32','33','34','35','36'].map(product_root => ({ product_root })))
    expect(changes.map(g => g.members)).toEqual([['31','32','33','34'],['35','36']])
    expect(changes[1].settings.price).toBe('195000')
    expect(source.members.map(m => m.id)).toEqual(['34','35','36'])
    expect(changes.map(g => g.legacy_basis.length)).toEqual([4,2])
  })
  it('refuses incomplete conflict review and hidden source economics', () => {
    expect(() => skuGroupChanges(group('27',['27']), [], [])).toThrow('belum seluruhnya')
    const source = group('old',['27']); source.settings = null
    expect(() => skuGroupChanges(group('new',['27']), [source], [{ product_root: '27' }])).toThrow('Hak baca')
  })
  it('formats large money exactly and handles rounding carry without float conversion', () => {
    expect(skuMoney('9007199254740993.995')).toBe('Rp9.007.199.254.740.994,00')
    expect(skuMoney(null)).toBe('Belum tersedia')
  })
  it('refuses HPP with missing physical size or duplicate lot', () => {
    const lot = { lot_id:'lot', lot_number:'L1', product_id:'p', size:'27', location_id:'g', grade:'GOOD', qty:'12', value:'120', provisional:false }
    const g = { group_key:'sku', sku:'32007-27', brand_name:'Vivo', qty:'12', value:'120', hpp_per_pcs:'10', provisional:false, lots:[lot] }
    const w = { at:'2026-09-28T00:00:00Z', page:1, page_size:50, total:1, groups:[g] }
    expect(parseSkuHpp(w).groups[0].qty).toBe('12')
    expect(() => parseSkuHpp({ ...w, groups:[{ ...g, qty:'13' }] })).toThrow('Total stok')
    expect(() => parseSkuHpp({ ...w, groups:[{ ...g, lots:[lot,lot] }] })).toThrow('Rincian stok')
  })
})
