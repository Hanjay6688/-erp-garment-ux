import type {AnalysisResult} from './cp7/contract'

type Item = AnalysisResult['recommendations'][number]
type Metric = AnalysisResult['metrics'][number]
type Timeline = AnalysisResult['timeline']

function pieces(fact: Item['actual_fg'] | undefined) {
  return fact && 'value' in fact && /^\d+(?:\.0+)?$/.test(fact.value) ? BigInt(fact.value.split('.')[0]) : null
}

export function StockCoverage({item,metrics,timeline}:{item:Item;metrics:Metric[];timeline:Timeline}) {
  const key=item.target.key
  const metric=metrics.find(m=>m.scope_kind==='TARGET'&&m.scope_key===key&&m.metric_id==='FG_STOCK_THRESHOLD:'+key)
  if(!metric)return null
  const actual=pieces(metric.operands[0]),threshold=pieces(metric.value),gap=pieces(item.q_conditional)
  if(actual===null||threshold===null)return null
  const directed=pieces(metric.operands[1]),allocated=pieces(metric.operands[2]),target=pieces(item.target_qty)
  const shortage=timeline.filter(day=>day.target_key===key&&day.first_gap_at).sort((a,b)=>a.date.localeCompare(b.date))[0]
  const covered=(directed??0n)+(allocated??0n)
  const projection=shortage?'Proyeksi kekurangan pada '+shortage.date+'.':
    gap===null?'Proyeksi belum diketahui.':gap>0n?'Proyeksi masih kurang '+gap+' pcs.':
    covered>0n&&target!==null&&actual<target?'Kebutuhan tertutup WIP tepat waktu pada skenario ini ('+covered+' pcs).':'Proyeksi kebutuhan terpenuhi.'
  return <div><span>{actual<=threshold?'Stok aktual rendah':'Stok aktual di atas ambang'} · {actual.toString()} pcs, ambang {threshold.toString()} pcs.</span><br/><span>{projection}</span></div>
}
