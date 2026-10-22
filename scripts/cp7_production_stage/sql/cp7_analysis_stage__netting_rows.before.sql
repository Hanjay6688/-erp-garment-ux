create or replace function cp7_analysis_stage.netting_rows(g jsonb,c jsonb,wip jsonb,capacity jsonb,alloc_status text,plan jsonb,
 planned_ord jsonb,rows jsonb,first jsonb,pairs jsonb,candidates jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare x jsonb;r jsonb;t jsonb;p jsonb;m jsonb;eta jsonb;line jsonb;net jsonb;supplies jsonb;directed_edges jsonb;line_edges jsonb;
 raw_need numeric;gap numeric;directed numeric;candidate numeric;open_work jsonb[];open_index integer[];i integer;w integer;supply_list jsonb[];edge_list jsonb[];
 row_list jsonb[]:='{}';by_position jsonb;hash text:=g->>'hash';eta_at jsonb:=g->'eta_at';eta_repeated jsonb:=g->'eta_repeated';
 planned_at jsonb:=plan->'planned_at';planned_repeated jsonb:=plan->'planned_repeated';etas jsonb:=g->'etas';matching jsonb:=g->'matching';
begin
 for x in select y.value from jsonb_array_elements(rows)with ordinality y(value,o)order by y.o loop
  r:=x->'row';directed:=0;candidate:=0;raw_need:=null;gap:=null;supplies:='[]';directed_edges:='[]';net:=null;
  if planned_repeated?(r->>'target_key')then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  t:=planned_at->(r->>'target_key');
  if t is not null then
   raw_need:=cp7_wip.pcs(t->'need_pcs');
   if open_work is null then
    open_work:='{}';open_index:='{}';i:=0;
    for p in select value from jsonb_array_elements(g->'eligible')loop
     i:=i+1;
     if cp7_wip.pcs(p->'remaining_pcs')>0 then open_work:=array_append(open_work,p);open_index:=array_append(open_index,i);end if;
    end loop;
   end if;
   -- The pair result of each open position for this key's first row: the
   -- first result of that position in the key's match results.
   select coalesce(jsonb_object_agg(f.k,f.v),'{}')into by_position from(
    select y.value->>'i' k,(array_agg(y.value->'e'->'result' order by y.o))[1] v
    from jsonb_array_elements(coalesce(pairs->(r->>'target_key'),'[]'))with ordinality y(value,o)group by 1)f;
   supply_list:='{}';edge_list:='{}';
   for w in 1..coalesce(cardinality(open_work),0) loop
    p:=open_work[w];m:=by_position->(open_index[w]::text);
    if eta_repeated?(p->>'key')then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
    eta:=eta_at->(p->>'key');
    if m->>'match'='CONFIRMED_TARGET'then
     supply_list:=array_append(supply_list,jsonb_build_object('physical_key',p->'key','snapshot_id',wip->'snapshot_id',
      'target_key',r->'target_key','size_id',r->'size_id','kind','DIRECTED',
      'qty_pcs',case when p->'projection'->>'quality'='SCENARIO'then p->'projection'->'projected_good_pcs'else null end,
      'eta',coalesce(eta->'at','null'::jsonb),'eligible',true,'refs',p->'refs'));
     if p->'projection'->>'quality'='SCENARIO'and eta->>'at'is not null then
      edge_list:=array_append(edge_list,jsonb_build_object('key',p->'key','position_key',p->'key',
       'target_key',r->'target_key','projected_good_pcs',p->'projection'->'projected_good_pcs','refs',p->'refs'));
     end if;
    end if;
   end loop;
   for p in select value from jsonb_array_elements(candidates->(r->>'target_key'))loop
    if eta_repeated?(p->>'position_key')then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
    eta:=eta_at->(p->>'position_key');
    supply_list:=array_append(supply_list,jsonb_build_object('physical_key',p->'position_key','snapshot_id',wip->'snapshot_id',
     'target_key',r->'target_key','size_id',r->'size_id','kind','ALLOCATED_CANDIDATE','qty_pcs',p->'projected_good_pcs',
     'eta',eta->'at','eligible',true,'refs',p->'refs'));
   end loop;
   supplies:=to_jsonb(supply_list);directed_edges:=to_jsonb(edge_list);
   net:=cp7_baseline.net(jsonb_build_object('contract_version','cp7.net-input.v1','snapshot_id',wip->'snapshot_id',
    'scope_id','GLOBAL_NATIVE_PLANNING','scenario_id',coalesce(c->'schedule'->'plan_id',to_jsonb('unreviewed-'||hash)),
    'target_key',r->'target_key','size_id',r->'size_id','deadline',t->'deadline',
    'target_pcs',r->'target'->'target_pcs','available_fg_pcs',r->'available_fg_pcs','supplies',supplies,'refs',r->'refs'));
   gap:=(net->>'q_base_pcs')::numeric;directed:=coalesce((net->>'directed_on_time_pcs')::numeric,0);
   candidate:=coalesce((net->>'candidate_on_time_pcs')::numeric,0);
  end if;
  if t is null then line:=jsonb_build_object('status','UNKNOWN','reason','TARGET_NEEDS_OR_POLICY_UNREVIEWED');
  else
   line_edges:=directed_edges||coalesce(candidates->(r->>'target_key'),'[]'::jsonb);
   -- build() reuses the first loop's timeline only for the very row that
   -- loop planned: a planned key is unique here (planned_repeated refused
   -- above), so that row is the one with this key's planned ord.
   if line_edges='[]'::jsonb and(planned_ord->>(r->>'target_key'))::integer=(x->>'ord')::integer then
    line:=first->(x->>'ord')->'line';
   else line:=cp7_netting_native.timeline(c,r,etas,line_edges,matching,wip);end if;
  end if;
  row_list:=array_append(row_list,r||jsonb_build_object('raw_gap_pcs',raw_need::text,'directed_on_time_good_pcs',net->'directed_on_time_pcs',
   'base_gap_pcs',net->'q_base_pcs','conditional_gap_pcs',case when alloc_status='SCENARIO'then net->'q_conditional_pcs'else null end,
   'net',net,
   'candidate_allocated_good_pcs',case when alloc_status='SCENARIO'then candidate::text else null end,
   'timeline',line,'start_new_pcs',case when t->>'production_status'='STOP'then '0'else null end,
   'material_state','UNKNOWN','new_start_capacity',capacity,'apply_enabled',false,
   'netting_basis','NATIVE_AVAILABLE_FG_ONCE_SOURCE_BOUND_YIELD_AND_ONE_SHARED_REMAINING_CALENDAR',
   'reason','SCENARIO_EXISTING_SUPPLY_DISTINCT_FROM_NEW_START_MATERIAL_FEASIBILITY'));
 end loop;
 return to_jsonb(row_list);
end $$;
