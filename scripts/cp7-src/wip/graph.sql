-- A conserved pool is original company/customer input of one exact size.
-- Nodes are positions of that same input, never additional supplies.
-- This kernel accepts normalized facts, not untrusted operational commands.
create function cp7_wip.reconcile(g jsonb) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare
 p jsonb; n jsonb; e jsonb; old jsonb; node jsonb; dest jsonb;
 pools jsonb:='{}'; nodes jsonb:='{}'; events jsonb:='{}'; outputs jsonb[]:='{}'; totals jsonb[]:='{}';
 k text; pool text; src text; dst text; ord numeric; last_ord numeric:=-1;
 qty numeric; val numeric; total numeric; wip numeric; fg numeric; bs numeric; withheld numeric; exited numeric;
 stages constant text[]:=array['CUT_UNASSIGNED','SEWING_ACTIVE','SEWING_UNRESOLVED',
  'LAUNDRY_OUTSTANDING','AWAIT_QC','FG','BS','MISSING','STUCK','HOLD','REWORK','REWASH','EXIT'];
 wip_stages constant text[]:=array['CUT_UNASSIGNED','SEWING_ACTIVE','SEWING_UNRESOLVED',
  'LAUNDRY_OUTSTANDING','AWAIT_QC','REWORK','REWASH'];
 i integer; j integer; repeated boolean[]; reversed boolean[]; at_pool jsonb; at_node jsonb;
 inputs numeric[]; balances numeric[]; ordered jsonb[]; o integer:=1;
begin
 perform cp7_wip.fields(g,array['contract_version','snapshot_id','complete','pools','nodes','events']);
 perform cp7_wip.key(g->'snapshot_id');
 if g->>'contract_version'<>'cp7.wip-graph.v1' or jsonb_typeof(g->'complete') is distinct from 'boolean'
   or jsonb_typeof(g->'pools') is distinct from 'array' or jsonb_typeof(g->'nodes') is distinct from 'array'
   or jsonb_typeof(g->'events') is distinct from 'array' then
  raise exception using errcode='22023',message='CP7_WIP_SHAPE';
 end if;
 if not (g->>'complete')::boolean then
  return jsonb_build_object('status','UNKNOWN','reason','SOURCE_CAPTURE_INCOMPLETE','snapshot_id',g->'snapshot_id');
 end if;
 if jsonb_array_length(g->'pools')>1000 or jsonb_array_length(g->'nodes')>10000 or jsonb_array_length(g->'events')>20000 then
  raise exception using errcode='54000',message='CP7_WIP_LIMIT';
 end if;
 -- Linear form: every key seen at an earlier element is flagged by position
 -- (an earlier element either passed or already raised), and the pool, node
 -- and event maps are built once after the loop that proved their keys unique.
 -- Balances live in arrays indexed by element position.
 select coalesce(array_agg(f.r order by f.o),'{}') into repeated from(select ordinality o,
  row_number()over(partition by value->>'key' order by ordinality)>1 r from jsonb_array_elements(g->'pools') with ordinality)f;
 i:=0;
 for p in select value from jsonb_array_elements(g->'pools') loop
  i:=i+1;
  perform cp7_wip.fields(p,array['key','size_id','input_pcs','origin','ownership','refs']);
  k:=cp7_wip.key(p->'key');perform cp7_wip.key(p->'size_id');perform cp7_wip.refs(p->'refs');
  qty:=cp7_wip.pcs(p->'input_pcs');
  if repeated[i] or p->>'origin' not in ('CUTTING','OPENING','NON_PO') or p->>'ownership' not in ('COMPANY','CUSTOMER')
    or p->>'origin' is null or p->>'ownership' is null then
   raise exception using errcode='22023',message='CP7_WIP_POOL';
  end if;
 end loop;
 select coalesce(jsonb_object_agg(value->>'key',value),'{}'),coalesce(jsonb_object_agg(value->>'key',ordinality),'{}')
  into pools,at_pool from jsonb_array_elements(g->'pools') with ordinality;
 inputs:=array_fill(0::numeric,array[i]);
 select coalesce(array_agg(f.r order by f.o),'{}') into repeated from(select ordinality o,
  row_number()over(partition by value->>'key' order by ordinality)>1 r from jsonb_array_elements(g->'nodes') with ordinality)f;
 i:=0;
 for n in select value from jsonb_array_elements(g->'nodes') loop
  i:=i+1;
  perform cp7_wip.fields(n,array['key','pool_key','stage','refs']);
  k:=cp7_wip.key(n->'key');pool:=cp7_wip.key(n->'pool_key');perform cp7_wip.refs(n->'refs');
  if repeated[i] or not pools ? pool or n->>'stage' is null or not (n->>'stage'=any(stages)) then
   raise exception using errcode='22023',message='CP7_WIP_NODE';
  end if;
 end loop;
 select coalesce(jsonb_object_agg(value->>'key',value),'{}'),coalesce(jsonb_object_agg(value->>'key',ordinality),'{}')
  into nodes,at_node from jsonb_array_elements(g->'nodes') with ordinality;
 balances:=array_fill(0::numeric,array[i]);
 -- An event may reverse only an event seen before it; a reversed key is
 -- reversed at most once, by the first later event that names it.
 select coalesce(array_agg(f.r order by f.o),'{}'),coalesce(array_agg(f.v order by f.o),'{}') into repeated,reversed from(select ordinality o,
  row_number()over(partition by value->>'key' order by ordinality)>1 r,
  value->>'reverses_key' is not null and row_number()over(partition by value->>'reverses_key' order by ordinality)>1 v
  from jsonb_array_elements(g->'events') with ordinality)f;
 select coalesce(jsonb_object_agg(f.k,jsonb_build_array(f.o,f.value)),'{}') into events from(select distinct on(value->>'key')value->>'key' k,ordinality o,value
  from jsonb_array_elements(g->'events') with ordinality where value->>'key' is not null order by value->>'key',ordinality)f;
 i:=0;
 -- Ordinal is explicit normalized dependency order, not a guessed wall-clock order.
 for e in select value from jsonb_array_elements(g->'events') loop
  i:=i+1;
  perform cp7_wip.fields(e,array['key','pool_key','from_node','to_node','qty_pcs','ordinal','reverses_key','refs']);
  k:=cp7_wip.key(e->'key');pool:=cp7_wip.key(e->'pool_key');dst:=cp7_wip.key(e->'to_node');
  perform cp7_wip.refs(e->'refs');qty:=cp7_wip.pcs(e->'qty_pcs');ord:=cp7_wip.pcs(e->'ordinal');
  if repeated[i] or not pools ? pool or qty=0 or ord<=last_ord then
   raise exception using errcode='22023',message='CP7_WIP_EVENT';
  end if;
  last_ord:=ord;src:=null;
  if e->'from_node'<>'null'::jsonb then src:=cp7_wip.key(e->'from_node');end if;
  dest:=nodes->dst;
  if dest is null or dest->>'pool_key'<>pool or src=dst then
   raise exception using errcode='22023',message='CP7_WIP_LINEAGE';
  end if;
  if e->'reverses_key'<>'null'::jsonb then
   old:=events->cp7_wip.key(e->'reverses_key');
   old:=case when (old->>0)::integer<i then old->1 end;
   if old is null or reversed[i] or old->'reverses_key'<>'null'::jsonb
     or old->'from_node'='null'::jsonb or old->>'pool_key'<>pool or old->>'from_node'<>dst
     or old->>'to_node' is distinct from src or cp7_wip.pcs(old->'qty_pcs')<>qty then
    raise exception using errcode='22023',message='CP7_WIP_REVERSAL';
   end if;
  end if;
  if src is null then
   if e->'reverses_key'<>'null'::jsonb then raise exception 'CP7_WIP_REVERSAL';end if;
   j:=(at_pool->>pool)::integer;val:=inputs[j]+qty;
   if val>cp7_wip.pcs(pools->pool->'input_pcs') then
    return jsonb_build_object('status','CONFLICT','reason','INPUT_EXCEEDS_ORIGIN','pool_key',pool,'event_key',k,'snapshot_id',g->'snapshot_id');
   end if;
   inputs[j]:=val;
  else
   node:=nodes->src;
   if node is null or node->>'pool_key'<>pool then raise exception 'CP7_WIP_LINEAGE';end if;
   j:=(at_node->>src)::integer;val:=balances[j]-qty;
   if val<0 then
    return jsonb_build_object('status','CONFLICT','reason','NEGATIVE_PREFIX','pool_key',pool,'event_key',k,'snapshot_id',g->'snapshot_id');
   end if;
   balances[j]:=val;
  end if;
  j:=(at_node->>dst)::integer;val:=balances[j]+qty;balances[j]:=val;
 end loop;
 -- Pools in key order, each with its own nodes in key order: one sort of the
 -- nodes by (pool key, node key) walked alongside the sorted pools.
 select coalesce(array_agg(value order by value->>'pool_key',value->>'key'),'{}') into ordered from jsonb_array_elements(g->'nodes');
 for p in select value from jsonb_array_elements(g->'pools') order by value->>'key' loop
  pool:=p->>'key';total:=0;wip:=0;fg:=0;bs:=0;withheld:=0;exited:=0;
  if inputs[(at_pool->>pool)::integer]<>cp7_wip.pcs(p->'input_pcs') then
   return jsonb_build_object('status','UNKNOWN','reason','ORIGIN_NOT_FULLY_ACCOUNTED','pool_key',pool,'snapshot_id',g->'snapshot_id');
  end if;
  while o<=cardinality(ordered) and ordered[o]->>'pool_key'=pool loop
   n:=ordered[o];o:=o+1;
   k:=n->>'key';qty:=balances[(at_node->>k)::integer];total:=total+qty;
   if n->>'stage'=any(wip_stages) then wip:=wip+qty;
   elsif n->>'stage'='FG' then fg:=fg+qty;
   elsif n->>'stage'='BS' then bs:=bs+qty;
   elsif n->>'stage'='EXIT' then exited:=exited+qty;
   else withheld:=withheld+qty;end if;
   -- Zero positions are retained as explicit evidence, never new supply.
   outputs:=array_append(outputs,n||jsonb_build_object('size_id',p->'size_id',
    'ownership',p->'ownership','remaining_pcs',qty::text,
    'quantity_quality','KNOWN','eligible_company_wip',p->>'ownership'='COMPANY' and n->>'stage'=any(wip_stages)));
  end loop;
  if total<>cp7_wip.pcs(p->'input_pcs') then raise exception 'CP7_WIP_CONSERVATION';end if;
  totals:=array_append(totals,jsonb_build_object('pool_key',pool,'size_id',p->'size_id',
   'ownership',p->'ownership','input_pcs',p->'input_pcs','wip_pcs',wip::text,'fg_pcs',fg::text,
   'bs_pcs',bs::text,'withheld_pcs',withheld::text,'exited_pcs',exited::text,'refs',p->'refs'));
 end loop;
 return jsonb_build_object('contract_version','cp7.wip-position.v1','status','COMPLETE',
  'snapshot_id',g->'snapshot_id','positions',to_jsonb(outputs),'totals',to_jsonb(totals),
  'scope','NORMALIZED_LINEAGE_ONLY','production_go',false);
end $$;
