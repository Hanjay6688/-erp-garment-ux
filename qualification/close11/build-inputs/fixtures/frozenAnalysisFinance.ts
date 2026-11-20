import fixture from './analysisFinanceSidecar.json'
import type {NativeDemandQuery} from '../../src/nativeDemandHistory'
// Explicit controlled wire data; not a Native finance capture or report proof.
export function frozenFinanceFixture(run:{query:NativeDemandQuery;reference:{captured_at:string;source_hash:string};pageSet:{request_id:string}},state:'READY'|'RUNNING'|'ACCESS_REVOKED'='READY'){
 const f=structuredClone(fixture)as Record<string,any>,q=run.query,asOf='2026-10-07'
 f.request_id=run.pageSet.request_id;f.query=q;f.reference={...run.reference}
 const dates={from:q.from_date,to:q.through_date,as_of:asOf}
 f.capture.dates=dates;f.result.dates=dates
 f.capture.report_read_at=f.result.report_read_at='2026-10-07T10:03:00.654321Z'
 for(const metric of f.result.metrics){const performance=metric.metric_id.includes(':performance:');metric.period_start=performance?q.from_date:asOf;metric.period_end=performance?q.through_date:asOf}
 if(state==='RUNNING'){f.state=f.capture.state=state;f.result=null;Object.assign(f.capture,{units_done:0,units_total:null,report_read_at:null,readiness:null})}
 if(state==='ACCESS_REVOKED'){f.state=state;f.capture=null;f.result=null}
 return f
}
