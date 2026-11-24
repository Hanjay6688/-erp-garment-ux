import {fixtureDate} from './accessoryPricing'

export const lastWarehouseDay=()=>[fixtureDate,new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Jakarta',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date())].sort().at(-1)!
export const dayOk=(day:string)=>/^\d{4}-\d{2}-\d{2}$/.test(day)&&Number.isFinite(Date.parse(day))&&new Date(day).toISOString().slice(0,10)===day&&day<=lastWarehouseDay()
