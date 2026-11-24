export type PeriodKind = 'all'|'day'|'week'|'month'|'custom'
export type Period = {kind:PeriodKind; anchor:string; start:string; end:string}
const iso=(date:Date)=>date.toISOString().slice(0,10)
export const dateLabel=(date:string)=>date?new Intl.DateTimeFormat('id-ID',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'}).format(new Date(date+'T12:00:00Z')):'…'
export function periodFor(kind:PeriodKind,anchor:string):Period {
  const base={kind,anchor,start:'',end:''}
  if(!anchor||kind==='all')return base
  const day=new Date(anchor+'T12:00:00Z'),last=new Date(day)
  if(kind==='week'){day.setUTCDate(day.getUTCDate()-(day.getUTCDay()+6)%7);last.setTime(day.getTime());last.setUTCDate(day.getUTCDate()+6)}
  if(kind==='month'){day.setUTCDate(1);last.setUTCMonth(last.getUTCMonth()+1,0)}
  return {...base,start:iso(day),end:iso(last)}
}
export const matchesPeriod=(date:string,p:Period)=>(!p.start||date>=p.start)&&(!p.end||date<=p.end)
export const periodLabel=(p:Period)=>p.start||p.end?dateLabel(p.start)+' – '+dateLabel(p.end):'Semua tanggal'
export function PeriodFilter({label,value,onChange}:{label:string;value:Period;onChange:(p:Period)=>void}){
  return <fieldset className="owner-period"><legend>{label}</legend><div className="owner-period-tabs">{([['all','Semua'],['day','Harian'],['week','Mingguan'],['month','Bulanan'],['custom','Rentang']] as const).map(([kind,name])=><button type="button" key={kind} aria-pressed={value.kind===kind} onClick={()=>onChange(kind==='custom'?{...value,kind}:periodFor(kind,value.anchor))}>{name}</button>)}</div>
    {['day','week','month'].includes(value.kind)&&<label>Tanggal acuan<input aria-label={label+' tanggal acuan'} type="date" value={value.anchor} onChange={e=>{if(e.target.value)onChange(periodFor(value.kind,e.target.value))}}/></label>}
    <label>Mulai<input aria-label={label+' mulai'} type="date" value={value.start} onChange={e=>onChange({...value,kind:'custom',start:e.target.value})}/></label>
    <label>Sampai<input aria-label={label+' sampai'} type="date" value={value.end} onChange={e=>onChange({...value,kind:'custom',end:e.target.value})}/></label>
    {value.start>value.end&&value.end&&<p role="alert">Tanggal akhir harus sama atau sesudah tanggal mulai.</p>}</fieldset>
}
