import { describe, expect, it } from 'vitest'
import {
  batchesWithSplits, batchLabel, initialCompleted, nextSplitSuffix, sizeTotal,
  splitCompletedBounds, validateWipSplit, wipSplitBlock,
} from './wipSplit'
import type { WipSplitPiece } from './wipSplit'

const seeds = [
  { id:'042-01', number:1, sizes:[229,0,0] as [number,number,number], note:'Navy' },
  { id:'042-02', number:2, sizes:[0,225,0] as [number,number,number], note:'Maroon' },
]
const piece = (over: Partial<WipSplitPiece>): WipSplitPiece => ({
  id:'042-02B', parentId:'POT-260827-042', rootId:'042-02', sourceId:'042-02', number:2, suffix:'B',
  sizes:[0,25,0], completed:25, note:'Hitam · BS bahan', reason:'BS bahan', at:'baru saja', ...over,
})

describe('WIP split rules', () => {
  it('conserves every size and the sewn total across a split', () => {
    const pieces = [piece({})]
    const view = batchesWithSplits('POT-260827-042', seeds, pieces)
    expect(view.map((batch) => [batch.id, batchLabel(batch.number, batch.suffix), batch.sizes])).toEqual([
      ['042-01', '01', [229,0,0]],
      ['042-02', '02A', [0,200,0]],
      ['042-02B', '02B', [0,25,0]],
    ])
    expect(sizeTotal(view.flatMap((batch) => batch.sizes))).toBe(229 + 225)
    expect(initialCompleted('042-02', 225, pieces) + initialCompleted('042-02B', 25, pieces)).toBe(225)
  })

  it('lists nested pieces after their source and keeps letters unique per root batch', () => {
    const first = piece({})
    const nested = piece({ id:'042-02C', sourceId:'042-02B', suffix:'C', sizes:[0,5,0], completed:5, note:'Putih' })
    expect(nextSplitSuffix('042-02', [first])).toBe('C')
    expect(nextSplitSuffix('042-01', [first])).toBe('B')
    const view = batchesWithSplits('POT-260827-042', seeds, [first, nested])
    expect(view.map((batch) => `${batch.id}:${batch.sizes[1]}`)).toEqual(['042-01:0', '042-02:200', '042-02B:20', '042-02C:5'])
    expect(view.find((batch) => batch.id === '042-02B')?.hasPieces).toBe(true)
    expect(initialCompleted('042-02B', 25, [first, nested])).toBe(20)
  })

  it('bounds the sewn pcs that move so neither side has more sewn than pieces', () => {
    // 225 pcs, 188 sewn, moving 50 → at least 13 sewn must move (only 175 stay), at most 50.
    expect(splitCompletedBounds(225, 188, 50)).toEqual({ min:13, max:50 })
    expect(splitCompletedBounds(225, 0, 50)).toEqual({ min:0, max:0 })
  })

  it('rejects splits that empty the source, exceed a size, or lack notes', () => {
    const base = { sourceSizes:[0,225,0] as [number,number,number], sourceCompleted:225, moveSizes:[0,25,0] as [number,number,number], completedMoved:25, newNote:'Hitam', sourceNote:'Putih', reason:'BS bahan' }
    expect(validateWipSplit(base)).toEqual([])
    expect(validateWipSplit({ ...base, moveSizes:[0,225,0], completedMoved:225 })).toContain('SOURCE_EMPTY')
    expect(validateWipSplit({ ...base, moveSizes:[1,25,0], completedMoved:26 })).toContain('SIZE_OVER_SOURCE')
    expect(validateWipSplit({ ...base, moveSizes:[0,0,0], completedMoved:0 })).toContain('NOTHING_MOVED')
    expect(validateWipSplit({ ...base, completedMoved:24 })).toContain('COMPLETED_OUT_OF_RANGE')
    expect(validateWipSplit({ ...base, newNote:' ' })).toContain('NEW_NOTE_REQUIRED')
    expect(validateWipSplit({ ...base, reason:'ok' })).toContain('REASON_REQUIRED')
  })

  it('blocks splitting once laundry or Final SKU owns the pcs', () => {
    const free = { qty:225, laundryOutside:0, laundryReturned:0, laundryDraft:false, finalSkuComplete:false }
    expect(wipSplitBlock(free)).toBeNull()
    expect(wipSplitBlock({ ...free, laundryDraft:true })).toBe('LAUNDRY_DRAFT')
    expect(wipSplitBlock({ ...free, laundryOutside:64 })).toBe('LAUNDRY_SENT')
    expect(wipSplitBlock({ ...free, laundryReturned:180 })).toBe('LAUNDRY_RETURNED')
    expect(wipSplitBlock({ ...free, finalSkuComplete:true })).toBe('FINAL_SKU')
    expect(wipSplitBlock({ ...free, qty:1 })).toBe('TOO_SMALL')
  })
})
