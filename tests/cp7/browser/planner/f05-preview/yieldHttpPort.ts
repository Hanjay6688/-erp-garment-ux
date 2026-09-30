import type { YieldReadPort } from './CuttingYieldAnalyzer'
import { guardYieldReview, yieldInputKey, type YieldReview } from './cuttingYieldContract'

// Same-origin disposable demo only. No fallback to prewritten ranges.
export const readComputedYieldDemo: YieldReadPort = async (input, context, _mix, example) => {
  const response=await fetch('/__cp7_demo_yield',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({input,inputKey:yieldInputKey(input),context,example}),signal:AbortSignal.timeout(15000),cache:'no-store'})
  if(!response.ok)throw new Error('Analyzer backend unavailable')
  return guardYieldReview(await response.json() as YieldReview,input,context)
}
