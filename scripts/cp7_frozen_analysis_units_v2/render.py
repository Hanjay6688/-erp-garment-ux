"""Prepare exact hooks; no installer, facade, connection, or default adoption."""
from pathlib import Path
from hashlib import sha256
import json
from cp7_production_stage import _body
from cp7_bounded_analysis_stage import source
from cp7_reorder_supply import patches
from cp7_frozen_analysis_v2.render import block

ROOT=Path(__file__).resolve().parent
BOUNDED=ROOT.parent/'cp7_bounded_analysis_stage/stage.sql'
TARGET=ROOT.parent/'cp7_model_target_consumer_v2_stage/hooks.sql'
ANALOG=ROOT.parent/'cp7_product_analog_consumer_stage/hooks.sql'


def original_run():
    return patches.patched({
        patches.RUN: source.block('analysis-stages.sql','cp7_analysis_stage.run_unit'),
        patches.SOURCE: source.block('analysis.sql','cp7_analysis_native.source_within'),
    })[patches.RUN]


def run_hook():
    # Preserve Native PAGE/PAGE_INDEX early exits and the already admitted
    # supply-budget hook. Only the once-per-unit local-reference assignment
    # changes. No target, quantity, allocation or finance math is duplicated.
    old=original_run()
    new=source.once(old," c:=j.reference||'{}'::jsonb;",
                    ' c:=cp7_frozen_analysis_units_v2.unit_reference(j,u);')
    return source.once(new,'create function ','create or replace function ')


def request_candidate():
    old=block((ROOT.parent/'cp7_bounded_analysis_stage/stage.sql').read_text(),
              'cp7_bounded_analysis_stage.request')
    new=source.once(old,'cp7_bounded_analysis_stage.request(',
                    'cp7_frozen_analysis_units_v2.request(')
    new=source.once(new,'cp7.bounded-analysis-request.v1','cp7.bounded-analysis-request.v2')
    return source.once(new,'cp7_bounded_analysis_stage.source(q,true)',
                       'cp7_frozen_analysis_units_v2.source(q,true)')


def originals():
    out={'cp7_analysis_stage.run_unit(cp7_analysis_stage.jobs,cp7_analysis_stage.units)':original_run()}
    for signature,path in {
      'cp7_supply_native.fingerprint(jsonb)':TARGET,
      'cp7_bounded_analysis_stage.require_inputs(jsonb,jsonb)':BOUNDED,
      'cp7_bounded_analysis_stage.source_for(jsonb,jsonb)':BOUNDED,
      # The installed analog parent adds per-chunk analog_consumer_context.
      # Preserve that admitted body on both the v2 branch and the inverse.
      'cp7_analysis_stage.run_scenario_unit(cp7_analysis_stage.jobs,cp7_analysis_stage.units,jsonb)':ANALOG,
      'cp7_analysis_stage.analysis_skeleton(jsonb,jsonb,uuid,jsonb,jsonb,jsonb,jsonb,jsonb,boolean,text)':TARGET,
      'cp7_schedule_staged_review.workspace(uuid)':BOUNDED,
      'cp7_schedule_staged_review.save(jsonb,uuid)':BOUNDED,
    }.items():out[signature]=block(path.read_text(),signature.split('(')[0])
    return out


def replacements():
    out=originals()
    for sig,old in out.items():
        name=sig.split('(')[0]
        if name=='cp7_analysis_stage.run_unit':new=run_hook()
        elif name=='cp7_supply_native.fingerprint':
            new=source.once(old," select case when c->>'bounded_request_contract'='cp7.bounded-analysis-request.v1'",
              " select case when c->>'bounded_request_contract'='cp7.bounded-analysis-request.v2'\n then cp7_frozen_analysis_v2.work_fingerprint(c)\n when c->>'bounded_request_contract'='cp7.bounded-analysis-request.v1'")
        elif name=='cp7_bounded_analysis_stage.require_inputs':
            new=source.once(old,' perform cp7_bounded_analysis_stage.work_fingerprint(c);',
              " if c->>'bounded_request_contract'='cp7.bounded-analysis-request.v2'then\n  perform cp7_frozen_analysis_v2.work_fingerprint(c);\n else perform cp7_bounded_analysis_stage.work_fingerprint(c);end if;")
        elif name=='cp7_bounded_analysis_stage.source_for':
            new=source.once(old," if p_reference?'bounded_request_contract'then",''' if p_reference->>'bounded_request_contract'='cp7.bounded-analysis-request.v2'then
  if p_reference->'bounded_query'is distinct from p_query then raise exception 'CP7_FROZEN_V2_REFERENCE_SHAPE';end if;
  begin
   return cp7_frozen_analysis_units_v2.source(p_query,false);
  exception when raise_exception then
   if sqlerrm in('CP7_ANALYSIS_STAGED_TARGET_LIMIT','CP7_BOUNDED_ANALYSIS_HISTORY_SCOPE','CP7_REORDER_NON_STOCK_SOURCE_INCOMPLETE')then
    raise exception using errcode='40001',message='CP7_SCHEDULE_SOURCE_CHANGED';end if;
   raise;
  end;
 end if;
 if p_reference?'bounded_request_contract'then''')
        elif name in('cp7_analysis_stage.run_scenario_unit','cp7_analysis_stage.analysis_skeleton'):
            expected=1 if name.endswith('run_scenario_unit')else 2
            marker="c->>'bounded_request_contract'='cp7.bounded-analysis-request.v1'"
            if old.count(marker)!=expected:raise ValueError('FROZEN_UNITS_DISPATCH_PARENT_CHANGED:'+name)
            new=old.replace(marker,"c->>'bounded_request_contract'in('cp7.bounded-analysis-request.v1','cp7.bounded-analysis-request.v2')")
        elif name=='cp7_schedule_staged_review.workspace':
            new=source.once(old,' return outcome;',""" if r.facts->>'bounded_request_contract'='cp7.bounded-analysis-request.v2'then
  outcome:=outcome||jsonb_build_object('contract_version','cp7.planning-schedule-staged-bounded.v2',
   'bounded_request_contract',r.facts->'bounded_request_contract','bounded_reference_contract',r.facts->'bounded_reference_contract',
   'history_input_coverage',cp7_frozen_analysis_units_v2.coverage(r.job_id));end if;
 return outcome;""")
        elif name=='cp7_schedule_staged_review.save':
            new=source.once(old,' insert into cp7_schedule_native.commands(actor,request_id,payload,result)',""" if run.facts->>'bounded_request_contract'='cp7.bounded-analysis-request.v2'then
  outcome:=outcome||jsonb_build_object('contract_version','cp7.planning-schedule-staged-bounded-outcome.v2',
   'bounded_request_contract',run.facts->'bounded_request_contract','bounded_reference_contract',run.facts->'bounded_reference_contract');end if;
 insert into cp7_schedule_native.commands(actor,request_id,payload,result)""")
        else:raise ValueError(name)
        out[sig]=new.replace('create function ','create or replace function ',1)
    return out


def manifest():
    return dict(
        contract='cp7.frozen-analysis-unit-adapter.prepared.v2',
        original_run_body_sha256=sha256(_body(original_run()).encode()).hexdigest(),
        prepared_run_body_sha256=sha256(_body(run_hook()).encode()).hexdigest(),
        original_bodies_sha256={sig:sha256(_body(sql).encode()).hexdigest()for sig,sql in originals().items()},
        replacement_bodies_sha256={sig:sha256(_body(sql).encode()).hexdigest()for sig,sql in replacements().items()},
        compiler_called_only_in_HIST_PREP=True,jobs_reference_update=False,
        new_table=False,default_installer=False,public_RPC_added=False,
        version_dispatch_workspace_skeleton_prepared=True,private_catalog_installer_prepared=True,
        catalog_installer_Native_qualified=False,private_request_and_hooks_prepared=True,
        actual_Native_qualified=False,request_or_unit_integrated=False,production_go=False)


if __name__=='__main__':
    (ROOT/'run-hook.prepared.sql').write_text(run_hook()+'\n')
    (ROOT/'request.prepared.sql').write_text(request_candidate()+'\n')
    (ROOT/'hooks.prepared.sql').write_text('\n\n'.join(replacements().values())+'\n')
    (ROOT/'PREPARATION.json').write_text(json.dumps(manifest(),indent=2)+'\n')
