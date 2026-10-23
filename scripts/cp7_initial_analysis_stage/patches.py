"""Two counted B hooks; no change to the frozen predecessor sources."""
from cp7_production_stage import _body

REQUEST='cp7_analysis_stage.request(jsonb,uuid)'
TICK='cp7_alert_native.analysis_tick()'
SIGNATURES=(REQUEST,TICK)


def once(text,old,new,signature):
    if text.count(old)!=1:
        raise ValueError('OW13A_HOOK_ANCHOR_CHANGED: '+signature+': '+repr(old))
    return text.replace(old,new,1)


def patched(originals):
    if set(originals)!=set(SIGNATURES):
        raise ValueError('OW13A_HOOK_SET_CHANGED')
    request=once(originals[REQUEST],"begin\n if current_setting('transaction_isolation')",
        """begin
 if p_query?'initial_auto'then
  if p_request is not null or jsonb_typeof(p_query)is distinct from'object'then raise exception 'CP7_INITIAL_MODE';end if;
  if jsonb_typeof(p_query->'initial_auto')is distinct from'string'
   or p_query->>'initial_auto'not in('STATUS','ENSURE')
   or (select count(*)from jsonb_object_keys(p_query))<>1 then raise exception 'CP7_INITIAL_MODE';end if;
  return cp7_initial_analysis.current(p_query->>'initial_auto'='ENSURE');
 end if;
 if current_setting('transaction_isolation')""",REQUEST)
    tick=once(originals[TICK],'prior jsonb;a jsonb;res jsonb;',
              'prior jsonb;a jsonb;res jsonb;initial_result jsonb;',TICK)
    tick=once(tick,'s:=cp7_alert_native.current_settings();',"""begin
  initial_result:=cp7_initial_analysis.tick();
 exception when query_canceled then raise;
 when others then initial_result:=jsonb_build_object('outcome','INITIAL_ANALYSIS_ERROR','sqlstate',SQLSTATE,
  'code',case when SQLERRM~'^CP7_[A-Z0-9_]+$'then SQLERRM else'CP7_INITIAL_ERROR'end);
 end;
 s:=cp7_alert_native.current_settings();""",TICK)
    for old in ("jsonb_build_object('ran',false,'outcome','NOT_CONFIGURED')",
                "jsonb_build_object('ran',false,'outcome','OWNER_ACCESS_DENIED')"):
        tick=once(tick,old,old+"||jsonb_build_object('initial_analysis',initial_result)",TICK)
    tick=once(tick,"return cp7_alert_native.record_tick('ANALYSIS',res);",
              "return cp7_alert_native.record_tick('ANALYSIS',res||jsonb_build_object('initial_analysis',initial_result));",TICK)
    return {REQUEST:request,TICK:tick}
