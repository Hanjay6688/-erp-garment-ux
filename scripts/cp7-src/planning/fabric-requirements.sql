-- Explicit effective-dated planning inputs, never Native BOM/stock/consumption.
-- An exact physical product/size and full current Native material identity are
-- reviewed together. No rate, pattern, width, allocation or installation default.
create schema cp7_fabric_native authorization cp7_capture;
revoke all on schema cp7_fabric_native from public,anon,authenticated,service_role;
grant select on erp.materials,erp.production_patterns to cp7_capture;
-- P08 physical facts: read-only columns at the shared capture clock. No price,
-- cost, reservation, issue, receipt or stock writer is granted.
grant select(id,material_id,status)on erp.material_rolls to cp7_capture;
grant select(material_id,roll_id,location_id,qty_signed,physical_at)on erp.material_stock_movements to cp7_capture;
grant select(id,location_type,is_active)on erp.locations to cp7_capture;
grant select(id,po_number,location_id,expected_date)on erp.bb_purchase_commitments_v1 to cp7_capture;
grant select(id,commitment_id,material_id,line_number)on erp.bb_purchase_commitment_lines_v1 to cp7_capture;
grant execute on function erp.bb_commitment_line_remaining_v1(uuid,uuid)to cp7_capture;
create table cp7_fabric_native.recipes(
 id uuid primary key default gen_random_uuid(),target_key text not null,
 revision bigint not null check(revision>0),source_run uuid not null,source_hash text not null,
 config jsonb not null,reason text not null,actor uuid not null,request_id uuid not null,
 recorded_at timestamptz not null default clock_timestamp(),unique(target_key,revision),unique(actor,request_id)
);
create table cp7_fabric_native.commands(
 actor uuid not null,request_id uuid not null,payload jsonb not null,result jsonb not null,
 primary key(actor,request_id)
);
alter table cp7_fabric_native.recipes owner to cp7_capture;
alter table cp7_fabric_native.commands owner to cp7_capture;
alter table cp7_fabric_native.recipes enable row level security;
alter table cp7_fabric_native.commands enable row level security;
create policy fabric_recipes_private on cp7_fabric_native.recipes for all to public using(false)with check(false);
create policy fabric_commands_private on cp7_fabric_native.commands for all to public using(false)with check(false);
revoke all on all tables in schema cp7_fabric_native from public,anon,authenticated,service_role;
create trigger fabric_recipe_immutable before update or delete on cp7_fabric_native.recipes
 for each row execute function cp7_private.immutable_run();
create trigger fabric_command_immutable before update or delete on cp7_fabric_native.commands
 for each row execute function cp7_private.immutable_run();

-- Review identity of a Native fabric master: every master field, but not the
-- stock/cost caches and audit counters that every receipt or issue rewrites
-- (cached_stock_qty, moving_average_cost, row_version, updated_at). A real
-- master revision (SKU, name, type, unit, activity, category) still changes it.
create function cp7_fabric_native.material_hash(m jsonb)returns text
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select encode(extensions.digest(convert_to(jsonb_build_object('id',m->'id','material_sku',m->'material_sku','material_name',m->'material_name',
  'material_type',m->'material_type','unit_code',m->'unit_code','is_active',m->'is_active','accessory_category_id',m->'accessory_category_id',
  'created_at',m->'created_at')::text,'UTF8'),'sha256'),'hex')
$$;

create function cp7_fabric_native.validate(v jsonb,catalog jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare m jsonb;p jsonb;lo timestamptz;hi timestamptz;
begin
 perform cp7_wip.fields(v,array['basis','effective_from','effective_to','material_id','material_hash','unit','qty_per_good_pcs','pattern_id','pattern_hash']);
 if v->>'basis'is distinct from'SELECTED_ASSUMPTIONS'then raise exception 'CP7_FABRIC_BASIS';end if;
 if jsonb_typeof(v->'material_id')is distinct from'string'or v->>'material_id'!~'^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$'
  or jsonb_typeof(v->'material_hash')is distinct from'string'or v->>'material_hash'!~'^[0-9a-f]{64}$'
  or jsonb_typeof(v->'unit')is distinct from'string'then raise exception 'CP7_FABRIC_NATIVE_MATERIAL_CHANGED';end if;
 lo:=cp7_demand.instant(v->'effective_from');
 if v->'effective_to'<>'null'::jsonb then hi:=cp7_demand.instant(v->'effective_to');
  if hi<=lo then raise exception 'CP7_FABRIC_EFFECTIVE_WINDOW';end if;
 end if;
 if jsonb_typeof(v->'qty_per_good_pcs')is distinct from'string'
  or v->>'qty_per_good_pcs'!~'^(0|[1-9][0-9]{0,11})([.][0-9]{1,6})?$'
  or (v->>'qty_per_good_pcs')::numeric<=0 then raise exception 'CP7_FABRIC_RATE';end if;
 select x into m from jsonb_array_elements(catalog->'materials')x where x->>'id'=v->>'material_id';
 if m is null or m->>'material_type'<>'FABRIC'or m->'is_active'is distinct from'true'::jsonb
  or v->>'material_hash'is distinct from cp7_fabric_native.material_hash(m)
  or v->>'unit'is distinct from m->>'unit_code'then raise exception 'CP7_FABRIC_NATIVE_MATERIAL_CHANGED';end if;
 if v->'pattern_id'='null'::jsonb then
  if v->'pattern_hash'<>'null'::jsonb then raise exception 'CP7_FABRIC_PATTERN';end if;
 else
  if jsonb_typeof(v->'pattern_id')is distinct from'string'or v->>'pattern_id'!~'^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$'
   or jsonb_typeof(v->'pattern_hash')is distinct from'string'or v->>'pattern_hash'!~'^[0-9a-f]{64}$'then raise exception 'CP7_FABRIC_PATTERN';end if;
  select x into p from jsonb_array_elements(catalog->'patterns')x where x->>'id'=v->>'pattern_id';
  if p is null or p->'is_active'is distinct from'true'::jsonb
   or v->>'pattern_hash'is distinct from encode(extensions.digest(convert_to(p::text,'UTF8'),'sha256'),'hex')then
   raise exception 'CP7_FABRIC_NATIVE_PATTERN_CHANGED';end if;
 end if;
 return v;
end $$;

create function cp7_fabric_native.source(products jsonb,p_at timestamptz)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare v jsonb;selected jsonb;m jsonb;p jsonb;
begin
 with targets as(select (x->>'root_id')||':'||(x->>'size_id')key from jsonb_array_elements(products)x),
 versions as(select to_jsonb(r)body from cp7_fabric_native.recipes r join targets t on t.key=r.target_key
  where r.recorded_at<=p_at order by r.target_key,r.revision limit 10001)
 select coalesce(jsonb_agg(body order by body->>'target_key',(body->>'revision')::bigint),'[]')into v from versions;
 if jsonb_array_length(v)>10000 then raise exception 'CP7_FABRIC_SOURCE_LIMIT';end if;
 -- A successor starts at its chosen effective clock. Expiry yields UNKNOWN;
 -- it never silently resurrects an older rate. Future versions are still kept
 -- in the Original, but cannot become a current operational operand early.
 with candidates as(select distinct on(x->>'target_key')x from jsonb_array_elements(v)x
  where(x->'config'->>'effective_from')::timestamptz<=p_at order by x->>'target_key',(x->>'revision')::bigint desc)
 select coalesce(jsonb_agg(x order by x->>'target_key'),'[]')into selected from candidates
  where x->'config'->'effective_to'='null'::jsonb or(x->'config'->>'effective_to')::timestamptz>p_at;
 select coalesce(jsonb_agg(to_jsonb(x)order by x.id),'[]')into m from erp.materials x
  where (to_jsonb(x)->>'created_at')::timestamptz<=p_at
   and exists(select 1 from jsonb_array_elements(selected)s where s->'config'->>'material_id'=x.id::text);
 select coalesce(jsonb_agg(to_jsonb(x)order by x.id),'[]')into p from erp.production_patterns x
  where x.created_at<=p_at and exists(select 1 from jsonb_array_elements(selected)s where s->'config'->>'pattern_id'=x.id::text);
 return jsonb_build_object('contract_version','cp7.fabric-source.v2','captured_at',p_at,
  'versions',v,'selected',selected,'materials',m,'patterns',p,
  'physical',cp7_fabric_native.physical_source(selected,p_at),
  'basis','SELECTED_ASSUMPTIONS_NOT_NATIVE_RECIPE_INSTALLATION_OR_ALLOCATION');
end $$;

-- Current Native physical operands for every selected fabric at one capture
-- clock: roll stock per location, every unposted cutting composition touching
-- those rolls or linked by a CP7 intent to a reviewed target, and every open
-- opening-balance purchase commitment. A draft is a plan, not a reservation;
-- posted groups are already represented once in physical stock.
create function cp7_fabric_native.physical_source(selected jsonb,p_at timestamptz)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare mats uuid[];targets text[];drafts jsonb;rolls jsonb;locations jsonb;commitments jsonb;
begin
 select coalesce(array_agg(distinct(x->'config'->>'material_id')::uuid),array[]::uuid[]),coalesce(array_agg(distinct x->>'target_key'),array[]::text[])
  into mats,targets from jsonb_array_elements(selected)x;
 with groups as materialized(
  select g.id,g.row_version,g.source_location_id from erp.cutting_groups g
  where not g.material_issue_posted and(
   exists(select 1 from erp.cutting_group_rolls l join erp.material_rolls r on r.id=l.roll_id where l.cutting_group_id=g.id and r.material_id=any(mats))
   or exists(select 1 from cp7_plan_native.intents i where i.cutting_group_id=g.id and i.target_key=any(targets)))
  order by g.id limit 10001)
 select coalesce(jsonb_agg(jsonb_build_object('id',g.id,'revision',g.row_version::text,'source_location_id',g.source_location_id,
   'intents',coalesce((select jsonb_agg(jsonb_build_object('id',i.id,'target_key',i.target_key)order by i.id)
    from cp7_plan_native.intents i where i.cutting_group_id=g.id),'[]'::jsonb),
   'lines',coalesce((select jsonb_agg(jsonb_build_object('id',l.id,'roll_id',l.roll_id,'qty_issued',trim_scale(l.qty_issued)::text)order by l.id)
    from erp.cutting_group_rolls l where l.cutting_group_id=g.id),'[]'::jsonb))order by g.id),'[]'::jsonb)
  into drafts from groups g;
 if jsonb_array_length(drafts)>10000 then raise exception 'CP7_FABRIC_PHYSICAL_LIMIT';end if;
 with ids as(select r.id from erp.material_rolls r where r.material_id=any(mats)
   union select(l->>'roll_id')::uuid from jsonb_array_elements(drafts)d cross join jsonb_array_elements(d->'lines')l),
 limited as materialized(select id from ids order by id limit 20001)
 select coalesce(jsonb_agg(jsonb_build_object('id',r.id,'material_id',r.material_id,'status',r.status,
   'consistent',not exists(select 1 from erp.material_stock_movements m where m.roll_id=r.id and m.physical_at<=p_at and m.material_id<>r.material_id),
   'stock',coalesce((select jsonb_agg(jsonb_build_object('location_id',s.location_id,'qty',trim_scale(s.qty)::text)order by s.location_id)
    from(select m.location_id,sum(m.qty_signed)qty from erp.material_stock_movements m
     where m.roll_id=r.id and m.physical_at<=p_at group by m.location_id)s where s.qty<>0),'[]'::jsonb))order by r.id),'[]'::jsonb)
  into rolls from limited x join erp.material_rolls r on r.id=x.id;
 if jsonb_array_length(rolls)>20000 then raise exception 'CP7_FABRIC_PHYSICAL_LIMIT';end if;
 with lines as materialized(select l.id,l.commitment_id,l.material_id,l.line_number,c.po_number,c.location_id,c.expected_date,
   erp.bb_commitment_line_remaining_v1(l.id,null)remaining
  from erp.bb_purchase_commitment_lines_v1 l join erp.bb_purchase_commitments_v1 c on c.id=l.commitment_id
  where l.material_id=any(mats)order by l.id limit 10001)
 select coalesce(jsonb_agg(jsonb_build_object('id',x.id,'commitment_id',x.commitment_id,'po_number',x.po_number,'line_number',x.line_number,
   'material_id',x.material_id,'location_id',x.location_id,'expected_date',x.expected_date,'remaining',trim_scale(x.remaining)::text)order by x.id),'[]'::jsonb)
  into commitments from lines x where x.remaining<>0;
 if jsonb_array_length(commitments)>10000 then raise exception 'CP7_FABRIC_PHYSICAL_LIMIT';end if;
 select coalesce(jsonb_agg(jsonb_build_object('id',l.id,'location_type',l.location_type,'is_active',l.is_active)order by l.id),'[]'::jsonb)
  into locations from erp.locations l
  where l.id in(select(s->>'location_id')::uuid from jsonb_array_elements(rolls)r cross join jsonb_array_elements(r->'stock')s where s->>'location_id'is not null
   union select(d->>'source_location_id')::uuid from jsonb_array_elements(drafts)d where d->>'source_location_id'is not null
   union select(c->>'location_id')::uuid from jsonb_array_elements(commitments)c);
 return jsonb_build_object('contract_version','cp7.fabric-physical.v1','drafts',drafts,'rolls',rolls,'locations',locations,'commitments',commitments,
  'basis','NATIVE_ROLL_STOCK_UNPOSTED_DRAFT_COMPOSITION_AND_OPEN_OPENING_COMMITMENT_NOT_RESERVATION');
end $$;

-- One immutable lookup per analysis; every consumer reads the same selection.
create function cp7_fabric_native.index(c jsonb)returns jsonb
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object(
  'selected',coalesce((select jsonb_object_agg(x->>'target_key',x)from jsonb_array_elements(c->'fabric_source'->'selected')x),'{}'::jsonb),
  'materials',coalesce((select jsonb_object_agg(x->>'id',x)from jsonb_array_elements(c->'fabric_source'->'materials')x),'{}'::jsonb),
  'patterns',coalesce((select jsonb_object_agg(x->>'id',x)from jsonb_array_elements(c->'fabric_source'->'patterns')x),'{}'::jsonb))
$$;

create function cp7_fabric_native.recipe_state(ix jsonb,r jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare recipe jsonb:=ix->'selected'->(r->>'target_key');cfg jsonb;m jsonb;p jsonb;refs jsonb:='[]';valid boolean:=false;
begin
 if recipe is null then return jsonb_build_object('recipe',null,'valid',false,'refs',refs,'gross',null);end if;
 cfg:=recipe->'config';refs:=jsonb_build_array(cp7_wip.ref('CP7_FABRIC_RECIPE',recipe->>'id',recipe->>'revision'));
 m:=ix->'materials'->(cfg->>'material_id');
 if m is not null then refs:=refs||jsonb_build_array(cp7_wip.ref('erp.materials',m->>'id',cp7_fabric_native.material_hash(m)));end if;
 if cfg->'pattern_id'<>'null'::jsonb then
  p:=ix->'patterns'->(cfg->>'pattern_id');
  if p is not null then refs:=refs||jsonb_build_array(cp7_wip.ref('erp.production_patterns',p->>'id',
   encode(extensions.digest(convert_to(p::text,'UTF8'),'sha256'),'hex')));end if;
 end if;
 valid:=m is not null and m->'is_active'='true'::jsonb and m->>'material_type'='FABRIC'
  and m->>'unit_code'=cfg->>'unit'and cfg->>'material_hash'=cp7_fabric_native.material_hash(m)
  and(cfg->'pattern_id'='null'::jsonb or(p is not null and p->'is_active'='true'::jsonb
   and cfg->>'pattern_hash'=encode(extensions.digest(convert_to(p::text,'UTF8'),'sha256'),'hex')));
 return jsonb_build_object('recipe',recipe,'material',m,'pattern',p,'valid',coalesce(valid,false),'refs',refs,
  'unit',cfg->>'unit','material_id',cfg->>'material_id',
  'gross',case when coalesce(valid,false)and r->>'conditional_gap_pcs'is not null
   then((r->>'conditional_gap_pcs')::numeric*(cfg->>'qty_per_good_pcs')::numeric)::text end);
end $$;

-- P08 physical facts, fail-closed. Installed is zero only for unstarted
-- conditional PCS whose WIP identity is fully resolved. Allocated unused is a
-- current linked Native draft composition covered by roll stock, plus free
-- eligible stock only when the claimant set is complete and the split is
-- unique. Open commitments count once, on time, for one claimant. Any doubt
-- is UNKNOWN with a reason; arithmetic is the trusted material-need kernel.
create function cp7_fabric_native.plan(c jsonb,n jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare ph jsonb:=c->'fabric_source'->'physical';ix jsonb:=cp7_fabric_native.index(c);r jsonb;st jsonb;policy text;zero boolean;
 unresolved_targets jsonb;drafts jsonb;pools jsonb;stats jsonb;claims jsonb[]:='{}';results jsonb[]:='{}';unresolved integer:=0;cl jsonb;pool jsonb;
 stat jsonb;t text;mat text;installed text;installed_code text;own jsonb;own_qty numeric;own_code text;own_refs jsonb;certain boolean;
 unused numeric;unused_refs jsonb;basis text;supplies jsonb;kernel jsonb;code text;ext text;ext_refs jsonb;eta text;v_line jsonb;
 upper text;captured timestamptz:=(c->>'captured_at')::timestamptz;today date:=((c->>'captured_at')::timestamptz at time zone 'Asia/Jakarta')::date;
begin
 if ph is null or ph->>'contract_version'is distinct from'cp7.fabric-physical.v1'then
  return jsonb_build_object('index',ix,'targets','{}'::jsonb,'physical_source',false);end if;
 select coalesce(jsonb_object_agg(k,true),'{}'::jsonb)into unresolved_targets from(select distinct x->>'target_key'k
  from jsonb_array_elements(coalesce(n->'match_results','[]'))x where x->'result'->>'match'in('UNKNOWN','NEEDS_CHECK'))s;
 -- Coverage is evaluated over every unposted composition on the same roll and
 -- location, linked or not; an over-committed roll covers no draft, frees none.
 with loc as(select x->>'id'id,(x->>'location_type'='RAW_MATERIAL_WAREHOUSE'and x->'is_active'='true'::jsonb)ok
   from jsonb_array_elements(ph->'locations')x),
 roll as(select x->>'id'id,x->>'material_id'material,x->>'status'status,x->'consistent'='true'::jsonb consistent
   from jsonb_array_elements(ph->'rolls')x),
 stock as(select x->>'id'roll,s->>'location_id'loc,(s->>'qty')::numeric qty
   from jsonb_array_elements(ph->'rolls')x cross join jsonb_array_elements(x->'stock')s),
 line as(select d->>'source_location_id'loc,l->>'roll_id'roll,(l->>'qty_issued')::numeric qty
   from jsonb_array_elements(ph->'drafts')d cross join jsonb_array_elements(d->'lines')l),
 drafted as(select roll,loc,sum(qty)qty from line group by roll,loc),
 cell as materialized(select coalesce(s.roll,d.roll)roll,coalesce(s.loc,d.loc)loc,coalesce(s.qty,0)stock,coalesce(d.qty,0)drafted
   from stock s full join drafted d on d.roll=s.roll and d.loc is not distinct from s.loc),
 linked as(select distinct i->>'target_key'tkey,d from jsonb_array_elements(ph->'drafts')d cross join jsonb_array_elements(d->'intents')i),
 checked as(select l.tkey,l.d->>'id'gid,l.d->>'revision'rev,
   (select coalesce(sum((x->>'qty_issued')::numeric),0)from jsonb_array_elements(l.d->'lines')x)qty,
   not exists(select 1 from jsonb_array_elements(l.d->'intents')i where i->>'target_key'<>l.tkey)
   and coalesce((select ok from loc where id=l.d->>'source_location_id'),false)
   and jsonb_array_length(l.d->'lines')>0
   and not exists(select 1 from jsonb_array_elements(l.d->'lines')x left join roll ro on ro.id=x->>'roll_id'
    left join cell ce on ce.roll=x->>'roll_id'and ce.loc is not distinct from l.d->>'source_location_id'
    where ro.id is null or ro.status not in('AVAILABLE','HALF_USED')or not ro.consistent or ce.roll is null or ce.stock<0 or ce.stock<ce.drafted)ok,
   (select coalesce(jsonb_agg(distinct ro.material),'[]'::jsonb)from jsonb_array_elements(l.d->'lines')x left join roll ro on ro.id=x->>'roll_id')materials
  from linked l)
 select coalesce(jsonb_object_agg(tkey,body),'{}'::jsonb)into drafts from(select c0.tkey,jsonb_build_object('qty',trim_scale(sum(qty))::text,'ok',bool_and(ok),
   'materials',(select coalesce(jsonb_agg(distinct m),'[]'::jsonb)from checked k cross join jsonb_array_elements(k.materials)m where k.tkey=c0.tkey),
   'refs',jsonb_agg(cp7_wip.ref('erp.cutting_groups',gid,rev)order by gid))body from checked c0 group by c0.tkey)a;
 with loc as(select x->>'id'id,(x->>'location_type'='RAW_MATERIAL_WAREHOUSE'and x->'is_active'='true'::jsonb)ok
   from jsonb_array_elements(ph->'locations')x),
 roll as(select x->>'id'id,x->>'material_id'material,x->>'status'status,x->'consistent'='true'::jsonb consistent,x
   from jsonb_array_elements(ph->'rolls')x),
 stock as(select x->>'id'roll,s->>'location_id'loc,(s->>'qty')::numeric qty
   from jsonb_array_elements(ph->'rolls')x cross join jsonb_array_elements(x->'stock')s),
 line as(select d->>'source_location_id'loc,l->>'roll_id'roll,(l->>'qty_issued')::numeric qty,jsonb_array_length(d->'intents')=0 manual,d
   from jsonb_array_elements(ph->'drafts')d cross join jsonb_array_elements(d->'lines')l),
 drafted as(select roll,loc,sum(qty)qty from line group by roll,loc),
 cell as materialized(select coalesce(s.roll,d.roll)roll,coalesce(s.loc,d.loc)loc,coalesce(s.qty,0)stock,coalesce(d.qty,0)drafted
   from stock s full join drafted d on d.roll=s.roll and d.loc is not distinct from s.loc),
 pending_lines as(select x from jsonb_array_elements(ph->'commitments')x where(x->>'remaining')::numeric>0),
 mats as(select distinct x->'config'->>'material_id'material from jsonb_array_elements(c->'fabric_source'->'selected')x)
 select coalesce(jsonb_object_agg(m.material,jsonb_build_object(
   'free',(select trim_scale(coalesce(sum(greatest(0,ce.stock-ce.drafted)),0))::text from cell ce join roll ro on ro.id=ce.roll join loc on loc.id=ce.loc
    where ro.material=m.material and ro.status in('AVAILABLE','HALF_USED')and ro.consistent and loc.ok),
   'bad',exists(select 1 from roll ro where ro.material=m.material and not ro.consistent)
    or exists(select 1 from cell ce join roll ro on ro.id=ce.roll where ro.material=m.material and ce.stock<0),
   'manual',exists(select 1 from line li join roll ro on ro.id=li.roll where ro.material=m.material and li.manual),
   'incoming',(select coalesce(jsonb_agg(o.x order by o.x->>'id'),'[]'::jsonb)from pending_lines o where o.x->>'material_id'=m.material),
   'incoming_location_ok',not exists(select 1 from pending_lines o where o.x->>'material_id'=m.material
    and not coalesce((select ok from loc where id=o.x->>'location_id'),false)),
   'hash',encode(extensions.digest(convert_to(jsonb_build_object(
    'rolls',(select coalesce(jsonb_agg(ro.x order by ro.id),'[]'::jsonb)from roll ro where ro.material=m.material),
    'drafts',(select coalesce(jsonb_agg(distinct li.d),'[]'::jsonb)from line li join roll ro on ro.id=li.roll where ro.material=m.material),
    'locations',ph->'locations',
    'commitments',(select coalesce(jsonb_agg(x order by x->>'id'),'[]'::jsonb)from jsonb_array_elements(ph->'commitments')x where x->>'material_id'=m.material))::text,'UTF8'),'sha256'),'hex'))),'{}'::jsonb)
  into pools from mats m;
 -- Claimants consume fabric for a new start. A known zero gap or a paused or
 -- stopped policy consumes none. Any other row without a proved recipe could
 -- need any fabric, so every shared stock/commitment split becomes uncertain.
 for r in select value from jsonb_array_elements(coalesce(n->'rows','[]'))order by value->>'target_key'loop
  t:=r->>'target_key';policy:=r->'production_policy'->'policy'->>'state';st:=cp7_fabric_native.recipe_state(ix,r);
  zero:=r->>'conditional_gap_pcs'is not null and(r->>'conditional_gap_pcs')::numeric=0;
  if st->>'valid'<>'true'then
   if not zero and coalesce(policy,'')not in('PAUSED','STOPPED')then unresolved:=unresolved+1;end if;continue;
  end if;
  mat:=st->>'material_id';own:=drafts->t;installed:=null;installed_code:=null;own_qty:=null;own_code:=null;own_refs:='[]';
  -- Installed is zero only for PCS proven not yet cut at the capture clock:
  -- every WIP position of this exact product/size is resolved. Unproved
  -- brand/color same-model WIP may already hold this target's fabric, so
  -- installation stays UNKNOWN; the external value is then only a bound.
  if st->>'gross'is null then installed_code:='FABRIC_GAP_UNKNOWN';
  elsif unresolved_targets?t then installed_code:='FABRIC_WIP_IDENTITY_UNRESOLVED';
  else installed:='0';end if;
  if own is null then own_qty:=0;
  elsif own->>'ok'='true'and own->'materials'=jsonb_build_array(mat)then own_qty:=(own->>'qty')::numeric;own_refs:=own->'refs';
  else own_code:='FABRIC_LINKED_DRAFT_NOT_ELIGIBLE';end if;
  claims:=array_append(claims,jsonb_build_object('target_key',t,'material_id',mat,'gross',st->'gross','unit',st->>'unit',
   'recipe_ref',st->'refs'->0,'disabled',coalesce(policy in('PAUSED','STOPPED'),false),
   'claimant',not zero and coalesce(policy,'')not in('PAUSED','STOPPED'),'deadline',r->'net'->'inputs'->'deadline',
   'identity_unresolved',coalesce(unresolved_targets?t,false),
   'installed',installed,'installed_code',installed_code,'own',case when own_qty is null then null else trim_scale(own_qty)::text end,
   'own_code',own_code,'own_refs',own_refs,
   -- Outstanding uses installed0 as the conservative maximum: exact when
   -- installation is proved, an upper bound when identity is unresolved.
   'outstanding',case when st->>'gross'is not null and own_qty is not null
    then trim_scale(greatest(0,(st->>'gross')::numeric-own_qty))::text end));
 end loop;
 select coalesce(jsonb_object_agg(material,jsonb_build_object('claimants',k,'all_known',all_known,'total',total)),'{}'::jsonb)into stats
  from(select x->>'material_id'material,count(*)k,bool_and(x->>'outstanding'is not null)all_known,
   trim_scale(coalesce(sum((x->>'outstanding')::numeric),0))::text total
   from unnest(claims)x where x->'claimant'='true'::jsonb group by 1)a;
 foreach cl in array claims loop
  t:=cl->>'target_key';mat:=cl->>'material_id';pool:=pools->mat;stat:=stats->mat;ext:=null;code:=null;unused:=null;unused_refs:='[]';upper:=null;
  basis:=null;supplies:='[]';ext_refs:='[]';certain:=unresolved=0 and coalesce(stat->'all_known'='true'::jsonb,false);
  if cl->>'own'is not null then unused:=(cl->>'own')::numeric;unused_refs:=cl->'own_refs';basis:=case when unused>0 then 'DRAFT'else 'NONE'end;end if;
  if cl->'disabled'='true'::jsonb then code:='FABRIC_PRODUCTION_DISABLED';
  elsif cl->>'outstanding'is null then code:=coalesce(cl->>'own_code',cl->>'installed_code','FABRIC_PHYSICAL_NOT_PROVEN');
  elsif cl->'claimant'<>'true'::jsonb then null; -- known zero new-start gap
  elsif pool is null or pool->'bad'='true'::jsonb then code:='FABRIC_STOCK_INCONSISTENT';
  elsif pool->'manual'='true'::jsonb then code:='FABRIC_UNLINKED_NATIVE_DRAFT';
  elsif certain and(stat->>'total')::numeric<=(pool->>'free')::numeric then
   unused:=unused+(cl->>'outstanding')::numeric;basis:='SUFFICIENT_FREE_STOCK';
   unused_refs:=unused_refs||jsonb_build_array(cp7_wip.ref('CP7_FABRIC_FREE_STOCK',mat,pool->>'hash'));
  elsif certain and(stat->>'claimants')::integer=1 then
   if(pool->>'free')::numeric>0 then unused:=unused+(pool->>'free')::numeric;basis:='SINGLE_CLAIMANT_FREE_STOCK';
    unused_refs:=unused_refs||jsonb_build_array(cp7_wip.ref('CP7_FABRIC_FREE_STOCK',mat,pool->>'hash'));end if;
   if jsonb_array_length(pool->'incoming')>0 then
    if pool->'incoming_location_ok'<>'true'::jsonb then code:='FABRIC_INCOMING_LOCATION_NOT_ELIGIBLE';
    elsif cl->>'deadline'is null then code:='FABRIC_DEADLINE_UNKNOWN';
    else
     ext_refs:=jsonb_build_array(cp7_wip.ref('CP7_FABRIC_OPEN_COMMITMENTS',mat,pool->>'hash'));
     for v_line in select value from jsonb_array_elements(pool->'incoming')loop
      -- A WIB expected date counts from the end of that day. An overdue open
      -- commitment has no proved arrival; it is never assumed on time.
      if(v_line->>'expected_date')::date<today then code:='FABRIC_INCOMING_OVERDUE';end if;
      eta:=case when v_line->>'expected_date'is null then null
       else cp7_planning.utc((((v_line->>'expected_date')::date+1)::timestamp)at time zone 'Asia/Jakarta')end;
      supplies:=supplies||jsonb_build_array(jsonb_build_object('physical_key','BB_COMMITMENT_LINE:'||(v_line->>'id'),'kind','INCOMING',
       'quantity',v_line->'remaining','verified_eligible_allocated',true,'eta',coalesce(to_jsonb(eta),'null'::jsonb),
       'refs',jsonb_build_array(cp7_wip.ref('erp.bb_purchase_commitment_lines_v1',v_line->>'id',v_line->>'remaining'))));
     end loop;
    end if;
   end if;
  elsif(pool->>'free')::numeric=0 and jsonb_array_length(pool->'incoming')=0 then null; -- nothing shared to split
  else code:=case when unresolved>0 then 'FABRIC_OTHER_NEEDS_UNREVIEWED'when not certain then 'FABRIC_SHARED_NEED_UNKNOWN'
   else 'FABRIC_SHARED_SUPPLY_SPLIT_UNDECIDED'end;
  end if;
  if code is null then
   supplies:=jsonb_build_array(jsonb_build_object('physical_key','FABRIC_ALLOCATED:'||t,'kind','UNUSED','quantity',trim_scale(unused)::text,
    'verified_eligible_allocated',true,'eta',null,'refs',case when jsonb_array_length(unused_refs)=0
     then jsonb_build_array(cp7_wip.ref('CP7_FABRIC_NO_ALLOCATION',t,mat))else unused_refs end))||supplies;
   kernel:=cp7_baseline.material(jsonb_build_object('contract_version','cp7.material-need-input.v1','snapshot_id','FABRIC:'||(c->>'captured_at'),
    'scope_id','GLOBAL_NATIVE_PLANNING','material_id',mat,'unit',cl->'unit','gross_need',cl->'gross','proven_installed',to_jsonb('0'::text),
    'deadline',case when cl->>'deadline'is null then to_jsonb(cp7_planning.utc(captured))else cl->'deadline'end,'supplies',supplies,
    'refs',jsonb_build_array(cl->'recipe_ref')));
   if kernel->>'status'='SCENARIO'then ext:=kernel->>'external_need';ext_refs:=unused_refs||ext_refs;
    -- With installation unproved the kernel ran on installed0, so its value
    -- is only an upper bound: never a purchase quantity, always UNKNOWN.
    if cl->>'installed'is null then
     upper:=ext;ext:=null;code:='FABRIC_WIP_IDENTITY_UNRESOLVED';ext_refs:='[]';end if;
   else code:=case when exists(select 1 from jsonb_array_elements(supplies)x where x->>'kind'='INCOMING'and x->'eta'='null'::jsonb)
    then 'FABRIC_INCOMING_ETA_UNKNOWN'else 'FABRIC_PHYSICAL_NOT_PROVEN'end;ext_refs:='[]';end if;
  else ext_refs:='[]';end if;
  results:=array_append(results,cl||jsonb_build_object('unused',case when unused is null then null else trim_scale(unused)::text end,
   'unused_basis',basis,'unused_refs',unused_refs,'external',ext,'external_code',code,'external_refs',ext_refs,'external_upper_bound',upper,
   'free',pool->'free','incoming_lines',coalesce(jsonb_array_length(pool->'incoming'),0),'unresolved_other_rows',unresolved,
   'material_claimants',coalesce((stat->>'claimants')::integer,0)));
 end loop;
 return jsonb_build_object('index',ix,'physical_source',true,
  'targets',coalesce((select jsonb_object_agg(x->>'target_key',x)from unnest(results)x),'{}'::jsonb));
end $$;

create function cp7_fabric_native.needs(c jsonb,r jsonb,assumptions jsonb,plan jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare st jsonb:=cp7_fabric_native.recipe_state(plan->'index',r);recipe jsonb:=nullif(st->'recipe','null'::jsonb);
 m jsonb:=nullif(st->'material','null'::jsonb);p jsonb:=nullif(st->'pattern','null'::jsonb);
 refs jsonb:=(r->'refs')||(st->'refs');ids jsonb:=assumptions;gross text:=st->>'gross';x jsonb;
 unit text:='MATERIAL_BASE_UNIT';material text:='FABRIC_UNREVIEWED:'||(r->>'target_key');
 reason text:='Resep kain untuk produk dan ukuran ini belum direview atau sudah berakhir; kebutuhan belum diketahui.';
 installed jsonb;unused jsonb;external jsonb;why text;
begin
 installed:=cp7_analysis_native.fact(null,unit,refs);unused:=installed;external:=installed;
 if recipe is not null then
  unit:=st->>'unit';material:='FABRIC_MATERIAL:'||(st->>'material_id');ids:=ids||jsonb_build_array(recipe->>'id');
  installed:=cp7_analysis_native.fact(null,unit,refs);unused:=installed;external:=installed;
  if gross is not null then
   x:=plan->'targets'->(r->>'target_key');
   reason:=(m->>'material_name')||': kebutuhan kain memakai pemakaian per PCS yang dipilih, bukan pemakaian aktual. '
    ||case when p is null then 'Pola belum dipilih. 'else 'Pola '||(p->>'pattern_code')||' versi '||(p->>'revision')||'. 'end;
   if x is null then
    reason:=reason||'Stok roll, draf potong dan PO terbuka belum tercatat pada hasil ini; pemasangan, sisa layak dan tambahan dari luar belum diketahui. ';
    installed:=installed||jsonb_build_object('reason','FABRIC_PHYSICAL_SOURCE_NOT_CAPTURED');unused:=installed;external:=installed;
   else
    if x->>'installed'is not null then installed:=cp7_analysis_native.fact(x->>'installed',unit,refs,ids);
     reason:=reason||'Terpasang dihitung nol karena kebutuhan ini hanya untuk PCS yang belum mulai dipotong. ';
    else installed:=installed||jsonb_build_object('reason',coalesce(x->>'installed_code','FABRIC_PHYSICAL_NOT_PROVEN'));
     reason:=reason||case x->>'installed_code'when 'FABRIC_WIP_IDENTITY_UNRESOLVED'
      then 'Ada WIP model dan ukuran yang sama yang belum pasti milik produk ini (warna/merek belum terbukti); kain yang sudah terpasang belum bisa dipastikan. '
      else 'Jumlah rencana belum diketahui. 'end;
    end if;
    if x->>'unused'is not null then
     unused:=cp7_analysis_native.fact(x->>'unused',unit,refs||(x->'unused_refs'),case when x->>'unused_basis'in('SUFFICIENT_FREE_STOCK','SINGLE_CLAIMANT_FREE_STOCK')then ids else '[]'::jsonb end);
     reason:=reason||case x->>'unused_basis'
      when 'SUFFICIENT_FREE_STOCK'then 'Sisa layak = draf potong ERP yang terhubung ke rencana produk ini ditambah bagian stok bebas di gudang bahan, karena stok bebas cukup untuk semua kebutuhan bahan ini. '
      when 'SINGLE_CLAIMANT_FREE_STOCK'then 'Sisa layak = draf potong ERP yang terhubung ke rencana produk ini ditambah seluruh stok bebas di gudang bahan, karena hanya produk ini yang membutuhkan bahan ini. '
      when 'DRAFT'then 'Sisa layak = draf potong ERP belum diposting yang terhubung ke rencana produk ini dan masih tertutup stok roll. '
      else 'Belum ada draf potong ERP yang terhubung ke rencana produk ini. 'end
      ||'Ini bukan reservasi stok; sisa di area potong yang belum dikembalikan tidak dihitung. ';
    else unused:=unused||jsonb_build_object('reason',coalesce(x->>'own_code',x->>'installed_code','FABRIC_LINKED_DRAFT_NOT_ELIGIBLE'));
     if x->>'own_code'is not null then reason:=reason||'Draf potong yang terhubung memakai roll yang bukan bahan resep, tidak siap, di luar gudang bahan aktif, atau stoknya tidak cukup untuk semua draf. ';end if;
    end if;
    if x->>'external'is not null then external:=cp7_analysis_native.fact(x->>'external',unit,refs||(x->'external_refs'),ids);
     reason:=reason||'Tambahan dari luar = kebutuhan dikurangi terpasang, sisa layak dan PO terbuka yang datang sebelum batas waktu'
      ||case when(x->>'incoming_lines')::integer>0 then ' ('||(x->>'incoming_lines')||' baris PO terbuka diperiksa)'else ''end
      ||'. PO di luar ERP tidak terlihat. ';
    else
     why:=coalesce(x->>'external_code',x->>'installed_code',x->>'own_code','FABRIC_PHYSICAL_NOT_PROVEN');
     external:=external||jsonb_build_object('reason',why);
     reason:=reason||case why
      when 'FABRIC_WIP_IDENTITY_UNRESOLVED'then 'Tambahan dari luar belum bisa dipastikan; paling banyak '
       ||coalesce(x->>'external_upper_bound','?')||' '||unit||' bila WIP sejenis itu bukan milik produk ini. Bila milik produk ini, kebutuhannya lebih kecil. Pastikan identitas WIP sebelum membeli. '
      when 'FABRIC_PRODUCTION_DISABLED'then 'Produksi baru produk ini sedang dihentikan; tambahan bahan tidak dihitung. '
      when 'FABRIC_STOCK_INCONSISTENT'then 'Stok roll bahan ini tidak konsisten (negatif atau beda bahan); periksa data stok dahulu. '
      when 'FABRIC_UNLINKED_NATIVE_DRAFT'then 'Ada draf potong ERP belum diposting yang memakai bahan ini tanpa terhubung ke rencana; pembagian stok belum pasti. '
      when 'FABRIC_OTHER_NEEDS_UNREVIEWED'then 'Ada '||(x->>'unresolved_other_rows')||' produk lain yang kebutuhan kainnya belum diketahui; stok bebas '||coalesce(x->>'free','?')||' '||unit||' dan PO terbuka bahan ini belum bisa dibagi dengan pasti. '
      when 'FABRIC_SHARED_NEED_UNKNOWN'then 'Kebutuhan produk lain untuk bahan ini belum diketahui; pembagian stok bebas dan PO belum pasti. '
      when 'FABRIC_SHARED_SUPPLY_SPLIT_UNDECIDED'then 'Bahan ini dibutuhkan '||(x->>'material_claimants')||' produk dan stok bebas '||coalesce(x->>'free','?')||' '||unit||' dan PO terbuka tidak cukup untuk semuanya; tentukan pembagian lewat draf potong. '
      when 'FABRIC_INCOMING_LOCATION_NOT_ELIGIBLE'then 'Ada PO terbuka bahan ini ke lokasi yang bukan gudang bahan aktif. '
      when 'FABRIC_DEADLINE_UNKNOWN'then 'Batas waktu kebutuhan belum diketahui; PO terbuka belum bisa dinilai tepat waktu. '
      when 'FABRIC_INCOMING_OVERDUE'then 'Ada PO terbuka bahan ini yang sudah lewat tanggal datang dan belum diterima; kedatangannya belum pasti. '
      when 'FABRIC_INCOMING_ETA_UNKNOWN'then 'Ada PO terbuka bahan ini tanpa tanggal datang; tambahan dari luar belum bisa dihitung. '
      else 'Tambahan dari luar belum bisa dihitung. 'end;
    end if;
   end if;
   reason:=reason||'Kemampuan produksi global belum terbukti.';
  else reason:='Sumber bahan/pola atau jumlah rencana berubah atau belum lengkap; review resep kain kembali.';end if;
 end if;
 return jsonb_build_array(jsonb_build_object('target_key',r->'target_key','material_key',material,
  'gross',cp7_analysis_native.fact(gross,unit,refs,ids),
  'installed_proven',installed,'unused_allocated_proven',unused,'additional_external',external,'reason',reason));
end $$;
alter function cp7_fabric_native.material_hash(jsonb)owner to cp7_capture;
alter function cp7_fabric_native.validate(jsonb,jsonb)owner to cp7_capture;
alter function cp7_fabric_native.source(jsonb,timestamptz)owner to cp7_capture;
alter function cp7_fabric_native.physical_source(jsonb,timestamptz)owner to cp7_capture;
alter function cp7_fabric_native.index(jsonb)owner to cp7_capture;
alter function cp7_fabric_native.recipe_state(jsonb,jsonb)owner to cp7_capture;
alter function cp7_fabric_native.plan(jsonb,jsonb)owner to cp7_capture;
alter function cp7_fabric_native.needs(jsonb,jsonb,jsonb,jsonb)owner to cp7_capture;
revoke all on all functions in schema cp7_fabric_native from public,anon,authenticated,service_role;
