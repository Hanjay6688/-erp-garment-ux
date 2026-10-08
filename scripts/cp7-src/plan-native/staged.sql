-- Production plan v2 from a staged analysis snapshot (snapshot contract v2 §2-§3,
-- owner decision 8 Oct 2026). A plan may be drafted and saved from a snapshot
-- that is no longer current; the snapshot values it was made from are stored
-- with it, labelled "data per <time>". Preview and apply re-read, in their own
-- transaction, the product, the production policy, the finished stock and the
-- WIP of the target, the material of the selected rolls, other plans and the
-- caller's access, and apply refuses with a stated reason (40001, numbers in
-- DETAIL) when the plan is no longer valid. Version 1 (one whole Original) is
-- unchanged; both versions share drafts, intents, commands and every lock key.

create table cp7_plan_native.staged_drafts(
 draft_id uuid primary key references cp7_plan_native.drafts(id),job_id uuid not null,run_id uuid not null,
 identity_hash text not null check(identity_hash~'^[0-9a-f]{64}$'),data_as_of timestamptz not null,snapshot jsonb not null,
 recorded_at timestamptz not null default clock_timestamp());
alter table cp7_plan_native.staged_drafts owner to cp7_plan_writer;
alter table cp7_plan_native.staged_drafts enable row level security;
create policy plan_staged_drafts_private on cp7_plan_native.staged_drafts for all to public using(false)with check(false);
revoke all on cp7_plan_native.staged_drafts from public,anon,authenticated,service_role;
create trigger immutable_plan_staged_draft before update or delete on cp7_plan_native.staged_drafts for each row execute function cp7_private.immutable_run();

-- Private capability into one target of the caller's own finished staged run:
-- its retained index row, the run's planning scope, the page that shows it and
-- the capture boundary. Whether the snapshot is still current is not required
-- (the plan states its time; preview and apply re-read the live facts).
create function cp7_plan_native.staged_source(p_run uuid,p_target text)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;j cp7_analysis_stage.jobs%rowtype;s cp7_analysis_stage.page_sets%rowtype;m cp7_analysis_stage.capture_marks%rowtype;t jsonb;
begin
 a:=cp7_private.access_now();
 select *into j from cp7_analysis_stage.jobs x where x.run_id=p_run and x.actor=(a->>'actor')::uuid and x.state='DONE';
 select *into s from cp7_analysis_stage.page_sets x where x.run_id=p_run;
 if j.id is null or s.run_id is null then raise exception using errcode='42501',message='CP7_PLAN_V2_SNAPSHOT_UNAVAILABLE';end if;
 select *into m from cp7_analysis_stage.capture_marks x where x.job_id=j.id;
 if m.job_id is null then raise exception 'CP7_PLAN_V2_SNAPSHOT_INDEX_MISSING';end if;
 t:=cp7_analysis_stage.plan_target(j.id,p_target);
 if cp7_private.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_PLAN_ACCESS_CHANGED';end if;
 return jsonb_build_object('run_id',p_run,'job_id',j.id,'identity_hash',s.identity_hash,'data_as_of',j.captured_at,'source_hash',j.source_hash,
  'capture_snapshot',m.source_snapshot::text,'ord',t->'ord','page_index',t->'page_index','row',t->'row','scope',t->'scope');
end $$;

-- The same target read live, under one clock: its current product row(s), the
-- production policy the analysis would resolve for it now (first current SKU
-- row whose members hold the root, as the netting does), its sellable finished
-- stock (grade A and B, as the analysis counts it) and the company WIP still
-- in the cut pools of its model and size: every posted group of the model not
-- proven exhausted at the snapshot, normalised in batches of 50 exactly as the
-- analysis captures them. More than 200 such groups, or a batch that does not
-- normalise COMPLETE, leaves the WIP unknown (apply refuses; never guessed).
-- Also, for the plan checks, the analysis state of every group linked to this
-- target and the linked groups posted outside the snapshot's scope.
create function cp7_plan_native.staged_live(p_run uuid,p_target text)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;j uuid;t jsonb;clk timestamptz:=clock_timestamp();root uuid;size uuid;model uuid;products jsonb;skus uuid[];policy jsonb;
 fg numeric;ids uuid[];n integer;bi integer:=1;part jsonb;norm jsonb;wip numeric:=0;wip_status text:='COMPLETE';wip_reason text;linked jsonb;outside jsonb;
begin
 a:=cp7_private.access_now();
 select x.id into j from cp7_analysis_stage.jobs x where x.run_id=p_run and x.actor=(a->>'actor')::uuid and x.state='DONE';
 if j is null then raise exception using errcode='42501',message='CP7_PLAN_V2_SNAPSHOT_UNAVAILABLE';end if;
 if p_target!~'^[0-9a-f-]{36}:[0-9a-f-]{36}$'then raise exception 'CP7_PLAN_TARGET';end if;
 t:=cp7_analysis_stage.plan_target(j,p_target);
 root:=split_part(p_target,':',1)::uuid;size:=split_part(p_target,':',2)::uuid;
 select(x->>'model_id')::uuid into model from jsonb_array_elements(t#>'{row,products}')x
  where x->>'root_id'=root::text and x->>'size_id'=size::text limit 1;
 select coalesce(jsonb_agg(jsonb_build_object('id',p.id,'model_id',p.model_id,'size_id',p.size_id,'is_active',p.is_active,
   'sku',p.sku,'product_name',p.product_name)order by p.id),'[]'::jsonb)into products
  from erp.products p where coalesce(p.identity_root_id,p.id)=root and p.effective_from<=clk and(p.effective_to is null or p.effective_to>clk);
 select coalesce(array_agg(distinct v.sku_id order by v.sku_id),'{}'::uuid[])into skus
  from erp.bf_sku_members_v1 m join erp.bf_sku_versions_v1 v on v.id=m.version_id
  where m.product_root=root and v.effective_from<=clk and(v.effective_to is null or v.effective_to>clk);
 select x.v into policy from jsonb_array_elements(cp7_identity.workspace_data(skus,clk)->'rows')with ordinality x(v,o)
  where jsonb_typeof(x.v->'members')='array'and(x.v->'members')?root::text order by x.o limit 1;
 select coalesce(sum(m.qty_signed),0)into fg from erp.fg_stock_movements m join erp.products p on p.id=m.product_id
  where coalesce(p.identity_root_id,p.id)=root and m.quality_grade in('GRADE_A','GRADE_B')and m.physical_at<=clk and m.system_created_at<=clk;
 if model is null then wip_status:='UNKNOWN';wip_reason:='SNAPSHOT_MODEL_UNKNOWN';
 else
  select coalesce(array_agg(x.id order by x.id),'{}'::uuid[]),count(*)into ids,n from(
   select g.id from erp.cutting_groups g join erp.production_orders po on po.id=g.po_id
   where po.model_id=model and g.material_issue_posted and g.cut_at<=clk
    and not exists(select 1 from cp7_analysis_stage.plan_groups x where x.job_id=j and x.group_id=g.id::text and x.scope='EXHAUSTED')
   order by g.id limit 201)x;
  if n>200 then wip_status:='UNKNOWN';wip_reason:='MODEL_WIP_GROUP_LIMIT';end if;
  while wip_status='COMPLETE'and bi<=n loop
   part:=cp7_wip.capture_cutting_sources(ids[bi:least(bi+49,n)],clk);
   if part->>'status'is distinct from 'COMPLETE'then wip_status:='UNKNOWN';wip_reason:='WIP_SOURCE_INCOMPLETE';exit;end if;
   begin norm:=cp7_wip.normalize_cutting(part);
   exception when others then norm:=jsonb_build_object('status','UNKNOWN','reason','WIP_NORMALIZATION_REFUSED');
   end;
   if norm->>'status'is distinct from 'COMPLETE'then wip_status:='UNKNOWN';wip_reason:=coalesce(norm->>'reason','WIP_NOT_COMPLETE');exit;end if;
   wip:=wip+(select coalesce(sum((x->>'wip_pcs')::numeric),0)from jsonb_array_elements(norm->'totals')x
    where x->>'pool_key'like 'CUT:%'and x->>'ownership'='COMPANY'and x->>'size_id'=size::text);
   bi:=bi+50;
  end loop;
 end if;
 select coalesce(jsonb_agg(jsonb_build_object('intent_id',i.id,'group_id',i.cutting_group_id,'group_exists',g.id is not null,
   'posted',g.material_issue_posted,'scope',x.scope,'unproven',x.unproven)order by i.id),'[]'::jsonb)into linked
  from cp7_plan_native.intents i left join erp.cutting_groups g on g.id=i.cutting_group_id
  left join cp7_analysis_stage.plan_groups x on x.job_id=j and x.group_id=i.cutting_group_id::text where i.target_key=p_target;
 select coalesce(jsonb_agg(i.cutting_group_id::text order by i.cutting_group_id),'[]'::jsonb)into outside
  from cp7_plan_native.intents i join erp.cutting_groups g on g.id=i.cutting_group_id
  where g.material_issue_posted and not exists(select 1 from cp7_analysis_stage.plan_groups x where x.job_id=j and x.group_id=i.cutting_group_id::text);
 if cp7_private.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_PLAN_ACCESS_CHANGED';end if;
 return jsonb_build_object('checked_at',clk,'products',products,'policy',policy,'fg_pcs',fg::text,
  'wip',jsonb_build_object('status',wip_status,'reason',wip_reason,'pcs',case when wip_status='COMPLETE'then wip::text end,
   'model_id',model,'size_id',size,'groups',n),'linked',linked,'posted_outside_snapshot',outside);
end $$;

-- Whether a row was recorded after a snapshot boundary: recorded later, or
-- written by a transaction the capture's snapshot did not see (in flight then).
-- The 32-bit xmin maps to the full id in the 2^32 window ending at this
-- statement's snapshot, as the change counts do (analysis-stage-snapshot.sql).
create function cp7_plan_native.after_snapshot(p_xmin xid,p_recorded timestamptz,p_since timestamptz,p_snap pg_snapshot)returns boolean
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select p_recorded>=p_since or(p_snap is not null and not pg_visible_in_snapshot(
  (case when p_xmin::text::bigint<=r.ref%4294967296 then r.ref-r.ref%4294967296 else greatest(r.ref-r.ref%4294967296-4294967296,0)end
   +p_xmin::text::bigint)::text::xid8,p_snap))
 from(select pg_snapshot_xmax(pg_current_snapshot())::text::bigint ref)r
$$;

-- One check of a v2 plan. SAVE: the snapshot conditions (the same as v1's,
-- over the retained index), the reviewed assumptions of this target and the
-- Native composition as v1 checks it. PREVIEW and APPLY add the live recheck:
-- need_now = need at the snapshot minus any increase of (finished stock + WIP
-- of the model and size) since the snapshot (taken together, so WIP that
-- became finished stock is not counted twice; a decrease never adds to the
-- plan); the cut limit at the same yield; the capacity left after every other
-- plan not already in the snapshot's load. APPLY raises the first refusal;
-- PREVIEW reports every verdict and writes nothing.
create function cp7_plan_native.preflight_v2(p jsonb,p_mode text,p_draft uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare s jsonb;r jsonb;sc jsonb;product jsonb;products jsonb;cut jsonb;slot jsonb;roll jsonb;y jsonb;
 po erp.production_orders%rowtype;pattern erp.production_patterns%rowtype;native_roll erp.material_rolls%rowtype;
 target text;size uuid;total numeric:=0;roll_total numeric;issued numeric;consumed numeric;remaining numeric;available numeric;
 gap numeric;capacity numeric;seen uuid[]:='{}';material_rows jsonb:='[]';assumptions jsonb;native_payload jsonb;pool jsonb;
 estimate jsonb;history jsonb;yield_basis text;num numeric;den numeric;cut_limit numeric;good numeric;
 snap jsonb;live jsonb;l jsonb;since timestamptz;boundary pg_snapshot;fg_snap numeric;wip_snap numeric;fg_now numeric;wip_now numeric;
 increase numeric;need_now numeric;cut_limit_now numeric;used numeric;capacity_now numeric;through timestamptz;
 verdicts jsonb:='[]';code text;first_code text;detail jsonb;planned boolean;conflict boolean;live_product jsonb;
begin
 if p_mode not in('SAVE','PREVIEW','APPLY')then raise exception 'CP7_PLAN_V2_MODE';end if;
 perform cp7_plan_native.fields(p,array['run_id','target_key','plan_id','expected_revision','identity_hash','cutting','reviewed_assumption_ids','reason']
  ||case when p?'new_start_yield'then array['new_start_yield']else'{}'::text[]end);
 if jsonb_typeof(p->'run_id')<>'string'or jsonb_typeof(p->'target_key')<>'string'or jsonb_typeof(p->'identity_hash')<>'string'
  or p->>'identity_hash'!~'^[0-9a-f]{64}$'or jsonb_typeof(p->'reason')<>'string'or length(btrim(p->>'reason'))not between 1 and 1000
  or jsonb_typeof(p->'reviewed_assumption_ids')is distinct from'array'then raise exception 'CP7_PLAN_REVIEW';end if;
 target:=p->>'target_key';s:=cp7_plan_native.staged_source((p->>'run_id')::uuid,target);
 if p->>'identity_hash'<>s->>'identity_hash'then raise exception 'CP7_PLAN_REVIEW';end if;
 r:=s->'row';sc:=s->'scope';
 select coalesce(jsonb_agg(x),'[]'::jsonb)into products from jsonb_array_elements(r->'products')x where(x->>'root_id')||':'||(x->>'size_id')=target;
 if jsonb_array_length(products)<>1 then raise exception 'CP7_PLAN_TARGET';end if;product:=products->0;
 if product->'is_active'is distinct from'true'::jsonb or r->'production_policy'->'policy'->>'state'is distinct from'ACTIVE'then raise exception 'CP7_PLAN_PRODUCTION_DISABLED';end if;
 if r->>'conditional_gap_pcs'is null or sc->>'alloc_status'is distinct from'SCENARIO'
  or sc->'capacity'->>'status'is distinct from'SCENARIO'then raise exception 'CP7_PLAN_FEASIBILITY_UNKNOWN';end if;
 gap:=(r->>'conditional_gap_pcs')::numeric;capacity:=(sc->'capacity'->>'capacity_pcs')::numeric;
 if gap<=0 or capacity is null then raise exception 'CP7_PLAN_NO_NEW_NEED';end if;
 -- The assumptions this target's numbers rest on: the run's global ones
 -- (the selected schedule), the target's demand profile and its fabric needs.
 select coalesce(jsonb_agg(distinct x->'id'),'[]'::jsonb)into assumptions
  from jsonb_array_elements(coalesce(sc->'assumptions','[]')||coalesce(r->'assumptions','[]')||coalesce(r->'fabric_assumptions','[]'))x
  where jsonb_typeof(x->'id')='string';
 estimate:=coalesce(p->'new_start_yield','null'::jsonb);history:=cp7_plan_native.history_yield(target);
 if estimate<>'null'::jsonb then
  perform cp7_plan_native.fields(estimate,array['numerator','denominator']);
  if jsonb_typeof(estimate->'numerator')<>'string'or jsonb_typeof(estimate->'denominator')<>'string'
   or estimate->>'numerator'!~'^[1-9][0-9]{0,5}$'or estimate->>'denominator'!~'^[1-9][0-9]{0,5}$'
   or(estimate->>'numerator')::numeric>(estimate->>'denominator')::numeric then raise exception 'CP7_PLAN_NEW_START_YIELD';end if;
  if history->>'status'='AVAILABLE'then raise exception 'CP7_PLAN_NEW_START_YIELD_HISTORY_AVAILABLE';end if;
  assumptions:=assumptions||jsonb_build_array('PLAN_NEW_START_YIELD');
 end if;
 if exists(select 1 from jsonb_array_elements(p->'reviewed_assumption_ids')x where jsonb_typeof(x)<>'string')
  or(select count(distinct value)from jsonb_array_elements(p->'reviewed_assumption_ids'))<>jsonb_array_length(p->'reviewed_assumption_ids')
  or not ((p->'reviewed_assumption_ids')@>assumptions)
  or not (assumptions@>(p->'reviewed_assumption_ids'))then raise exception 'CP7_PLAN_ASSUMPTIONS_NOT_REVIEWED';end if;
 -- The Native composition, checked as v1 checks it.
 cut:=p->'cutting';perform cp7_plan_native.fields(cut,array['po_id','pattern_id','source_location_id','cut_at','notes','size_slots','rolls']);
 select *into po from erp.production_orders where id=(cut->>'po_id')::uuid;
 select *into pattern from erp.production_patterns where id=(cut->>'pattern_id')::uuid;
 if po.id is null or po.status in('FINISHED','CANCELLED')or po.model_id::text is distinct from product->>'model_id'then raise exception 'CP7_PLAN_NATIVE_PO_MODEL';end if;
 if pattern.id is null or not pattern.is_active then raise exception 'CP7_PLAN_NATIVE_PATTERN';end if;
 if not exists(select 1 from erp.locations where id=(cut->>'source_location_id')::uuid and is_active and location_type='RAW_MATERIAL_WAREHOUSE')then raise exception 'CP7_PLAN_NATIVE_LOCATION';end if;
 if jsonb_typeof(cut->'cut_at')<>'string'or not isfinite((cut->>'cut_at')::timestamptz)or(cut->>'cut_at')::timestamptz>clock_timestamp()+interval'5 minutes'then raise exception 'CP7_PLAN_NATIVE_CUT_DATE';end if;
 if jsonb_typeof(cut->'size_slots')is distinct from'array'or jsonb_array_length(cut->'size_slots')<>1
  or jsonb_typeof(cut->'rolls')is distinct from'array'or jsonb_array_length(cut->'rolls')not between 1 and 100 then raise exception 'CP7_PLAN_NATIVE_COMPOSITION';end if;
 slot:=cut->'size_slots'->0;perform cp7_plan_native.fields(slot,array['slot_no','size_id','drawing_no']);size:=(product->>'size_id')::uuid;
 if slot->>'slot_no'<>'1'or(slot->>'size_id')::uuid<>size or cp7_plan_native.decimal(slot->'drawing_no',true)=0
  or not exists(select 1 from erp.sizes where id=size and is_active)
  or not exists(select 1 from erp.product_model_sizes where model_id=po.model_id and size_id=size)then raise exception 'CP7_PLAN_NATIVE_EXACT_SIZE';end if;
 for roll in select value from jsonb_array_elements(cut->'rolls')loop
  perform cp7_plan_native.fields(roll,array['roll_id','qty_issued','qty_consumed','qty_reported_remaining','yields']);
  select *into native_roll from erp.material_rolls where id=(roll->>'roll_id')::uuid;
  if native_roll.id is null or native_roll.id=any(seen)or native_roll.status not in('AVAILABLE','HALF_USED')then raise exception 'CP7_PLAN_NATIVE_ROLL';end if;
  seen:=array_append(seen,native_roll.id);issued:=cp7_plan_native.decimal(roll->'qty_issued');consumed:=cp7_plan_native.decimal(roll->'qty_consumed');remaining:=cp7_plan_native.decimal(roll->'qty_reported_remaining');
  if issued<=0 or consumed<=0 or consumed+remaining<>issued then raise exception 'CP7_PLAN_NATIVE_MATERIAL_RECONCILIATION';end if;
  pool:=cp7_plan_native.material_pool(native_roll.id,(cut->>'source_location_id')::uuid);
  available:=(pool->>'native_available')::numeric;
  if available<issued or not exists(select 1 from erp.materials where id=native_roll.material_id and is_active and material_type='FABRIC')then raise exception 'CP7_PLAN_NATIVE_MATERIAL_NOT_READY';end if;
  if pool->>'free_for_new_plan'is null or(pool->>'free_for_new_plan')::numeric<issued then raise exception using errcode='40001',message='CP7_PLAN_SHARED_MATERIAL_BUDGET_CHANGED';end if;
  if jsonb_typeof(roll->'yields')is distinct from'array'or jsonb_array_length(roll->'yields')<>1 then raise exception 'CP7_PLAN_NATIVE_EXACT_SIZE';end if;
  y:=roll->'yields'->0;perform cp7_plan_native.fields(y,array['slot_no','qty_pcs']);roll_total:=cp7_plan_native.decimal(y->'qty_pcs',true);
  if y->>'slot_no'<>'1'or roll_total<=0 then raise exception 'CP7_PLAN_NATIVE_EXACT_SIZE';end if;total:=total+roll_total;
  material_rows:=material_rows||jsonb_build_array(jsonb_build_object('roll_id',native_roll.id,'material_id',native_roll.material_id,
   'native_available',available::text,'linked_native_draft_qty',pool->'linked_native_draft_qty','free_for_new_plan',pool->'free_for_new_plan',
   'linked_native_drafts',pool->'linked_native_drafts','selected_issued',issued::text,'selected_consumption',consumed::text,'selected_remaining',remaining::text,
   'native_status',native_roll.status,'basis','OPERATOR_SELECTED_DRAFT_COMPOSITION_NOT_PROVEN_INSTALLED_OR_RESERVED'));
 end loop;
 if history->>'status'='AVAILABLE'then yield_basis:='HISTORY_NATIVE';num:=(history->>'numerator')::numeric;den:=(history->>'denominator')::numeric;
 elsif estimate<>'null'::jsonb then yield_basis:='PLAN_ESTIMATE_REVIEWED';num:=(estimate->>'numerator')::numeric;den:=(estimate->>'denominator')::numeric;
 else yield_basis:='UNKNOWN';end if;
 cut_limit:=case when yield_basis='UNKNOWN'then ceil(gap)else ceil(gap*den/num)end;
 good:=case when yield_basis='UNKNOWN'then null else floor(total*num/den)end;
 if total>cut_limit or total>capacity then raise exception 'CP7_PLAN_QUANTITY_EXCEEDS_NEED_OR_CAPACITY';end if;
 fg_snap:=(r->>'available_fg_pcs')::numeric;
 wip_snap:=case when sc->>'wip_status'='COMPLETE'then coalesce((sc->'wip_by_model_size'->>((product->>'model_id')||':'||size::text))::numeric,0)end;
 snap:=jsonb_build_object('need_pcs',gap::text,'available_fg_pcs',fg_snap::text,'wip_model_size_pcs',wip_snap::text,'wip_status',sc->'wip_status',
  'capacity_pcs',capacity::text,'capacity_through_at',sc#>'{capacity,inputs,through_at}','alloc_status',sc->'alloc_status',
  'production_state',r->'production_policy'->'policy'->'state','policy_revision',r->'production_policy'->'policy_revision',
  'sku_id',r->'production_policy'->'sku_id','root_id',product->'root_id','model_id',product->'model_id','size_id',product->'size_id',
  'sku',product->'sku','product_name',product->'product_name','schedule',sc->'schedule','assumption_ids',assumptions);
 if p_mode<>'SAVE'then
  live:=cp7_plan_native.staged_live((p->>'run_id')::uuid,target);
  since:=(s->>'data_as_of')::timestamptz;boundary:=(s->>'capture_snapshot')::pg_snapshot;
  -- Product: still exactly one current, active row of the same model and size.
  live_product:=case when jsonb_array_length(live->'products')=1 then live->'products'->0 end;
  code:=case when live_product is null or live_product->'is_active'is distinct from'true'::jsonb
   or live_product->>'size_id'<>size::text or live_product->>'model_id'<>product->>'model_id'then 'CP7_PLAN_V2_PRODUCT_CHANGED'end;
  verdicts:=verdicts||jsonb_build_array(jsonb_build_object('check','PRODUCT','status',case when code is null then 'OK'else'REFUSED'end,'code',code));
  first_code:=coalesce(first_code,code);
  code:=case when live->'policy'->'policy'->>'quality'is distinct from'KNOWN'or live->'policy'->'policy'->>'state'is distinct from'ACTIVE'
   then 'CP7_PLAN_V2_POLICY_CHANGED'end;
  verdicts:=verdicts||jsonb_build_array(jsonb_build_object('check','POLICY','status',case when code is null then 'OK'else'REFUSED'end,'code',code));
  first_code:=coalesce(first_code,code);
  -- Another plan of this target recorded after the snapshot: the snapshot's
  -- need did not know it.
  select exists(select 1 from cp7_plan_native.intents i where i.target_key=target and i.draft_id is distinct from p_draft
   and cp7_plan_native.after_snapshot(i.xmin,i.recorded_at,since,boundary))into planned;
  code:=case when planned then 'CP7_PLAN_V2_TARGET_PLANNED'end;
  verdicts:=verdicts||jsonb_build_array(jsonb_build_object('check','TARGET_PLANS','status',case when code is null then 'OK'else'REFUSED'end,'code',code));
  first_code:=coalesce(first_code,code);
  -- v1's linked-intent rule over the snapshot's own production scope: an
  -- earlier plan's group must be posted, in the scope, and not unproven.
  select exists(select 1 from cp7_plan_native.intents i join jsonb_array_elements(live->'linked')x on x->>'intent_id'=i.id::text
   where i.target_key=target and i.draft_id is distinct from p_draft and x->'group_exists'='true'::jsonb
    and not cp7_plan_native.after_snapshot(i.xmin,i.recorded_at,since,boundary)
    and(x->'posted'is distinct from'true'::jsonb or sc->>'wip_status'is distinct from'COMPLETE'or x->>'scope'is null or x->'unproven'='true'::jsonb))into conflict;
  code:=case when conflict then 'CP7_PLAN_LINKED_INTENT_CONFLICT'end;
  verdicts:=verdicts||jsonb_build_array(jsonb_build_object('check','LINKED_PLANS','status',case when code is null then 'OK'else'REFUSED'end,'code',code));
  first_code:=coalesce(first_code,code);
  code:=case when wip_snap is null or live->'wip'->>'status'is distinct from'COMPLETE'then 'CP7_PLAN_V2_WIP_UNKNOWN'end;
  verdicts:=verdicts||jsonb_build_array(jsonb_build_object('check','WIP','status',case when code is null then 'OK'else'REFUSED'end,'code',code,
   'reason',case when wip_snap is null then 'SNAPSHOT_WIP_NOT_COMPLETE'else live->'wip'->>'reason'end));
  first_code:=coalesce(first_code,code);
  fg_now:=(live->>'fg_pcs')::numeric;wip_now:=(live->'wip'->>'pcs')::numeric;
  if code is null then
   increase:=greatest(0,(fg_now+wip_now)-(fg_snap+wip_snap));need_now:=greatest(0,gap-increase);
   cut_limit_now:=case when yield_basis='UNKNOWN'then ceil(need_now)else ceil(need_now*den/num)end;
   code:=case when need_now=0 or total>cut_limit_now then 'CP7_PLAN_V2_NEED_CHANGED'end;
  else code:=null;end if;
  verdicts:=verdicts||jsonb_build_array(jsonb_build_object('check','NEED','status',case when need_now is null then 'UNKNOWN'when code is null then 'OK'else'REFUSED'end,'code',code));
  first_code:=coalesce(first_code,code);
  -- Capacity: one shared centre. Every other plan not already in the
  -- snapshot's load uses it: recorded after the snapshot, still a Native
  -- draft, or posted outside the snapshot's scope. A deleted draft uses none.
  with counted as materialized(select i.draft_id from cp7_plan_native.intents i join erp.cutting_groups g on g.id=i.cutting_group_id
    where i.draft_id is distinct from p_draft and(not g.material_issue_posted or(live->'posted_outside_snapshot')?(i.cutting_group_id::text)
     or cp7_plan_native.after_snapshot(i.xmin,i.recorded_at,since,boundary)))
  select coalesce(sum((yy.value->>'qty_pcs')::numeric),0)into used from counted c join cp7_plan_native.drafts d on d.id=c.draft_id
   cross join lateral jsonb_array_elements(d.payload#>'{cutting,rolls}')rr(value)cross join lateral jsonb_array_elements(rr.value->'yields')yy(value);
  capacity_now:=capacity-used;through:=(sc#>>'{capacity,inputs,through_at}')::timestamptz;
  code:=case when through is null or through<=(live->>'checked_at')::timestamptz then 'CP7_PLAN_V2_CAPACITY_EXPIRED'
   when total>capacity_now then 'CP7_PLAN_V2_CAPACITY_USED'end;
  verdicts:=verdicts||jsonb_build_array(jsonb_build_object('check','CAPACITY','status',case when code is null then 'OK'else'REFUSED'end,'code',code));
  first_code:=coalesce(first_code,code);
  l:=jsonb_build_object('checked_at',live->'checked_at','fg_now_pcs',fg_now::text,'fg_snapshot_pcs',fg_snap::text,
   'wip_now_pcs',wip_now::text,'wip_snapshot_pcs',wip_snap::text,'wip_status',live->'wip'->'status','wip_reason',live->'wip'->'reason',
   'increase_pcs',increase::text,'need_now_pcs',need_now::text,'cut_limit_now_pcs',cut_limit_now::text,'selected_new_pcs',total::text,
   'capacity_now_pcs',capacity_now::text,'capacity_used_by_other_plans_pcs',used::text,'capacity_through_at',through,
   'product',live_product,'policy_state',live->'policy'->'policy'->'state','policy_quality',live->'policy'->'policy'->'quality',
   'verdicts',verdicts,'apply_ready',first_code is null);
  if p_mode='APPLY'and first_code is not null then
   detail:=jsonb_build_object('code',first_code,'data_as_of',s->'data_as_of')||(l-'verdicts'-'product');
   raise exception using errcode='40001',message=first_code,detail=detail::text,hint='CP7_PLAN_V2_REVIEW_REQUIRED';
  end if;
 end if;
 native_payload:=cut||jsonb_build_object('action','SAVE_DRAFT','change_reason',btrim(p->>'reason'));
 return jsonb_build_object('contract_version','cp7.plan-preview-staged.v1','run_id',s->'run_id','identity_hash',s->'identity_hash',
  'data_as_of',s->'data_as_of','source_hash',s->'source_hash','job_id',s->'job_id','page_index',s->'page_index',
  'target_key',target,'product_sku',product->'sku','product_name',product->'product_name','snapshot',snap,
  'needed_pcs',gap::text,'selected_new_pcs',total::text,'free_capacity_pcs',capacity::text,
  'new_start_yield',jsonb_build_object('basis',yield_basis,'numerator',num::text,'denominator',den::text,
   'assumption_id',case when yield_basis='PLAN_ESTIMATE_REVIEWED'then'PLAN_NEW_START_YIELD'end,'history',history),
  'cut_limit_pcs',cut_limit::text,'cut_limit_basis',case when yield_basis='UNKNOWN'then'NEED_CAP_YIELD_UNKNOWN_NOT_ASSUMED_100_PERCENT'else'NEED_AT_STATED_YIELD'end,
  'expected_good_pcs',good::text,'rounding_extra_pcs',case when good is null then null else greatest(0,good-gap)::text end,
  'unresolved_pcs',case when good is null then null else greatest(0,gap-good)::text end,'material_rows',material_rows,'pattern_revision',pattern.revision,
  'composition_hash',encode(extensions.digest(convert_to(jsonb_build_object('po_id',po.id,'po_model',po.model_id,'po_status',po.status,'pattern_id',pattern.id,'pattern_version',pattern.row_version,'pattern_revision',pattern.revision,'material_rows',material_rows)::text,'UTF8'),'sha256'),'hex'),
  'native_payload',native_payload,'command','erp_save_cutting_group_before_sewing_v2:SAVE_DRAFT','live',l,
  'status',case when p_mode='SAVE'then 'SNAPSHOT_CHECKED_LIVE_RECHECK_AT_APPLY'when first_code is null then 'READY_FOR_EXPLICIT_NATIVE_DRAFT'else'REVIEW_REQUIRED'end,
  'reservation_created',false,'physical_production_confirmed',false,'production_go',false);
end $$;

create function cp7_plan_native.options_v2(q jsonb)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;s jsonb;p jsonb;r jsonb;sc jsonb;loc uuid;n integer;po_off integer;roll_off integer;pattern_off integer;
 po_q text;roll_q text;orders jsonb;patterns jsonb;rolls jsonb;locations jsonb;po_count bigint;pattern_count bigint;roll_count bigint;assumptions jsonb;
begin
 a:=cp7_plan_native.access_now('READ');perform cp7_plan_native.fields(q,array['run_id','target_key','location_id','po_query','roll_query','po_offset','roll_offset','pattern_offset','limit']);
 if jsonb_typeof(q->'run_id')<>'string'or jsonb_typeof(q->'target_key')<>'string'
  or jsonb_typeof(q->'po_query')<>'string'or jsonb_typeof(q->'roll_query')<>'string'or length(q->>'po_query')>200 or length(q->>'roll_query')>200 then raise exception 'CP7_PLAN_OPTIONS';end if;
 n:=cp7_plan_native.decimal(q->'limit',true);po_off:=cp7_plan_native.decimal(q->'po_offset',true);roll_off:=cp7_plan_native.decimal(q->'roll_offset',true);pattern_off:=cp7_plan_native.decimal(q->'pattern_offset',true);
 if n not between 1 and 50 or greatest(po_off,roll_off,pattern_off)>1000000 then raise exception 'CP7_PLAN_OPTIONS';end if;
 s:=cp7_plan_native.staged_source((q->>'run_id')::uuid,q->>'target_key');r:=s->'row';sc:=s->'scope';
 p:=(select x from jsonb_array_elements(r->'products')x where (x->>'root_id')||':'||(x->>'size_id')=q->>'target_key');
 if p is null then raise exception 'CP7_PLAN_TARGET';end if;
 select coalesce(jsonb_agg(x.e order by x.o),'[]'::jsonb)into assumptions from(select distinct on(e->>'id')e,o
  from jsonb_array_elements(coalesce(sc->'assumptions','[]')||coalesce(r->'assumptions','[]')||coalesce(r->'fabric_assumptions','[]'))with ordinality y(e,o)
  where jsonb_typeof(e->'id')='string'order by e->>'id',o)x;
 loc:=(q->>'location_id')::uuid;po_q:=lower(btrim(q->>'po_query'));roll_q:=lower(btrim(q->>'roll_query'));
 if loc is not null and not exists(select 1 from erp.locations where id=loc and is_active and location_type='RAW_MATERIAL_WAREHOUSE')then raise exception 'CP7_PLAN_NATIVE_LOCATION';end if;
 select count(*)into po_count from erp.production_orders x where x.model_id=(p->>'model_id')::uuid and x.status not in('FINISHED','CANCELLED')and(po_q=''or strpos(lower(x.po_number),po_q)>0);
 select coalesce(jsonb_agg(jsonb_build_object('id',id,'number',po_number,'model_id',model_id)order by po_number,id),'[]')into orders from(select x.id,x.po_number,x.model_id from erp.production_orders x where x.model_id=(p->>'model_id')::uuid and x.status not in('FINISHED','CANCELLED')and(po_q=''or strpos(lower(x.po_number),po_q)>0)order by x.po_number,x.id limit n offset po_off)x;
 select count(*)into pattern_count from erp.production_patterns where is_active;
 select coalesce(jsonb_agg(jsonb_build_object('id',id,'code',pattern_code,'name',pattern_name,'revision',revision)order by pattern_code,revision,id),'[]')into patterns from(select *from erp.production_patterns where is_active order by pattern_code,revision,id limit n offset pattern_off)x;
 with balances as(select x.id,x.roll_number,x.material_id,m.material_name,m.unit_code,coalesce(sum(sm.qty_signed),0)qty
  from erp.material_rolls x join erp.materials m on m.id=x.material_id
  left join erp.material_stock_movements sm on sm.roll_id=x.id and sm.location_id=loc and sm.physical_at<=clock_timestamp()
  where loc is not null and x.status in('AVAILABLE','HALF_USED')and m.is_active and m.material_type='FABRIC'
   and(roll_q=''or strpos(lower(x.roll_number||' '||m.material_name),roll_q)>0)
  group by x.id,x.roll_number,x.material_id,m.material_name,m.unit_code having coalesce(sum(sm.qty_signed),0)>0),
 paged as(select *from balances order by roll_number,id limit n offset roll_off)
 select(select count(*)from balances),coalesce(jsonb_agg(jsonb_build_object('id',id,'number',roll_number,'material_id',material_id,'material_name',material_name,'unit',unit_code,'available',pool->'native_available',
  'linked_native_draft_qty',pool->'linked_native_draft_qty','free_for_new_plan',pool->'free_for_new_plan')order by roll_number,id),'[]')into roll_count,rolls
 from paged cross join lateral(select cp7_plan_native.material_pool(id,loc)pool)budget;
 select coalesce(jsonb_agg(jsonb_build_object('id',id,'name',location_name)order by location_name,id),'[]')into locations from erp.locations where is_active and location_type='RAW_MATERIAL_WAREHOUSE';
 if jsonb_array_length(locations)>1000 then raise exception 'CP7_PLAN_OPTIONS_LOCATION_LIMIT';end if;
 if cp7_plan_native.access_now('READ')is distinct from a then raise exception using errcode='42501',message='CP7_PLAN_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.plan-options-staged.v1','actor_scope_id',a->>'actor','run_id',q->'run_id','target_key',q->'target_key',
  'identity_hash',s->'identity_hash','data_as_of',s->'data_as_of','page_index',s->'page_index',
  'model_id',p->'model_id','size_id',p->'size_id','product_sku',p->'sku','product_name',p->'product_name',
  'needed_pcs',r->'conditional_gap_pcs','available_fg_pcs',r->'available_fg_pcs','capacity_pcs',sc->'capacity'->'capacity_pcs',
  'production_state',r->'production_policy'->'policy'->'state','assumptions',assumptions,'location_id',loc,'orders',orders,'patterns',patterns,'rolls',rolls,'locations',locations,
  'page',jsonb_build_object('limit',n,'po_offset',po_off,'po_total',po_count::text,'pattern_offset',pattern_off,'pattern_total',pattern_count::text,'roll_offset',roll_off,'roll_total',roll_count::text),
  'live_recheck','AT_PREVIEW_AND_APPLY','reservation_created',false,'production_go',false);
end $$;

create function cp7_plan_native.save_v2(p jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;r cp7_plan_native.drafts%rowtype;sd cp7_plan_native.staged_drafts%rowtype;preview jsonb;plan uuid;revision bigint;expected bigint;
begin
 a:=cp7_plan_native.access_now('DRAFT');if p_request is null then raise exception 'CP7_PLAN_REQUEST';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:PLAN_SAVE:'||(a->>'actor')||':'||p_request::text,0));
 if cp7_plan_native.access_now('DRAFT')is distinct from a then raise exception using errcode='42501',message='CP7_PLAN_ACCESS_CHANGED';end if;
 select *into r from cp7_plan_native.drafts where actor=(a->>'actor')::uuid and request_id=p_request;
 if found then
  select *into sd from cp7_plan_native.staged_drafts where draft_id=r.id;
  if r.payload<>p or sd.draft_id is null then raise exception 'CP7_PLAN_REQUEST_CHANGED';end if;
  return jsonb_build_object('contract_version','cp7.plan-draft.v2','actor_scope_id',a->>'actor','draft_id',r.id,'plan_id',r.plan_id,'revision',r.revision::text,
   'run_id',r.run_id,'target_key',r.target_key,'identity_hash',sd.identity_hash,'data_as_of',sd.data_as_of,'request_id',p_request,'state','SAVED',
   'reservation_created',false,'production_go',false);
 end if;
 perform cp7_plan_native.fields(p,array['run_id','target_key','plan_id','expected_revision','identity_hash','cutting','reviewed_assumption_ids','reason']
  ||case when p?'new_start_yield'then array['new_start_yield']else'{}'::text[]end);
 if p->'plan_id'='null'::jsonb then
  if p->'expected_revision'<>'null'::jsonb then raise exception 'CP7_PLAN_REVISION';end if;plan:=gen_random_uuid();revision:=1;
 else
  if jsonb_typeof(p->'plan_id')<>'string'or jsonb_typeof(p->'expected_revision')<>'string'or p->>'expected_revision'!~'^[1-9][0-9]{0,14}$'then raise exception 'CP7_PLAN_REVISION';end if;
  plan:=(p->>'plan_id')::uuid;expected:=(p->>'expected_revision')::bigint;
  perform pg_advisory_xact_lock(hashtextextended('CP7:PLAN_VERSION:'||plan::text,0));
  if cp7_plan_native.access_now('DRAFT')is distinct from a then raise exception using errcode='42501',message='CP7_PLAN_ACCESS_CHANGED';end if;
  select *into r from cp7_plan_native.drafts where plan_id=plan and actor=(a->>'actor')::uuid order by revision desc limit 1;
  if r.id is null or r.revision<>expected or r.target_key<>p->>'target_key'then raise exception using errcode='40001',message='CP7_PLAN_REVISION_CHANGED';end if;
  if not exists(select 1 from cp7_plan_native.staged_drafts where draft_id=r.id)then raise exception 'CP7_PLAN_V2_DRAFT_KIND';end if;
  if exists(select 1 from cp7_plan_native.intents where draft_id in(select id from cp7_plan_native.drafts where plan_id=plan))then raise exception 'CP7_PLAN_ALREADY_APPLIED';end if;revision:=expected+1;
 end if;
 preview:=cp7_plan_native.preflight_v2(p,'SAVE',null);
 if cp7_plan_native.access_now('DRAFT')is distinct from a then raise exception using errcode='42501',message='CP7_PLAN_ACCESS_CHANGED';end if;
 insert into cp7_plan_native.drafts(plan_id,revision,actor,request_id,payload,run_id,target_key,source_hash,core_hash,composition_hash)
 values(plan,revision,(a->>'actor')::uuid,p_request,p,(p->>'run_id')::uuid,p->>'target_key',preview->>'source_hash',preview->>'identity_hash',preview->>'composition_hash')returning *into r;
 insert into cp7_plan_native.staged_drafts(draft_id,job_id,run_id,identity_hash,data_as_of,snapshot)
 values(r.id,(preview->>'job_id')::uuid,r.run_id,preview->>'identity_hash',(preview->>'data_as_of')::timestamptz,preview->'snapshot')returning *into sd;
 return jsonb_build_object('contract_version','cp7.plan-draft.v2','actor_scope_id',a->>'actor','draft_id',r.id,'plan_id',r.plan_id,'revision',r.revision::text,
  'run_id',r.run_id,'target_key',r.target_key,'identity_hash',sd.identity_hash,'data_as_of',sd.data_as_of,'request_id',p_request,'state','SAVED',
  'reservation_created',false,'production_go',false);
end $$;

create function cp7_plan_native.read_v2(p_draft uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;r cp7_plan_native.drafts%rowtype;sd cp7_plan_native.staged_drafts%rowtype;i cp7_plan_native.intents%rowtype;g erp.cutting_groups%rowtype;outcome jsonb;
begin
 a:=cp7_plan_native.access_now('READ');select *into r from cp7_plan_native.drafts where id=p_draft and actor=(a->>'actor')::uuid;
 if r.id is null then raise exception using errcode='42501',message='CP7_PLAN_DRAFT_UNAVAILABLE';end if;
 select *into sd from cp7_plan_native.staged_drafts where draft_id=r.id;
 if sd.draft_id is null then raise exception 'CP7_PLAN_V2_DRAFT_KIND';end if;
 select *into i from cp7_plan_native.intents where draft_id=r.id;if found then select *into g from erp.cutting_groups where id=i.cutting_group_id;end if;
 outcome:=jsonb_build_object('contract_version','cp7.plan-draft-read.v2','actor_scope_id',a->>'actor','draft_id',r.id,'plan_id',r.plan_id,'revision',r.revision::text,
  'run_id',r.run_id,'target_key',r.target_key,'identity_hash',sd.identity_hash,'data_as_of',sd.data_as_of,'snapshot',sd.snapshot,
  'recorded_at',r.recorded_at,'payload',r.payload,
  'is_latest',r.revision=(select max(revision)from cp7_plan_native.drafts where plan_id=r.plan_id),
  'state',case when i.id is null then 'SAVED'when g.id is null then 'NATIVE_DRAFT_DELETED'when g.material_issue_posted then 'NATIVE_MATERIAL_POSTED'else'NATIVE_DRAFT_CREATED'end,
  'native_intent',case when i.id is null then null else jsonb_build_object('id',i.id,'cutting_group_id',i.cutting_group_id,'group_number',g.group_number,'material_issue_posted',g.material_issue_posted)end,
  'reservation_created',false,'production_go',false);
 if cp7_plan_native.access_now('READ')is distinct from a then raise exception using errcode='42501',message='CP7_PLAN_ACCESS_CHANGED';end if;return outcome;
end $$;

create function cp7_plan_native.preview_v2(p_draft uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;r cp7_plan_native.drafts%rowtype;outcome jsonb;
begin
 a:=cp7_plan_native.access_now('READ');select *into r from cp7_plan_native.drafts where id=p_draft and actor=(a->>'actor')::uuid;
 if r.id is null then raise exception using errcode='42501',message='CP7_PLAN_DRAFT_UNAVAILABLE';end if;
 if not exists(select 1 from cp7_plan_native.staged_drafts where draft_id=r.id)then raise exception 'CP7_PLAN_V2_DRAFT_KIND';end if;
 if r.revision<>(select max(revision)from cp7_plan_native.drafts where plan_id=r.plan_id)then raise exception using errcode='40001',message='CP7_PLAN_REVISION_CHANGED';end if;
 outcome:=cp7_plan_native.preflight_v2(r.payload,'PREVIEW',r.id)-'native_payload';
 if outcome->>'composition_hash'<>r.composition_hash then raise exception using errcode='40001',message='CP7_PLAN_NATIVE_SELECTION_CHANGED';end if;
 if cp7_plan_native.access_now('READ')is distinct from a then raise exception using errcode='42501',message='CP7_PLAN_ACCESS_CHANGED';end if;
 return outcome||jsonb_build_object('draft_id',r.id,'plan_id',r.plan_id,'revision',r.revision::text,'actor_scope_id',a->>'actor',
  'already_applied',exists(select 1 from cp7_plan_native.intents where draft_id=r.id));
end $$;

-- Apply: v1's order (request, rolls, target, version) with one more lock: the
-- one shared capacity centre, after the rolls and before the target. v1 never
-- takes it, so no cycle can form. The live recheck runs after every lock and
-- again after the Native writer (which may wait on its own row locks); any
-- refusal rolls the Native draft back with the rest of the transaction.
create function cp7_plan_native.apply_v2(p jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;old cp7_plan_native.commands%rowtype;r cp7_plan_native.drafts%rowtype;sd cp7_plan_native.staged_drafts%rowtype;preview jsonb;native jsonb;outcome jsonb;k uuid;
begin
 a:=cp7_plan_native.access_now('APPLY');perform cp7_plan_native.fields(p,array['draft_id','expected_revision','explicit_review','reason']);
 if p_request is null or jsonb_typeof(p->'draft_id')<>'string'or jsonb_typeof(p->'expected_revision')<>'string'
  or p->>'expected_revision'!~'^[1-9][0-9]{0,14}$'or p->'explicit_review'is distinct from'true'::jsonb
  or jsonb_typeof(p->'reason')<>'string'or length(btrim(p->>'reason'))not between 1 and 1000 then raise exception 'CP7_PLAN_EXPLICIT_REVIEW';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:PLAN_APPLY_REQUEST:'||(a->>'actor')||':'||p_request::text,0));
 if cp7_plan_native.access_now('APPLY')is distinct from a then raise exception using errcode='42501',message='CP7_PLAN_ACCESS_CHANGED';end if;
 select *into old from cp7_plan_native.commands where actor=(a->>'actor')::uuid and request_id=p_request;
 if found then if old.payload<>p or old.result->>'contract_version'<>'cp7.plan-apply-outcome.v2'then raise exception 'CP7_PLAN_REQUEST_CHANGED';end if;return old.result;end if;
 select *into r from cp7_plan_native.drafts where id=(p->>'draft_id')::uuid and actor=(a->>'actor')::uuid;
 if r.id is null then raise exception using errcode='42501',message='CP7_PLAN_DRAFT_UNAVAILABLE';end if;
 select *into sd from cp7_plan_native.staged_drafts where draft_id=r.id;
 if sd.draft_id is null then raise exception 'CP7_PLAN_V2_DRAFT_KIND';end if;
 for k in select distinct(x->>'roll_id')::uuid from jsonb_array_elements(r.payload->'cutting'->'rolls')x order by 1 loop
  perform pg_advisory_xact_lock(hashtextextended('CP7:PLAN_MATERIAL_POOL:'||k::text,0));
 end loop;
 if cp7_plan_native.access_now('APPLY')is distinct from a then raise exception using errcode='42501',message='CP7_PLAN_ACCESS_CHANGED';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:PLAN_CAPACITY',0));
 if cp7_plan_native.access_now('APPLY')is distinct from a then raise exception using errcode='42501',message='CP7_PLAN_ACCESS_CHANGED';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:PLAN_TARGET:'||r.target_key,0));
 perform pg_advisory_xact_lock(hashtextextended('CP7:PLAN_VERSION:'||r.plan_id::text,0));
 if cp7_plan_native.access_now('APPLY')is distinct from a then raise exception using errcode='42501',message='CP7_PLAN_ACCESS_CHANGED';end if;
 if r.revision::text<>p->>'expected_revision'or r.revision<>(select max(revision)from cp7_plan_native.drafts where plan_id=r.plan_id)then raise exception using errcode='40001',message='CP7_PLAN_REVISION_CHANGED';end if;
 if exists(select 1 from cp7_plan_native.intents where draft_id=r.id)then raise exception 'CP7_PLAN_ALREADY_APPLIED';end if;
 preview:=cp7_plan_native.preflight_v2(r.payload,'APPLY',r.id);
 if preview->>'composition_hash'<>r.composition_hash then raise exception using errcode='40001',message='CP7_PLAN_NATIVE_SELECTION_CHANGED';end if;
 if cp7_plan_native.access_now('APPLY')is distinct from a then raise exception using errcode='42501',message='CP7_PLAN_ACCESS_CHANGED';end if;
 native:=public.erp_save_cutting_group_before_sewing_v2(preview->'native_payload',p_request,null);
 if native->'material_issue_posted'is distinct from'false'::jsonb then raise exception 'CP7_PLAN_DOMAIN_DRAFT_ONLY';end if;
 -- The Native writer can wait on real roll locks: recheck everything after
 -- that wait, before recording an intent (its own unposted draft is not WIP).
 preview:=cp7_plan_native.preflight_v2(r.payload,'APPLY',r.id);
 if preview->>'composition_hash'<>r.composition_hash then raise exception using errcode='40001',message='CP7_PLAN_NATIVE_SELECTION_CHANGED';end if;
 if cp7_plan_native.access_now('APPLY')is distinct from a then raise exception using errcode='42501',message='CP7_PLAN_ACCESS_CHANGED';end if;
 insert into cp7_plan_native.intents(draft_id,actor,target_key,core_hash,cutting_group_id,request_id)
 values(r.id,(a->>'actor')::uuid,r.target_key,sd.identity_hash,(native->>'cutting_group_id')::uuid,p_request)returning id into k;
 outcome:=jsonb_build_object('contract_version','cp7.plan-apply-outcome.v2','kind','COMMITTED_OUTCOME','actor_scope_id',a->>'actor',
  'request_id',p_request,'draft_id',r.id,'revision',r.revision::text,'intent_id',k,'target_key',r.target_key,
  'identity_hash',sd.identity_hash,'data_as_of',sd.data_as_of,'live',preview->'live','native',native,
  'state','NATIVE_DRAFT_CREATED','reservation_created',false,'physical_production_confirmed',false,'production_go',false);
 insert into cp7_plan_native.commands(actor,request_id,payload,result)values((a->>'actor')::uuid,p_request,p,outcome);return outcome;
end $$;

alter function cp7_plan_native.staged_source(uuid,text)owner to cp7_capture;
alter function cp7_plan_native.staged_live(uuid,text)owner to cp7_capture;
alter function cp7_plan_native.after_snapshot(xid,timestamptz,timestamptz,pg_snapshot)owner to cp7_plan_writer;
alter function cp7_plan_native.preflight_v2(jsonb,text,uuid)owner to cp7_plan_writer;
alter function cp7_plan_native.options_v2(jsonb)owner to cp7_plan_writer;
alter function cp7_plan_native.save_v2(jsonb,uuid)owner to cp7_plan_writer;
alter function cp7_plan_native.read_v2(uuid)owner to cp7_plan_writer;
alter function cp7_plan_native.preview_v2(uuid)owner to cp7_plan_writer;
alter function cp7_plan_native.apply_v2(jsonb,uuid)owner to cp7_plan_writer;
revoke all on function cp7_plan_native.staged_source(uuid,text),cp7_plan_native.staged_live(uuid,text),
 cp7_plan_native.after_snapshot(xid,timestamptz,timestamptz,pg_snapshot),cp7_plan_native.preflight_v2(jsonb,text,uuid),
 cp7_plan_native.options_v2(jsonb),cp7_plan_native.save_v2(jsonb,uuid),cp7_plan_native.read_v2(uuid),
 cp7_plan_native.preview_v2(uuid),cp7_plan_native.apply_v2(jsonb,uuid)from public,anon,authenticated,service_role;
grant execute on function cp7_plan_native.staged_source(uuid,text),cp7_plan_native.staged_live(uuid,text)to cp7_plan_writer;
grant create on schema public to cp7_plan_writer;
create function public.erp_cp7_get_plan_options_v2(p_query jsonb)returns jsonb language sql volatile security definer set search_path=''as $$select cp7_plan_native.options_v2(p_query)$$;
create function public.erp_cp7_save_plan_draft_v2(p_payload jsonb,p_request uuid)returns jsonb language sql volatile security definer set search_path=''as $$select cp7_plan_native.save_v2(p_payload,p_request)$$;
create function public.erp_cp7_read_plan_draft_v2(p_draft uuid)returns jsonb language sql volatile security definer set search_path=''as $$select cp7_plan_native.read_v2(p_draft)$$;
create function public.erp_cp7_preview_plan_action_v2(p_draft uuid)returns jsonb language sql volatile security definer set search_path=''as $$select cp7_plan_native.preview_v2(p_draft)$$;
create function public.erp_cp7_apply_plan_action_v2(p_payload jsonb,p_request uuid)returns jsonb language sql volatile security definer set search_path=''as $$select cp7_plan_native.apply_v2(p_payload,p_request)$$;
alter function public.erp_cp7_get_plan_options_v2(jsonb)owner to cp7_plan_writer;
alter function public.erp_cp7_save_plan_draft_v2(jsonb,uuid)owner to cp7_plan_writer;
alter function public.erp_cp7_read_plan_draft_v2(uuid)owner to cp7_plan_writer;
alter function public.erp_cp7_preview_plan_action_v2(uuid)owner to cp7_plan_writer;
alter function public.erp_cp7_apply_plan_action_v2(jsonb,uuid)owner to cp7_plan_writer;
revoke create on schema public from cp7_plan_writer;
revoke all on function public.erp_cp7_get_plan_options_v2(jsonb),public.erp_cp7_save_plan_draft_v2(jsonb,uuid),public.erp_cp7_read_plan_draft_v2(uuid),
 public.erp_cp7_preview_plan_action_v2(uuid),public.erp_cp7_apply_plan_action_v2(jsonb,uuid)from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_plan_options_v2(jsonb),public.erp_cp7_save_plan_draft_v2(jsonb,uuid),public.erp_cp7_read_plan_draft_v2(uuid),
 public.erp_cp7_preview_plan_action_v2(uuid),public.erp_cp7_apply_plan_action_v2(jsonb,uuid)to authenticated;
