export const cleanMoneyInput=(value:string)=>value.replace(/\D/g,'').replace(/^0+(?=\d)/,'')

export const formatMoneyInput=(value:string|number)=>{
  const digits=cleanMoneyInput(String(value))
  return digits.replace(/\B(?=(\d{3})+(?!\d))/g,'.')
}
