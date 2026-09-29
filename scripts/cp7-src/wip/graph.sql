-- A conserved pool is original company/customer input of one exact size.
-- Nodes are positions of that same input, never additional supplies.
-- This kernel accepts normalized facts, not untrusted operational commands.
create function cp7_wip.reconcile(g jsonb) returns jsonb
language plpgsql immutable security invoker set search_path='' as $$
declare
 p jsonb; n jsonb; e jsonb; old jsonb; node jsonb; dest jsonb;
 pools jsonb:='{}'; nodes jsonb:='{}'; events jsonb:='{}'; reversed jsonb:='{}';
 balances jsonb:='{}'; inputs jsonb:='{}'; outputs jsonb:='[]'; totals jsonb:='[]';
 k text; pool text; src text; dst text; ord numeric; last_ord numeric:=-1;
 qty numeric; val numeric; total numeric; wip numeric; fg numeric; bs numeric; withheld numeric; exited numeric;
 stages constant text[]:=array['CUT_UNASSIGNED','SEWING_ACTIVE','SEWING_UNRESOLVED',
  'LAUNDRY_OUTSTANDING','AWAIT_QC','FG','BS','MISSING','STUCK','HOLD','REWORK','REWASH','EXIT'];
 wip_stages constant text[]:=array['CUT_UNASSIGNED','SEWING_ACTIVE','SEWING_UNRESOLVED',
  'LAUNDRY_OUTSTANDING','AWAIT_QC','REWORK','REWASH'];
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
 for p in select value from jsonb_array_elements(g->'pools') loop
  perform cp7_wip.fields(p,array['key','size_id','input_pcs','origin','ownership','refs']);
  k:=cp7_wip.key(p->'key');perform cp7_wip.key(p->'size_id');perform cp7_wip.refs(p->'refs');
  qty:=cp7_wip.pcs(p->'input_pcs');
  if pools ? k or p->>'origin' not in ('CUTTING','OPENING','NON_PO') or p->>'ownership' not in ('COMPANY','CUSTOMER')
    or p->>'origin' is null or p->>'ownership' is null then
   raise exception using errcode='22023',message='CP7_WIP_POOL';
  end if;
  pools:=pools||jsonb_build_object(k,p);inputs:=inputs||jsonb_build_object(k,0);
 end loop;
 for n in select value from jsonb_array_elements(g->'nodes') loop
  perform cp7_wip.fields(n,array['key','pool_key','stage','refs']);
  k:=cp7_wip.key(n->'key');pool:=cp7_wip.key(n->'pool_key');perform cp7_wip.refs(n->'refs');
  if nodes ? k or not pools ? pool or n->>'stage' is null or not (n->>'stage'=any(stages)) then
   raise exception using errcode='22023',message='CP7_WIP_NODE';
  end if;
  nodes:=nodes||jsonb_build_object(k,n);balances:=balances||jsonb_build_object(k,0);
 end loop;
 -- Ordinal is explicit normalized dependency order, not a guessed wall-clock order.
 for e in select value from jsonb_array_elements(g->'events') loop
  perform cp7_wip.fields(e,array['key','pool_key','from_node','to_node','qty_pcs','ordinal','reverses_key','refs']);
  k:=cp7_wip.key(e->'key');pool:=cp7_wip.key(e->'pool_key');dst:=cp7_wip.key(e->'to_node');
  perform cp7_wip.refs(e->'refs');qty:=cp7_wip.pcs(e->'qty_pcs');ord:=cp7_wip.pcs(e->'ordinal');
  if events ? k or not pools ? pool or qty=0 or ord<=last_ord then
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
   if old is null or reversed ? (e->>'reverses_key') or old->'reverses_key'<>'null'::jsonb
     or old->'from_node'='null'::jsonb or old->>'pool_key'<>pool or old->>'from_node'<>dst
     or old->>'to_node' is distinct from src or cp7_wip.pcs(old->'qty_pcs')<>qty then
    raise exception using errcode='22023',message='CP7_WIP_REVERSAL';
   end if;
   reversed:=reversed||jsonb_build_object(e->>'reverses_key',true);
  end if;
  if src is null then
   if e->'reverses_key'<>'null'::jsonb then raise exception 'CP7_WIP_REVERSAL';end if;
   val:=(inputs->>pool)::numeric+qty;
   if val>cp7_wip.pcs(pools->pool->'input_pcs') then
    return jsonb_build_object('status','CONFLICT','reason','INPUT_EXCEEDS_ORIGIN','pool_key',pool,'event_key',k,'snapshot_id',g->'snapshot_id');
   end if;
   inputs:=inputs||jsonb_build_object(pool,val);
  else
   node:=nodes->src;
   if node is null or node->>'pool_key'<>pool then raise exception 'CP7_WIP_LINEAGE';end if;
   val:=(balances->>src)::numeric-qty;
   if val<0 then
    return jsonb_build_object('status','CONFLICT','reason','NEGATIVE_PREFIX','pool_key',pool,'event_key',k,'snapshot_id',g->'snapshot_id');
   end if;
   balances:=balances||jsonb_build_object(src,val);
  end if;
  balances:=balances||jsonb_build_object(dst,(balances->>dst)::numeric+qty);
  events:=events||jsonb_build_object(k,e);
 end loop;
 for p in select value from jsonb_each(pools) order by key loop
  pool:=p->>'key';total:=0;wip:=0;fg:=0;bs:=0;withheld:=0;exited:=0;
  if (inputs->>pool)::numeric<>cp7_wip.pcs(p->'input_pcs') then
   return jsonb_build_object('status','UNKNOWN','reason','ORIGIN_NOT_FULLY_ACCOUNTED','pool_key',pool,'snapshot_id',g->'snapshot_id');
  end if;
  for n in select value from jsonb_each(nodes) where value->>'pool_key'=pool order by key loop
   k:=n->>'key';qty:=(balances->>k)::numeric;total:=total+qty;
   if n->>'stage'=any(wip_stages) then wip:=wip+qty;
   elsif n->>'stage'='FG' then fg:=fg+qty;
   elsif n->>'stage'='BS' then bs:=bs+qty;
   elsif n->>'stage'='EXIT' then exited:=exited+qty;
   else withheld:=withheld+qty;end if;
   -- Zero positions are retained as explicit evidence, never new supply.
   outputs:=outputs||jsonb_build_array(n||jsonb_build_object('size_id',p->'size_id',
    'ownership',p->'ownership','remaining_pcs',qty::text,
    'quantity_quality','KNOWN','eligible_company_wip',p->>'ownership'='COMPANY' and n->>'stage'=any(wip_stages)));
  end loop;
  if total<>cp7_wip.pcs(p->'input_pcs') then raise exception 'CP7_WIP_CONSERVATION';end if;
  totals:=totals||jsonb_build_array(jsonb_build_object('pool_key',pool,'size_id',p->'size_id',
   'ownership',p->'ownership','input_pcs',p->'input_pcs','wip_pcs',wip::text,'fg_pcs',fg::text,
   'bs_pcs',bs::text,'withheld_pcs',withheld::text,'exited_pcs',exited::text,'refs',p->'refs'));
 end loop;
 return jsonb_build_object('contract_version','cp7.wip-position.v1','status','COMPLETE',
  'snapshot_id',g->'snapshot_id','positions',outputs,'totals',totals,
  'scope','NORMALIZED_LINEAGE_ONLY','production_go',false);
end $$;
