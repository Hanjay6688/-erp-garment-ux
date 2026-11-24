import { describe, expect, test } from 'vitest'
import { dozenPieces } from '../worker-demo/src/fgQuantity'
import { fgTotals } from '../worker-demo/src/demo/fgOverview'
import type { Product } from '../worker-demo/src/productCatalog'
const item = (grade:string,stocks:number[]):Product => ({ brand:'Vivo',code:'93001',range:'31–33',name:'Kulot Jumbo',color:'Biru',sizes:['31','32','33'],stocks,grade,location:'Utama' })
describe('kuantitas finished goods',()=>{
  test('jumlahkan seluruh potong, termasuk sisa lintas SKU dan ukuran',()=>{
    const rows=[item('Good',[5,2,1]),item('Good',[3,4,1]),item('BS',[2,3,1])]
    expect(fgTotals(rows)).toEqual({all:22,good:16,bs:6})
    expect(dozenPieces(fgTotals(rows).good)).toBe('1 lusin 4 potong')
    expect(dozenPieces(fgTotals(rows,['32','33']).all)).toBe('1 lusin 0 potong')
    expect(fgTotals([],['31']).all).toBe(0)
  })
  test('nol, sisa dan mutasi negatif memakai format yang sama',()=>{
    expect([0,1,11,12,13,25,-13].map(dozenPieces)).toEqual(['0 lusin 0 potong','0 lusin 1 potong','0 lusin 11 potong','1 lusin 0 potong','1 lusin 1 potong','2 lusin 1 potong','−1 lusin 1 potong'])
    expect(dozenPieces('12000000000000000005')).toBe('1.000.000.000.000.000.000 lusin 5 potong')
  })
})
