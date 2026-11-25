import type { AttendanceBook, AttendancePeriodStatus } from '../attendance/domain'
import { attendanceEntryAmount } from '../attendance/domain'

type Choice = 'CARRY' | 'EXPENSE'
type Decision = {id:string; choice:Choice; reason:string; day:string; cost:number; allocated?:{start:string;end:string;qty:number;reason:string}}
type History = Record<string, Decision[]>
export const attendanceChoiceKey = 'erp.demo.attendance-cost-choice.v1'
export const readAttendanceChoices = ():History => JSON.parse(sessionStorage.getItem(attendanceChoiceKey) ?? '{}')

export const postedAttendanceKey = 'erp.demo.attendance-posted.v1'
type PostedAttendance = {books:Record<string,AttendanceBook>;statuses:Record<string,AttendancePeriodStatus>;dates:Record<string,string>}
export const readPostedAttendance = ():PostedAttendance => JSON.parse(sessionStorage.getItem(postedAttendanceKey) ?? '{"books":{},"statuses":{},"dates":{}}')

export const periodCostPath = (area: 'kantong' | 'absensi') => '/keuangan/hpp/?biaya=' + area
export const pocketCostPath = '/gudang/kain-kantong/?tab=biaya'

export function attendanceSourcePath(mandor:string, start:string, end:string) {
  const params = new URLSearchParams({mandor, mulai:start, akhir:end})
  return '/keuangan/absensi/?' + params + '#biaya-absensi'
}

export function attendancePeriods() {
  const posted = readPostedAttendance()
  const choices = readAttendanceChoices()
  return Object.entries(posted.statuses).filter(([,status]) => status === 'POSTED').map(([key]) => {
    const [id, start, end] = key.split('::')
    const mandor = id.charAt(0).toUpperCase() + id.slice(1)
    const decision = choices[[mandor,start,end].join('|')]?.at(-1)
    const cost = Object.values(posted.books[key] ?? {}).reduce((sum,line) => sum + attendanceEntryAmount(line, []), 0)
    return {key, id, mandor, start, end, cost, decision}
  }).sort((a,b) => b.start.localeCompare(a.start) || a.mandor.localeCompare(b.mandor))
}
