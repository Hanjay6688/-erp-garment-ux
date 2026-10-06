import { execFileSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { jsonArg } from './runtime.mjs'
import { assemblyArgs, extractFunction, installAssemblyControls } from './analysis-assembly-fixture.mjs'

// P19: report_render grouped product labels once instead of a per-recommendation
// query over the whole serve outcome. Exact predecessor text vs current function
// on compiler outputs; disposable kernel comparison only, no Native/Auth credit.
export const renderBase = 'c1f91041035941edded57da13482176701b2bfb6'
const path = 'scripts/cp7-src/planning/report-publication.sql'

export async function installRenderControls(db) {
 await installAssemblyControls(db)
 const current = readFileSync(path, 'utf8'), old = execFileSync('git', ['show', `${renderBase}:${path}`], { encoding: 'utf8', maxBuffer: 1024 * 1024 })
 await db.execute(`${extractFunction(current, 'cp7_analysis_native.report_fact')}
  ${[old, current].map((src, i) => extractFunction(src, 'cp7_analysis_native.report_render').replace('create function cp7_analysis_native.report_render(', `create function public.p19_render_${i}(`)).join('\n')}
  ${[0, 1].map(i => `create function public.p19_render_state_${i}(e jsonb,k text,t text)returns text language plpgsql as $$begin perform public.p19_render_${i}(e,k,t);return 'NO_ERROR';exception when others then return SQLSTATE;end$$;`).join('\n')}
  create function public.p19_outcome(c jsonb,q jsonb,p uuid,a jsonb,f jsonb)returns jsonb language sql as $$
   select jsonb_build_object('contract_version','cp7.native-analysis-run.v1','run_id',p,'request_id',p,'analysis',public.p19_assembly_1(c,q,p,a),
    'product_labels',coalesce((select jsonb_agg(jsonb_build_object('target_key',x->>'root_id'||':'||(x->>'size_id'),
     'sku',coalesce(x->'commercial'->0->>'sku',x->>'sku'),'product_name',x->>'product_name')order by x->>'root_id')
     from jsonb_array_elements(c->'facts'->'products')x),'[]'::jsonb),'query',q,'financial_source',f,'source_state','UNCHANGED')$$;`)
}

export const outcomeSql = (c, finance = null) => `public.p19_outcome(${assemblyArgs(c)},${jsonArg(finance)})`
