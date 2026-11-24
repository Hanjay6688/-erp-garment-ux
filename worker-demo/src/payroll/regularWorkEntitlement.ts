export type WorkComponentRate = {
  name: string
  rate: number
}

export type RegularWorkEntitlementInput = {
  sewnQty: number
  fullRate: number
  bsQty: number
  bsComponents: readonly WorkComponentRate[]
  stuckQty: number
  stuckComponents: readonly WorkComponentRate[]
}

const nonNegative = (value: number) => Number.isFinite(value) ? Math.max(0, value) : 0
const money = (value: number) => Math.round(value * 100) / 100
const totalComponentRate = (components: readonly WorkComponentRate[]) =>
  components.reduce((sum, component) => sum + nonNegative(component.rate), 0)

export function calculateRegularWorkEntitlement(input: RegularWorkEntitlementInput) {
  const sewnQty = nonNegative(input.sewnQty)
  const fullRate = nonNegative(input.fullRate)
  const bsQty = nonNegative(input.bsQty)
  const stuckQty = nonNegative(input.stuckQty)
  const bsComponentRate = totalComponentRate(input.bsComponents)
  const stuckComponentRate = totalComponentRate(input.stuckComponents)
  const gross = money(sewnQty * fullRate)
  const bsDeduction = money(bsQty * bsComponentRate)
  const stuckDeduction = money(stuckQty * stuckComponentRate)
  const totalDeduction = money(bsDeduction + stuckDeduction)

  return {
    sewnQty,
    fullRate,
    bsQty,
    stuckQty,
    bsComponentRate,
    stuckComponentRate,
    gross,
    bsDeduction,
    stuckDeduction,
    totalDeduction,
    subtotal: money(gross - totalDeduction),
  }
}
