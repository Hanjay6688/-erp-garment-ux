"""Derive an opt-in integration overlay without editing qualified predecessors.

This module only renders files. Installation requires an exact predecessor,
catalog admission and complete qualification; none is implied by rendering.
"""
from pathlib import Path
from hashlib import sha256
import re
import json
from cp7_production_stage import _body
from cp7_bounded_analysis_stage.source import current_analysis_source
import cp7_product_analog_consumer as consumer

ROOT=Path(__file__).resolve().parent
SCRIPTS=ROOT.parent


def block(path,name):
    text=(SCRIPTS/path).read_text()
    found=re.findall(r'create (?:or replace )?function '+re.escape(name)+r'\(.*?\$\$;',text,re.S)
    if len(found)!=1:raise ValueError('ANALOG_CONSUMER_PREDECESSOR_NOT_UNIQUE: '+name)
    return found[0].replace('create function ','create or replace function ',1)


def once(text,old,new):
    if text.count(old)!=1:raise ValueError('ANALOG_CONSUMER_ANCHOR_CHANGED: '+old[:120])
    return text.replace(old,new,1)


def originals():
    specs=[
      ('cp7-src/planning/baseline-source.sql','cp7_baseline_native.source_within','integer'),
      ('cp7_reorder_inputs/capture.sql','cp7_reorder_inputs.capture_baseline','integer'),
      ('cp7_target_policy_stage/sql/cp7_baseline_native__build.sql','cp7_baseline_native.build','jsonb,jsonb'),
      ('cp7_target_policy_stage/sql/cp7_analysis_stage__baseline_rows.sql','cp7_analysis_stage.baseline_rows','jsonb,jsonb,jsonb,text'),
      ('cp7_production_stage/sql/cp7_analysis_stage__history_prep.sql','cp7_analysis_stage.history_prep','jsonb,jsonb,integer,bigint,integer'),
      ('cp7_reorder_inputs/history.sql','cp7_reorder_inputs.history','jsonb,jsonb'),
      ('cp7_reorder_inputs/read.sql','cp7_reorder_inputs.compile','jsonb'),
      ('cp7_history_bounded/inputs.sql','cp7_history_bounded.compile','jsonb,jsonb,jsonb,integer'),
      ('cp7_bounded_analysis_stage/stage.sql','cp7_bounded_analysis_stage.run_scenario_unit','cp7_analysis_stage.jobs,cp7_analysis_stage.units,jsonb'),
      ('cp7_bounded_analysis_stage/stage.sql','cp7_analysis_stage.run_scenario_unit','cp7_analysis_stage.jobs,cp7_analysis_stage.units,jsonb'),
      ('cp7_bounded_analysis_stage/stage.sql','cp7_bounded_analysis_stage.analysis_source','integer,integer'),
      ('cp7_bounded_analysis_stage/stage.sql','cp7_bounded_analysis_stage.producer_hash',''),
      ('cp7_bounded_analysis_stage/stage.sql','cp7_bounded_analysis_stage.native_work_fingerprint','jsonb'),
      ('cp7_bounded_analysis_stage/stage.sql','cp7_supply_native.fingerprint','jsonb'),
      ('cp7_reorder_inputs/source.sql','cp7_reorder_inputs.source_within','integer'),
      ('cp7_reorder_inputs/points.sql','cp7_reorder_inputs.points','jsonb,jsonb,jsonb,jsonb'),
      ('cp7_product_analog_choice_stage/choice.sql','cp7_product_analog_choice.apply','jsonb,uuid'),
    ]
    out={name+'('+args+')':block(path,name)for path,name,args in specs}
    out['cp7_analysis_native.source_within(integer,integer)']=current_analysis_source().replace('create function ','create or replace function ',1)
    return out


def add_identity(text,variable='c'):
    old="'production_policies',"+variable+"->'production_policies'->'rows'"
    new=old+",'product_analog_choices',"+variable+"->'product_analog_choices','analog_consumer_engine',"+variable+"->'analog_consumer_engine'"
    return once(text,old,new)


def two_pass(text,indent,baseline_hash,output_anchor):
    line=indent+"chunk_targets:=cp7_analysis_stage.baseline_rows(c,chunk_rows,stock,"+baseline_hash+");\n"
    text=once(text,line,'')
    text=once(text,indent+'for item in select value from jsonb_array_elements(chunk_targets)loop targets_out:=array_append(targets_out,item);end loop;\n','')
    # Histories are complete before the first target is calculated. Reuse the
    # same prepared context for all target chunks; never recapture a source.
    prefix=indent[:-1] if indent else ''
    phase=(prefix+"c:=c||jsonb_build_object('analog_consumer_context',cp7_product_analog_consumer.prepare(c,to_jsonb(rows_out),q));\n"
      +prefix+"offset_at:=0;\n"+prefix+"while offset_at<n loop\n"
      +indent+"select coalesce(jsonb_agg(x order by ord),'[]')into chunk_rows from jsonb_array_elements(to_jsonb(rows_out))with ordinality all_history(x,ord)where ord>offset_at and ord<=offset_at+per;\n"
      +line+indent+"for item in select value from jsonb_array_elements(chunk_targets)loop targets_out:=array_append(targets_out,item);end loop;\n"
      +indent+"offset_at:=offset_at+per;\n"+prefix+"end loop;\n")
    return once(text,output_anchor,phase+output_anchor)


def replacements():
    consumer.verify_sources()
    out=originals()
    for sig in ['cp7_baseline_native.source_within(integer)','cp7_reorder_inputs.capture_baseline(integer)']:
        out[sig]=once(out[sig],"select value||jsonb_build_object('profiles',",
          "select value||jsonb_build_object('product_analog_choices',cp7_product_analog_consumer.capture(value),\n  'analog_consumer_engine',cp7_product_analog_consumer.engine_hash(),'profiles',")
    sig='cp7_baseline_native.build(jsonb,jsonb)';text=out[sig]
    first=text.index(' for r in select value');last=text.index(' return jsonb_build_object',first)
    text=text[:first]+" rows:=array(select value from jsonb_array_elements(cp7_product_analog_consumer.baseline_rows(c,h->'history'->'rows',h->'current_stock',hash,cp7_product_analog_consumer.prepare(c,h->'history'->'rows',q)))order by value->>'target_key');\n"+text[last:]
    out[sig]=add_identity(text)
    sig='cp7_analysis_stage.baseline_rows(jsonb,jsonb,jsonb,text)';text=out[sig]
    start=text.index('declare ');end=text.index('end $$;')
    out[sig]=text[:start]+"begin\n return cp7_product_analog_consumer.baseline_rows(c,history_rows,current_stock,hash,c->'analog_consumer_context');\n"+text[end:]
    sig='cp7_analysis_stage.history_prep(jsonb,jsonb,integer,bigint,integer)';out[sig]=add_identity(out[sig])
    sig='cp7_reorder_inputs.history(jsonb,jsonb)';out[sig]=two_pass(out[sig],'  ',"g->>'baseline_hash'"," return jsonb_build_object('contract_version','cp7.reorder-native-inputs.v1'")
    for sig,anchor in [('cp7_reorder_inputs.compile(jsonb)',"  inputs:=jsonb_build_object('contract_version','cp7.reorder-native-inputs.v1'"),('cp7_history_bounded.compile(jsonb,jsonb,jsonb,integer)',"  inputs:=jsonb_build_object('contract_version','cp7.reorder-native-inputs.v1'")]:
        out[sig]=two_pass(add_identity(out[sig]),'   ','baseline_hash',anchor)
    for sig in ['cp7_bounded_analysis_stage.run_scenario_unit(cp7_analysis_stage.jobs,cp7_analysis_stage.units,jsonb)','cp7_analysis_stage.run_scenario_unit(cp7_analysis_stage.jobs,cp7_analysis_stage.units,jsonb)']:
        out[sig]=once(out[sig]," if u.kind='BASE_ROWS'then\n", " if u.kind='BASE_ROWS'then\n  c:=c||jsonb_build_object('analog_consumer_context',cp7_product_analog_consumer.prepare(c,\n   (select coalesce(jsonb_agg(x.payload order by x.ord),'[]')from cp7_analysis_stage.target_rows x where x.job_id=j.id and x.kind='HIST'),j.query));\n")
    for sig in ['cp7_bounded_analysis_stage.analysis_source(integer,integer)','cp7_analysis_native.source_within(integer,integer)','cp7_bounded_analysis_stage.producer_hash()','cp7_reorder_inputs.source_within(integer)']:
        out[sig]=once(out[sig],"where n.nspname in(","where n.nspname in('cp7_product_analog_consumer','cp7_product_analog_choice',")
    for sig in ['cp7_bounded_analysis_stage.native_work_fingerprint(jsonb)','cp7_supply_native.fingerprint(jsonb)']:
        out[sig]=add_identity(out[sig])
    sig='cp7_reorder_inputs.source_within(integer)';text=out[sig]
    anchor="'production_policies',boundary.c->'production_policies'->'rows'"
    if text.count(anchor)!=2:raise ValueError('ANALOG_CONSUMER_REORDER_HASH_ANCHORS')
    out[sig]=text.replace(anchor,anchor+",'product_analog_choices',boundary.c->'product_analog_choices','analog_consumer_engine',boundary.c->'analog_consumer_engine'")
    sig='cp7_reorder_inputs.points(jsonb,jsonb,jsonb,jsonb)'
    # Keep observed own PCS/days intact. Scaled analog demand can be fractional
    # and must never be exposed as historical sales or copied into sales_pcs.
    out[sig]=once(out[sig],"'target',kernel,'manual_state',manual_state,", "'target',kernel,'demand_basis',row_value->'demand_estimate'->'basis',\n   'analog_resolution',row_value->'analog_resolution','manual_state',manual_state,")
    sig='cp7_product_analog_choice.apply(jsonb,uuid)'
    old=" if action='CONFIRM'and cp7_analysis_native.fingerprint(cp7_bounded_analysis_stage.source_for(j.reference,j.query))is distinct from j.source_hash then\n  raise exception using errcode='40001',message='CP7_ANALOG_CHOICE_SOURCE_CHANGED';end if;"
    new=" if action='CONFIRM'then\n  current_source:=cp7_product_analog_consumer.normalize_confirmed_delta(j.reference,cp7_bounded_analysis_stage.source_for(j.reference,j.query),outcome);\n  if cp7_analysis_native.fingerprint(current_source)is distinct from j.source_hash then\n   raise exception using errcode='40001',message='CP7_ANALOG_CHOICE_SOURCE_CHANGED';end if;\n end if;"
    out[sig]=once(out[sig],old,new)
    return out


def render():
    return '\n\n'.join(replacements().values())+'\n'


def manifest():
    return dict(contract='cp7.product-analog-consumer-overlay.prototype.v1',
      predecessor_body_sha256={sig:sha256(_body(sql).encode()).hexdigest()for sig,sql in originals().items()},
      replacement_body_sha256={sig:sha256(_body(sql).encode()).hexdigest()for sig,sql in replacements().items()},
      sql_sha256=sha256(render().encode()).hexdigest(),confirmation_sql_sha256=sha256((ROOT/'confirmation.sql').read_bytes()).hexdigest(),
      existing_replacements=len(originals()),private_functions=7,new_tables=0,new_public_rpcs=0,
      default_installed=False,Native_qualified=False,frontend_provenance_integration=False,production_go=False)


if __name__=='__main__':
    (ROOT/'hooks.sql').write_text(render())
    (ROOT/'MANIFEST.json').write_text(json.dumps(manifest(),indent=2)+'\n')
