"""Optional preparation: one private caller substitution, parent command exact."""
from hashlib import sha256
from pathlib import Path
import json
import re
from cp7_bounded_analysis_stage.source import once
from cp7_frozen_analysis_choice_v2 import render as parent

ROOT=Path(__file__).resolve().parent
SCHEMA='cp7_frozen_choice_preparation'
REPLACED=parent.SCHEMA+'.review_context('+parent.reader.ARGS+')'
READER=parent.reader.NEW+'('+parent.reader.ARGS+')'
PRIVATE={'guard_work()':'v','source(uuid,text)':'v','worker_active(uuid)':'s','status(cp7_analysis_stage.jobs,boolean)':'s',
 'request(uuid,text)':'v','get(uuid,text)':'v','step(uuid,text)':'v',
 'reference(cp7_analysis_stage.jobs)':'s','run_next()':'v','purge_expired(integer)':'v'}
PUBLIC={f'public.erp_cp7_{verb}_frozen_choice_preparation_v1(uuid,text)':verb for verb in ('request','get','step')}
FUNCTIONS={**{SCHEMA+'.'+sig:(vol,False) for sig,vol in PRIVATE.items()},
 **{sig:('v',True)for sig in PUBLIC},REPLACED:('v',False),READER:('v',False)}

def originals():return {REPLACED:parent.definitions()[REPLACED],READER:parent.reader.reader()}

def replacement(sig=REPLACED):
 s=originals()[sig]
 s=once(s,'create function ','create or replace function ')
 return once(s,'cp7_frozen_analysis_readers_v2.reference(j)',SCHEMA+'.reference(j)')

def render():
 s=(ROOT/'work.sql').read_text()
 for sig in PRIVATE:
  s+=f'\nalter function {SCHEMA}.{sig}owner to cp7_capture;\nrevoke all on function {SCHEMA}.{sig}from public,anon,authenticated,service_role;\n'
 for sig,verb in PUBLIC.items():
  name=sig.split('(')[0]
  s+=f"\ncreate function {name}(p_source_request uuid,p_access text)returns jsonb\nlanguage sql volatile security definer set search_path=''set TimeZone='UTC'as $$\n select {SCHEMA}.{verb}(p_source_request,p_access)\n$$;\nalter function {sig}owner to cp7_capture;\nrevoke all on function {sig}from public,anon,authenticated,service_role,postgres;\ngrant execute on function {sig}to authenticated;\n"
 return s+'\n'+'\n'.join(replacement(sig)for sig in originals())+'\n'

def manifest():
 return dict(contract='cp7.frozen-choice-preparation.optional.v1',
  sql_sha256=sha256(render().encode()).hexdigest(),parent_reader_bodies_sha256={sig:sha256(body.encode()).hexdigest()for sig,body in originals().items()},
  exact_parent_command_sha256=sha256(parent.definitions()[parent.SCHEMA+'.apply(jsonb,uuid)'].encode()).hexdigest(),
  private_functions=10,new_public_rpcs=3,new_tables=1,existing_replacements=list(originals()),
  source_request_is_original=True,default_adopted=False,server_scheduler_installed=False,
  actual_Native_qualified=False,actual_Auth_HTTP_credit=False,production_go=False)

if __name__=='__main__':
 (ROOT/'preparation.prepared.sql').write_text(render())
 (ROOT/'PREPARATION.json').write_text(json.dumps(manifest(),indent=2)+'\n')
