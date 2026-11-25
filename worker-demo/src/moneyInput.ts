export const cleanMoneyInput=(value:string)=>value.replace(/\D/g,'').replace(/^0+(?=\d)/,'')

export const formatMoneyInput=(value:string|number)=>{
  const digits=cleanMoneyInput(String(value))
  return digits.replace(/\B(?=(\d{3})+(?!\d))/g,'.')
}

export function readRupiahInput(value: string) {
  const text = value.trim()
  if (/^\d{1,3}(?:\.\d{3})+(?:,\d{1,6})?$/.test(text)) return Number(text.replaceAll('.', '').replace(',', '.'))
  return /^\d+(?:[.,]\d{1,6})?$/.test(text) ? Number(text.replace(',', '.')) : NaN
}
