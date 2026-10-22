-- SS-1 (owner D17-8, D17-9, 20 Oct 2026): the reorder point of each finished good computed with the experts' formula from
-- the ERP's own data, compared with the stock every minute, and the items at or under it handed to Pengingat sistem and
-- WhatsApp (cp7_alert_native, kind FG_AT_REORDER_POINT). Proposal: docs/cp7/wa/PROPOSAL_SAFETY_STOCK_R6_20261020.md;
-- formula: docs/cp7/benchmark-decisions.md (MIT ESD.260). Read-only toward Native: it writes only its own tables.
--
-- Item: one current, active product per identity root (the planning target key root:size).
-- * Free stock: GRADE_A + GRADE_B, every movement known now (physical_at and system_created_at <= now), every location,
--   reservations of draft sales already out: the accepted planning availability (NATIVE_SELLABLE_GRADE_A_AND_B).
-- * Daily demand: posted sales (movement SALE, not itself an inverse, no inverse known now) per complete WIB day of the
--   window (window_days, default 30, ending yesterday). Returns stay separate (the accepted history rule). A day counts
--   only when the item sold that day or had free stock at its start: a day out of stock is not a day of zero demand.
--   D = mean, sigma = sample standard deviation over the counted days; at least 14 counted days, else NOT_ENOUGH_DATA.
-- * Lead time L (days) per model: median of produced_at - cut_at over production lots of the last 365 days (origin
--   PRODUCTION, QC posted, cutting group issued), from at least 3 cutting groups; else the planning profile's lead_days
--   of the item (the owner's reviewed assumption); else NOT_ENOUGH_DATA. Waiting before cutting is not recorded.
-- * Safety stock: STATISTICAL z(service level) x sigma x sqrt(L), z 1.2816 / 1.6449 / 2.3263 for 90 / 95 / 99%; or DAYS
--   D x buffer_days when the item's planning profile sets buffer_days (never both).
-- * Reorder point = ceil(D x L + safety stock). A manual number of Owner/Admin replaces it (manual_points; 0 = never).
-- * In production: the accepted cutting WIP (cp7_wip capture + normalize, CUT pools, company-owned) of the item's model
--   and size, over the cutting groups of its production orders not FINISHED or CANCELLED (a finished order's remaining
--   WIP was closed to expense by the finish). Counted toward every item of that model and size, as the analysis does.
--   Cached per model; refreshed within a time budget, items near their point first.
-- * AT_OR_BELOW when free + in production <= reorder point (> 0); when in production is unknown, free <= point.
create schema cp7_stock_formula authorization cp7_capture;
revoke all on schema cp7_stock_formula from public,anon,authenticated,service_role;

-- Owner/Admin settings, append-only revisions; none saved: 95% and 30 days.
create table cp7_stock_formula.settings(
 revision bigint primary key check(revision>0),service_level numeric(3,2) not null check(service_level in(0.90,0.95,0.99)),
 window_days integer not null check(window_days between 14 and 365),reason text not null check(length(btrim(reason))between 1 and 500),
 actor uuid not null,request_id uuid not null unique,request_hash text not null check(request_hash~'^[0-9a-f]{64}$'),
 saved_at timestamptz not null default clock_timestamp());
-- Manual reorder points per item, append-only revisions; the latest is in force, null clears it (the formula again).
create table cp7_stock_formula.manual_points(
 root_id uuid not null,revision integer not null check(revision>0),size_id uuid not null,product_version_id uuid not null,
 reorder_point_pcs integer check(reorder_point_pcs between 0 and 10000000),reason text not null check(length(btrim(reason))between 1 and 500),
 actor uuid not null,request_id uuid not null unique,request_hash text not null check(request_hash~'^[0-9a-f]{64}$'),
 recorded_at timestamptz not null default clock_timestamp(),primary key(root_id,revision));
-- In production per model and size, the last time it was read.
create table cp7_stock_formula.wip_models(
 model_id uuid primary key,status text not null check(status in('COMPLETE','UNKNOWN')),reason text check(length(reason)<=80),
 groups integer not null check(groups>=0),sizes jsonb not null check(jsonb_typeof(sizes)='object'),
 computed_at timestamptz not null,millis integer not null check(millis>=0),check((status='COMPLETE')=(reason is null)));
-- The latest evaluation of every item; a row changes only when one of its values does.
create table cp7_stock_formula.evaluations(
 target_key text primary key,root_id uuid not null unique,size_id uuid not null,model_id uuid,product_id uuid not null,
 sku text not null,product_name text not null,size_code text,free_pcs numeric not null,sales_pcs numeric not null,
 counted_days integer not null,sale_days integer not null,daily_mean numeric,daily_sd numeric,
 lead_days numeric,lead_basis text check(lead_basis in('MEASURED','PROFILE')),lead_lots integer,lead_groups integer,
 buffer_mode text check(buffer_mode in('STATISTICAL','DAYS')),buffer_days numeric,z numeric,safety_pcs numeric,
 formula_point integer,manual_point integer,manual_revision integer,point integer,
 basis text not null check(basis in('MANUAL','FORMULA','NOT_ENOUGH_DATA','NO_SALES')),reason text check(length(reason)<=80),
 wip_pcs numeric,wip_status text check(wip_status in('COMPLETE','UNKNOWN','NOT_READ')),wip_reason text check(length(wip_reason)<=80),
 state text not null check(state in('AT_OR_BELOW','ABOVE','NO_POINT')),changed_at timestamptz not null,
 check((basis in('MANUAL','FORMULA'))=(point is not null)));
create table cp7_stock_formula.runs(
 id boolean primary key default true check(id),computed_at timestamptz not null,window_from date not null,window_through date not null,
 settings_revision bigint not null,service_level numeric not null,window_days integer not null,items integer not null,
 at_or_below integer not null,wip_read integer not null,materials integer not null,materials_at_or_below integer not null,
 millis integer not null);
do $$declare t text;begin
 foreach t in array array['settings','manual_points','wip_models','evaluations','runs']loop
  execute format('alter table cp7_stock_formula.%I owner to cp7_capture',t);
  execute format('alter table cp7_stock_formula.%I enable row level security',t);
  execute format('create policy formula_no_access on cp7_stock_formula.%I for all to public using(false)with check(false)',t);
  execute format('revoke all on cp7_stock_formula.%I from public,anon,authenticated,service_role',t);
 end loop;end $$;
create function cp7_stock_formula.append_only()returns trigger
language plpgsql security definer set search_path=''set TimeZone='UTC'as $$
begin raise exception 'CP7_FORMULA_APPEND_ONLY' using detail=tg_table_name;end $$;
create trigger settings_append_only before update or delete on cp7_stock_formula.settings for each row execute function cp7_stock_formula.append_only();
create trigger manual_points_append_only before update or delete on cp7_stock_formula.manual_points for each row execute function cp7_stock_formula.append_only();

create function cp7_stock_formula.z(p_level numeric)returns numeric
language sql immutable security definer set search_path=''set TimeZone='UTC'as $$
 select case p_level when 0.90 then 1.2816 when 0.95 then 1.6449 when 0.99 then 2.3263 end$$;
create function cp7_stock_formula.current_settings()returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select coalesce((select jsonb_build_object('revision',s.revision,'service_level',s.service_level::text,'window_days',s.window_days,'reason',s.reason,
   'saved_at',s.saved_at)from cp7_stock_formula.settings s order by s.revision desc limit 1),
  jsonb_build_object('revision',0,'service_level','0.95','window_days',30,'reason',null,'saved_at',null))$$;

-- Whether a model may have pieces in production now: a cutting group with its material issued, of an order of the model
-- not FINISHED or CANCELLED (the groups model_wip reads).
create function cp7_stock_formula.open_groups(p_model uuid,p_at timestamptz)returns boolean
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select exists(select 1 from erp.production_orders po join erp.cutting_groups g on g.po_id=po.id
  where po.model_id=p_model and po.status not in('FINISHED','CANCELLED')and g.material_issue_posted and g.cut_at<=p_at)$$;
-- In production of one model per size: the planning live reader's rule (plan-native staged_live) over the cutting groups
-- of the model's orders not FINISHED or CANCELLED. More than 200 groups, a capture not complete or a normalization that
-- refuses: UNKNOWN, never a guess.
create function cp7_stock_formula.model_wip(p_model uuid,p_at timestamptz)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare ids uuid[];n integer;bi integer:=1;part jsonb;norm jsonb;sizes jsonb:='{}';
begin
 select coalesce(array_agg(x.id order by x.id),'{}'::uuid[]),count(*)into ids,n from(
  select g.id from erp.cutting_groups g join erp.production_orders po on po.id=g.po_id
  where po.model_id=p_model and po.status not in('FINISHED','CANCELLED')and g.material_issue_posted and g.cut_at<=p_at
  order by g.id limit 201)x;
 if n>200 then return jsonb_build_object('status','UNKNOWN','reason','MODEL_WIP_GROUP_LIMIT','groups',n,'sizes','{}'::jsonb);end if;
 while bi<=n loop
  part:=cp7_wip.capture_cutting_sources(ids[bi:least(bi+49,n)],p_at);
  if part->>'status'is distinct from'COMPLETE'then
   return jsonb_build_object('status','UNKNOWN','reason','WIP_SOURCE_INCOMPLETE','groups',n,'sizes','{}'::jsonb);end if;
  begin norm:=cp7_wip.normalize_cutting(part);
  exception when others then return jsonb_build_object('status','UNKNOWN','reason','WIP_NORMALIZATION_REFUSED','groups',n,'sizes','{}'::jsonb);
  end;
  if norm->>'status'is distinct from'COMPLETE'then
   return jsonb_build_object('status','UNKNOWN','reason',left(coalesce(norm->>'reason','WIP_NOT_COMPLETE'),80),'groups',n,'sizes','{}'::jsonb);end if;
  select coalesce(jsonb_object_agg(y.k,y.v),'{}')into sizes from(
   select z.k,sum(z.v)v from(select e.key k,(e.value#>>'{}')::numeric v from jsonb_each(sizes)e
    union all select t->>'size_id',(t->>'wip_pcs')::numeric from jsonb_array_elements(norm->'totals')t
     where t->>'pool_key'like'CUT:%'and t->>'ownership'='COMPANY'and t->>'size_id'is not null)z group by z.k)y;
  bi:=bi+50;
 end loop;
 return jsonb_build_object('status','COMPLETE','reason',null,'groups',n,'sizes',sizes);
end $$;

-- Every item evaluated at p_at. In production is read for the models of items at or under their point first (when its
-- last read is older than 55 s), then for the other models with orders in production (older than 10 minutes), while
-- p_budget lasts; a model not reached keeps its last read and its time. The caller holds the module lock.
-- jit off: the planner's estimate of the day series is far above the real rows (thousands), and JIT compilation alone
-- took about 3 s of a 3.7 s evaluation of 2,000 items and 202,000 movements (local measurement); the work itself is
-- about 0.6 s.
create function cp7_stock_formula.compute(p_at timestamptz,p_budget interval)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'set jit=off as $$
declare cfg jsonb:=cp7_stock_formula.current_settings();sl numeric;zv numeric;w integer;today date;d0 date;t0 timestamptz;t1 timestamptz;
 started timestamptz:=clock_timestamp();deadline timestamptz:=clock_timestamp()+p_budget;mdl record;got jsonb;wip_read integer:=0;n_items integer;n_low integer;
 mats jsonb;
begin
 sl:=(cfg->>'service_level')::numeric;zv:=cp7_stock_formula.z(sl);w:=(cfg->>'window_days')::integer;
 today:=(p_at at time zone'Asia/Jakarta')::date;d0:=today-w;
 t0:=d0::timestamp at time zone'Asia/Jakarta';t1:=today::timestamp at time zone'Asia/Jakarta';
 with cur as(
  select coalesce(p.identity_root_id,p.id)root_id,p.id product_id,p.size_id,p.model_id,p.sku::text sku,p.product_name::text product_name,p.is_active,
   count(*)over(partition by coalesce(p.identity_root_id,p.id))n
  from erp.products p where p.effective_from<=p_at and(p.effective_to is null or p.effective_to>p_at)),
 items as materialized(
  select c.root_id,c.product_id,c.size_id,c.model_id,c.sku,c.product_name,s.size_code::text size_code,c.root_id::text||':'||c.size_id::text target_key
  from cur c left join erp.sizes s on s.id=c.size_id where c.n=1 and c.is_active),
 bal as materialized(
  select coalesce(p.identity_root_id,p.id)root_id,sum(m.qty_signed)::numeric free,coalesce(sum(m.qty_signed)filter(where m.physical_at<t0),0)::numeric opening
  from erp.fg_stock_movements m join erp.products p on p.id=m.product_id
  where m.quality_grade in('GRADE_A','GRADE_B')and m.physical_at<=p_at and m.system_created_at<=p_at group by 1),
 net as materialized(
  select coalesce(p.identity_root_id,p.id)root_id,(m.physical_at at time zone'Asia/Jakarta')::date as day,sum(m.qty_signed)::numeric pcs
  from erp.fg_stock_movements m join erp.products p on p.id=m.product_id
  where m.quality_grade in('GRADE_A','GRADE_B')and m.physical_at>=t0 and m.physical_at<t1 and m.system_created_at<=p_at group by 1,2),
 sold as materialized(
  select coalesce(p.identity_root_id,p.id)root_id,(m.physical_at at time zone'Asia/Jakarta')::date as day,sum(-m.qty_signed)::numeric pcs
  from erp.fg_stock_movements m join erp.products p on p.id=m.product_id
  where m.movement_type='SALE'and m.reversal_of_id is null and m.qty_signed<0 and m.physical_at>=t0 and m.physical_at<t1 and m.system_created_at<=p_at
   and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id and rv.physical_at<=p_at and rv.system_created_at<=p_at)
  group by 1,2),
 series as(
  select x.root_id,x.day,coalesce(s.pcs,0)pcs,
   coalesce(b.opening,0)+coalesce(sum(coalesce(n.pcs,0))over(partition by x.root_id order by x.day rows between unbounded preceding and 1 preceding),0)start_free
  from(select r.root_id,g::date as day from(select distinct root_id from sold)r cross join generate_series(d0,today-1,interval'1 day')g)x
  left join sold s on s.root_id=x.root_id and s.day=x.day left join net n on n.root_id=x.root_id and n.day=x.day
  left join bal b on b.root_id=x.root_id),
 stats as materialized(
  select y.root_id,count(*)filter(where y.pcs>0 or y.start_free>0)counted,count(*)filter(where y.pcs>0)sale_days,sum(y.pcs)total,
   avg(y.pcs)filter(where y.pcs>0 or y.start_free>0)mean,stddev_samp(y.pcs)filter(where y.pcs>0 or y.start_free>0)sd
  from series y group by y.root_id),
 lead_obs as(
  select po.model_id,g.id group_id,extract(epoch from l.produced_at-g.cut_at)/86400.0 days
  from erp.fg_lots l join erp.cutting_groups g on g.id=l.cutting_group_id join erp.production_orders po on po.id=g.po_id
  join erp.qc_inspection_items qi on qi.id=l.qc_item_id join erp.qc_inspections q on q.id=qi.inspection_id
  where l.lot_origin='PRODUCTION'and q.status='POSTED'and g.material_issue_posted and l.produced_at<=p_at
   and l.produced_at>p_at-interval'365 days'and l.produced_at>=g.cut_at),
 lead as materialized(
  select o.model_id,round(percentile_cont(0.5)within group(order by o.days)::numeric,2)med,count(*)lots,count(distinct o.group_id)groups
  from lead_obs o group by o.model_id),
 prof as materialized(
  select distinct on(x.root_id)x.root_id,x.product_version_id,x.config from cp7_profile.profiles x
  where x.recorded_at<=p_at order by x.root_id,x.revision desc),
 man as materialized(
  select distinct on(x.root_id)x.root_id,x.revision,x.reorder_point_pcs from cp7_stock_formula.manual_points x order by x.root_id,x.revision desc),
 calc as(
  select i.*,coalesce(b.free,0)free,coalesce(st.total,0)sales_pcs,coalesce(st.counted,0)counted,coalesce(st.sale_days,0)sale_days,st.mean,
   case when st.counted>=2 then st.sd end sd,
   case when ld.groups>=3 then ld.med when pf.product_version_id=i.product_id and pf.config->>'lead_days'is not null
    and(pf.config->>'lead_days')::numeric>0 then(pf.config->>'lead_days')::numeric end lead_days,
   case when ld.groups>=3 then'MEASURED'when pf.product_version_id=i.product_id and pf.config->>'lead_days'is not null
    and(pf.config->>'lead_days')::numeric>0 then'PROFILE'end lead_basis,ld.lots lead_lots,ld.groups lead_groups,
   case when pf.product_version_id=i.product_id and pf.config->>'buffer_days'is not null then'DAYS'else'STATISTICAL'end buffer_mode,
   case when pf.product_version_id=i.product_id and pf.config->>'buffer_days'is not null then(pf.config->>'buffer_days')::numeric end buffer_days,
   mn.revision manual_revision,mn.reorder_point_pcs manual_point
  from items i left join bal b on b.root_id=i.root_id left join stats st on st.root_id=i.root_id
  left join lead ld on ld.model_id=i.model_id left join prof pf on pf.root_id=i.root_id left join man mn on mn.root_id=i.root_id),
 formula as(
  select c.*,zv z,
   case when c.sales_pcs>0 and c.counted>=14 and c.lead_days is not null then
    case c.buffer_mode when'DAYS'then c.mean*c.buffer_days else zv*coalesce(c.sd,0)*sqrt(c.lead_days)end end safety
  from calc c),
 final as(
  -- Exact: total x lead / counted days (multiply before dividing), never the rounded mean times the lead time; a DAYS
  -- buffer is one product (total x (lead + buffer) / counted), so a whole number of pieces is never pushed up by one.
  select f.*,case when f.safety is not null then case f.buffer_mode when'DAYS'then ceil(f.sales_pcs*(f.lead_days+f.buffer_days)/f.counted)
    else ceil(f.sales_pcs*f.lead_days/f.counted+f.safety)end::integer end formula_point,
   case when f.manual_point is not null then'MANUAL'when f.sales_pcs<=0 then'NO_SALES'when f.counted<14 or f.lead_days is null then'NOT_ENOUGH_DATA'
    else'FORMULA'end basis,
   case when f.manual_point is not null then null when f.sales_pcs<=0 then'NO_POSTED_SALES_IN_WINDOW'when f.counted<14 then'FEWER_THAN_14_COUNTED_DAYS'
    when f.lead_days is null then'NO_LEAD_TIME'end reason
  from formula f)
 ,ins as(
 insert into cp7_stock_formula.evaluations as e(target_key,root_id,size_id,model_id,product_id,sku,product_name,size_code,free_pcs,sales_pcs,
  counted_days,sale_days,daily_mean,daily_sd,lead_days,lead_basis,lead_lots,lead_groups,buffer_mode,buffer_days,z,safety_pcs,formula_point,
  manual_point,manual_revision,point,basis,reason,state,changed_at)
 select x.target_key,x.root_id,x.size_id,x.model_id,x.product_id,x.sku,x.product_name,x.size_code,x.free,x.sales_pcs,x.counted,x.sale_days,
  round(x.mean,4),round(x.sd,4),x.lead_days,x.lead_basis,x.lead_lots,x.lead_groups,x.buffer_mode,x.buffer_days,x.z,round(x.safety,4),x.formula_point,
  x.manual_point,x.manual_revision,case x.basis when'MANUAL'then x.manual_point when'FORMULA'then x.formula_point end,x.basis,x.reason,'NO_POINT',p_at
 from final x
 on conflict(target_key)do update set root_id=excluded.root_id,size_id=excluded.size_id,model_id=excluded.model_id,product_id=excluded.product_id,
  sku=excluded.sku,product_name=excluded.product_name,size_code=excluded.size_code,free_pcs=excluded.free_pcs,sales_pcs=excluded.sales_pcs,
  counted_days=excluded.counted_days,sale_days=excluded.sale_days,daily_mean=excluded.daily_mean,daily_sd=excluded.daily_sd,lead_days=excluded.lead_days,
  lead_basis=excluded.lead_basis,lead_lots=excluded.lead_lots,lead_groups=excluded.lead_groups,buffer_mode=excluded.buffer_mode,
  buffer_days=excluded.buffer_days,z=excluded.z,safety_pcs=excluded.safety_pcs,formula_point=excluded.formula_point,manual_point=excluded.manual_point,
  manual_revision=excluded.manual_revision,point=excluded.point,basis=excluded.basis,reason=excluded.reason,changed_at=p_at
 where(e.root_id,e.size_id,e.model_id,e.product_id,e.sku,e.product_name,e.size_code,e.free_pcs,e.sales_pcs,e.counted_days,e.sale_days,e.daily_mean,
  e.daily_sd,e.lead_days,e.lead_basis,e.lead_lots,e.lead_groups,e.buffer_mode,e.buffer_days,e.z,e.safety_pcs,e.formula_point,e.manual_point,
  e.manual_revision,e.point,e.basis,e.reason)is distinct from(excluded.root_id,excluded.size_id,excluded.model_id,excluded.product_id,excluded.sku,
  excluded.product_name,excluded.size_code,excluded.free_pcs,excluded.sales_pcs,excluded.counted_days,excluded.sale_days,excluded.daily_mean,
  excluded.daily_sd,excluded.lead_days,excluded.lead_basis,excluded.lead_lots,excluded.lead_groups,excluded.buffer_mode,excluded.buffer_days,
  excluded.z,excluded.safety_pcs,excluded.formula_point,excluded.manual_point,excluded.manual_revision,excluded.point,excluded.basis,excluded.reason)
 returning 1)
 -- An item no longer current (inactive, ended, or two current versions of its root) leaves the evaluation.
 delete from cp7_stock_formula.evaluations e where not exists(select 1 from items i where i.target_key=e.target_key);
 -- In production is read only for a model with pieces possibly in production (a cutting group issued, of an order not
 -- FINISHED or CANCELLED); any other model has none, known without reading.
 for mdl in
  select y.model_id from(
   select e.model_id,(e.point>0 and e.free_pcs<=e.point)near from cp7_stock_formula.evaluations e where e.model_id is not null
   union all select po.model_id,false from erp.production_orders po where po.status not in('FINISHED','CANCELLED')and po.model_id is not null)y
  left join cp7_stock_formula.wip_models c on c.model_id=y.model_id
  where y.model_id in(select po.model_id from erp.production_orders po join erp.cutting_groups g on g.po_id=po.id
   where po.status not in('FINISHED','CANCELLED')and g.material_issue_posted and g.cut_at<=p_at)
  group by y.model_id,c.computed_at
  having c.computed_at is null or c.computed_at<p_at-case when bool_or(y.near)then interval'55 seconds'else interval'10 minutes'end
  order by bool_or(y.near)desc,c.computed_at nulls first,y.model_id
 loop
  exit when clock_timestamp()>deadline;
  started:=clock_timestamp();
  got:=cp7_stock_formula.model_wip(mdl.model_id,p_at);
  insert into cp7_stock_formula.wip_models as x(model_id,status,reason,groups,sizes,computed_at,millis)
  values(mdl.model_id,got->>'status',got->>'reason',(got->>'groups')::integer,got->'sizes',p_at,(extract(epoch from clock_timestamp()-started)*1000)::integer)
  on conflict(model_id)do update set status=excluded.status,reason=excluded.reason,groups=excluded.groups,sizes=excluded.sizes,
   computed_at=excluded.computed_at,millis=excluded.millis;
  wip_read:=wip_read+1;
 end loop;
 with open_models as materialized(
  select distinct po.model_id from erp.production_orders po join erp.cutting_groups g on g.po_id=po.id
  where po.status not in('FINISHED','CANCELLED')and g.material_issue_posted and g.cut_at<=p_at),
 v as(
  select e.target_key,e.point,e.free_pcs,o.open,
   case when e.model_id is null then'UNKNOWN'when not o.open then'COMPLETE'when c.model_id is null then'NOT_READ'else c.status end wip_status,
   case when e.model_id is not null and not o.open then 0 when o.open and c.status='COMPLETE'then coalesce((c.sizes->>e.size_id::text)::numeric,0)end wip_pcs,
   case when e.model_id is null then'PRODUCT_WITHOUT_MODEL'when not o.open then null when c.model_id is null then'NOT_READ_YET'else c.reason end wip_reason
  from cp7_stock_formula.evaluations e left join cp7_stock_formula.wip_models c on c.model_id=e.model_id
  cross join lateral(select e.model_id is not null and e.model_id in(select m.model_id from open_models m)open)o),
 s as(
  select v.*,case when v.point is null or v.point<=0 then'NO_POINT'
   when v.wip_status='COMPLETE'and v.free_pcs+v.wip_pcs<=v.point then'AT_OR_BELOW'
   when v.wip_status<>'COMPLETE'and v.free_pcs<=v.point then'AT_OR_BELOW'else'ABOVE'end state from v)
 update cp7_stock_formula.evaluations e set wip_pcs=s.wip_pcs,wip_status=s.wip_status,wip_reason=s.wip_reason,state=s.state,changed_at=p_at
 from s where s.target_key=e.target_key and(e.wip_pcs,e.wip_status,e.wip_reason,e.state)is distinct from(s.wip_pcs,s.wip_status,s.wip_reason,s.state);
 select count(*),count(*)filter(where state='AT_OR_BELOW')into n_items,n_low from cp7_stock_formula.evaluations;
 mats:=cp7_stock_formula.compute_materials(p_at);
 insert into cp7_stock_formula.runs as x(id,computed_at,window_from,window_through,settings_revision,service_level,window_days,items,at_or_below,wip_read,
  materials,materials_at_or_below,millis)
 values(true,p_at,d0,today-1,(cfg->>'revision')::bigint,sl,w,n_items,n_low,wip_read,(mats->>'materials')::integer,(mats->>'materials_at_or_below')::integer,
  (extract(epoch from clock_timestamp()-p_at)*1000)::integer)
 on conflict(id)do update set computed_at=excluded.computed_at,window_from=excluded.window_from,window_through=excluded.window_through,
  settings_revision=excluded.settings_revision,service_level=excluded.service_level,window_days=excluded.window_days,items=excluded.items,
  at_or_below=excluded.at_or_below,wip_read=excluded.wip_read,materials=excluded.materials,materials_at_or_below=excluded.materials_at_or_below,
  millis=excluded.millis;
 return jsonb_build_object('computed_at',p_at,'items',n_items,'at_or_below',n_low,'wip_read',wip_read)||mats;
end $$;

-- An item as Pengingat sistem shows it (an evaluation row as jsonb): the numbers only, no time, so the alert is refreshed
-- only when a number changes.
create function cp7_stock_formula.alert_row(e jsonb,p_level numeric)returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('subject_key',e->>'target_key','title','Stok barang jadi menipis: '||(e->>'product_name')||coalesce(' '||(e->>'size_code'),''),
  'detail',jsonb_build_object('root_id',e->'root_id','size_id',e->'size_id','sku',e->'sku','product_name',e->'product_name','size_code',e->'size_code',
   'free_pcs',(e->>'free_pcs')::numeric::text,'wip_pcs',(e->>'wip_pcs')::numeric::text,'wip_status',e->'wip_status',
   'position_pcs',case when e->>'wip_status'='COMPLETE'then((e->>'free_pcs')::numeric+(e->>'wip_pcs')::numeric)::text end,
   'reorder_point_pcs',e->>'point','basis',e->'basis','daily_mean',round((e->>'daily_mean')::numeric,2)::text,'lead_days',(e->>'lead_days')::numeric::text,
   'lead_basis',e->'lead_basis','buffer_mode',case when e->>'basis'='FORMULA'then e->'buffer_mode'end,
   'safety_pcs',case when e->>'basis'='FORMULA'then round((e->>'safety_pcs')::numeric,1)::text end,
   'service_level',case when e->>'basis'='FORMULA'and e->>'buffer_mode'='STATISTICAL'then p_level::text end),
  'party_names','[]'::jsonb)$$;
-- The source of FG_AT_REORDER_POINT for cp7_alert_native, read with the identity of the owner who saved the WhatsApp
-- settings: the Ringkasan Barang Jadi permission. The first source of a tick that takes the module lock evaluates every
-- item (ensure_computed, materials.sql); a caller that finds it held (the other tick, or an owner's save) checks the
-- items at or under their point in the last evaluation against the free stock now, with that evaluation's point and
-- in-production read, and writes nothing.
create function cp7_stock_formula.fg_source()returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare r jsonb;lvl numeric:=(cp7_stock_formula.current_settings()->>'service_level')::numeric;t timestamptz:=clock_timestamp();
begin
 if erp.has_permission('warehouse.fg.view')is not true then raise exception using errcode='42501',message='CP7_FORMULA_FG_SOURCE_DENIED';end if;
 if cp7_stock_formula.ensure_computed()then
  select jsonb_build_object(
   'rows',coalesce(jsonb_agg(cp7_stock_formula.alert_row(to_jsonb(e),lvl)order by e.sku,e.target_key)filter(where e.state='AT_OR_BELOW'),'[]'),
   'states',coalesce(jsonb_object_agg(e.target_key,case when e.state='ABOVE'then'ABOVE_REORDER_POINT'else'NO_REORDER_POINT'end)
    filter(where e.state<>'AT_OR_BELOW'),'{}'))into r from cp7_stock_formula.evaluations e;
  return r;
 end if;
 with low as(select e.target_key,e.root_id,e.sku,e.point,e.wip_pcs,e.wip_status,to_jsonb(e)j from cp7_stock_formula.evaluations e where e.state='AT_OR_BELOW'),
 live as(select l.*,coalesce((select sum(m.qty_signed)from erp.fg_stock_movements m join erp.products p on p.id=m.product_id
   where coalesce(p.identity_root_id,p.id)=l.root_id and m.quality_grade in('GRADE_A','GRADE_B')and m.physical_at<=t and m.system_created_at<=t),0)::numeric free
  from low l),
 now_state as(select v.*,(v.wip_status='COMPLETE'and v.free+v.wip_pcs<=v.point)or(v.wip_status<>'COMPLETE'and v.free<=v.point)still from live v)
 select jsonb_build_object(
  'rows',coalesce(jsonb_agg(cp7_stock_formula.alert_row(n.j||jsonb_build_object('free_pcs',n.free),lvl)order by n.sku,n.target_key)filter(where n.still),'[]'),
  'states',coalesce(jsonb_object_agg(n.target_key,'ABOVE_REORDER_POINT')filter(where not n.still),'{}'))into r from now_state n;
 return jsonb_set(r,'{states}',(r->'states')||coalesce((select jsonb_object_agg(e.target_key,case when e.state='ABOVE'then'ABOVE_REORDER_POINT'else'NO_REORDER_POINT'end)
  from cp7_stock_formula.evaluations e where e.state<>'AT_OR_BELOW'),'{}'));
end $$;

-- --------------------------------------------------------------- the RPCs --
-- Read: an active ERP user with the Ringkasan Barang Jadi permission. Change: Owner or Admin with it.
create function cp7_stock_formula.access_now(p_manage boolean)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;
begin
 if auth.uid()is null or coalesce(auth.jwt()->>'role','')<>'authenticated'then raise exception using errcode='42501',message='CP7_FORMULA_ACCESS_DENIED';end if;
 a:=erp.get_my_access_v1();
 if a->'allowed'is distinct from'true'::jsonb or erp.has_permission('warehouse.fg.view')is not true
  or(p_manage and coalesce(a->'profile'->>'role_code','')not in('OWNER','ADMIN'))then
  raise exception using errcode='42501',message='CP7_FORMULA_ACCESS_DENIED';end if;
 return a;
end $$;
create function cp7_stock_formula.workspace(p jsonb)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;q text;f text;off integer;n integer;total bigint;rows jsonb;
begin
 a:=cp7_stock_formula.access_now(false);
 if jsonb_typeof(p)is distinct from'object'or exists(select 1 from jsonb_object_keys(p)k where k not in('q','filter','offset','limit'))
  or(p?'q'and jsonb_typeof(p->'q')<>'string')or(p?'filter'and(jsonb_typeof(p->'filter')<>'string'
   or p->>'filter'not in('ALL','AT_OR_BELOW','MANUAL','NOT_ENOUGH_DATA')))
  or(p?'offset'and(jsonb_typeof(p->'offset')<>'number'or(p->>'offset')!~'^[0-9]{1,7}$'))
  or(p?'limit'and(jsonb_typeof(p->'limit')<>'number'or(p->>'limit')!~'^[0-9]{1,3}$'))then raise exception using errcode='22023',message='CP7_FORMULA_QUERY';end if;
 q:=lower(btrim(coalesce(p->>'q','')));f:=coalesce(p->>'filter','ALL');off:=coalesce((p->>'offset')::integer,0);n:=coalesce((p->>'limit')::integer,25);
 if length(q)>120 or n not between 1 and 100 then raise exception using errcode='22023',message='CP7_FORMULA_QUERY';end if;
 select count(*)into total from cp7_stock_formula.evaluations e
 where(q=''or strpos(lower(concat_ws(' ',e.sku,e.product_name,e.size_code)),q)>0)
  and(f='ALL'or(f='AT_OR_BELOW'and e.state='AT_OR_BELOW')or(f='MANUAL'and e.basis='MANUAL')or(f='NOT_ENOUGH_DATA'and e.basis='NOT_ENOUGH_DATA'));
 select coalesce(jsonb_agg(to_jsonb(x)-'ord'order by x.ord,x.sku,x.target_key),'[]')into rows from(
  select e.*,case when e.model_id is not null and cp7_stock_formula.open_groups(e.model_id,statement_timestamp())then c.computed_at end wip_read_at,
   case e.state when'AT_OR_BELOW'then 0 when'ABOVE'then 1 else 2 end ord
  from cp7_stock_formula.evaluations e left join cp7_stock_formula.wip_models c on c.model_id=e.model_id
  where(q=''or strpos(lower(concat_ws(' ',e.sku,e.product_name,e.size_code)),q)>0)
   and(f='ALL'or(f='AT_OR_BELOW'and e.state='AT_OR_BELOW')or(f='MANUAL'and e.basis='MANUAL')or(f='NOT_ENOUGH_DATA'and e.basis='NOT_ENOUGH_DATA'))
  order by ord,e.sku,e.target_key limit n offset off)x;
 return jsonb_build_object('contract_version','cp7.fg-reorder.v1','read_at',statement_timestamp(),'settings',cp7_stock_formula.current_settings(),
  'run',(select to_jsonb(r)-'id'from cp7_stock_formula.runs r),'can_manage',coalesce(a->'profile'->>'role_code','')in('OWNER','ADMIN'),
  'counts',(select jsonb_build_object('items',count(*),'at_or_below',count(*)filter(where e.state='AT_OR_BELOW'),'manual',count(*)filter(where e.basis='MANUAL'),
    'formula',count(*)filter(where e.basis='FORMULA'),'not_enough_data',count(*)filter(where e.basis='NOT_ENOUGH_DATA'),'no_sales',count(*)filter(where e.basis='NO_SALES'))
   from cp7_stock_formula.evaluations e),
  'page',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',n,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows)end));
end $$;
-- Evaluate every item now (the same evaluation as the tick); refused while another evaluation runs.
create function cp7_stock_formula.refresh()returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 perform cp7_stock_formula.access_now(false);
 if not pg_try_advisory_xact_lock(hashtextextended('CP7:FORMULA:FG',0))then raise exception using errcode='55P03',message='CP7_FORMULA_BUSY';end if;
 return cp7_stock_formula.compute(clock_timestamp(),interval'3 seconds');
end $$;
create function cp7_stock_formula.save_manual(p jsonb,p_request uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;h text;prev cp7_stock_formula.manual_points;root uuid;cur_rev integer;prod record;row cp7_stock_formula.manual_points;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_stock_formula.access_now(true);
 if p_request is null then raise exception using errcode='22023',message='CP7_FORMULA_REQUEST_REQUIRED';end if;
 h:=encode(sha256(convert_to(coalesce(p::text,''),'UTF8')),'hex');
 perform pg_advisory_xact_lock(hashtextextended('CP7:FORMULA:FG',0));
 select*into prev from cp7_stock_formula.manual_points x where x.request_id=p_request;
 if found then
  if prev.actor<>auth.uid()or prev.request_hash<>h then raise exception using errcode='22023',message='CP7_FORMULA_REQUEST_REUSED';end if;
  return jsonb_build_object('replay',true,'root_id',prev.root_id,'revision',prev.revision,'reorder_point_pcs',prev.reorder_point_pcs);
 end if;
 if jsonb_typeof(p)is distinct from'object'or not p?&array['root_id','expected_revision','reorder_point_pcs','reason']
  or exists(select 1 from jsonb_object_keys(p)k where k not in('root_id','expected_revision','reorder_point_pcs','reason'))
  or jsonb_typeof(p->'root_id')<>'string'or(p->>'root_id')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or jsonb_typeof(p->'expected_revision')<>'number'or(p->>'expected_revision')!~'^[0-9]{1,9}$'
  or jsonb_typeof(p->'reorder_point_pcs')not in('number','null')or coalesce(p->>'reorder_point_pcs','0')!~'^[0-9]{1,8}$'
  or jsonb_typeof(p->'reason')<>'string'or length(btrim(p->>'reason'))not between 1 and 500
 then raise exception using errcode='22023',message='CP7_FORMULA_MANUAL_INVALID';end if;
 root:=(p->>'root_id')::uuid;
 select p2.id,p2.size_id into prod from erp.products p2 where coalesce(p2.identity_root_id,p2.id)=root and p2.is_active
  and p2.effective_from<=clock_timestamp()and(p2.effective_to is null or p2.effective_to>clock_timestamp());
 if prod.id is null or(select count(*)from erp.products q where coalesce(q.identity_root_id,q.id)=root and q.effective_from<=clock_timestamp()
  and(q.effective_to is null or q.effective_to>clock_timestamp()))<>1 then raise exception using errcode='22023',message='CP7_FORMULA_ITEM_UNKNOWN';end if;
 select coalesce(max(x.revision),0)into cur_rev from cp7_stock_formula.manual_points x where x.root_id=root;
 if cur_rev<>(p->>'expected_revision')::integer then raise exception using errcode='40001',message='CP7_FORMULA_MANUAL_STALE';end if;
 insert into cp7_stock_formula.manual_points(root_id,revision,size_id,product_version_id,reorder_point_pcs,reason,actor,request_id,request_hash)
 values(root,cur_rev+1,prod.size_id,prod.id,(p->>'reorder_point_pcs')::integer,btrim(p->>'reason'),auth.uid(),p_request,h)returning*into row;
 perform cp7_stock_formula.compute(clock_timestamp(),interval'1 second');
 return jsonb_build_object('replay',false,'root_id',row.root_id,'revision',row.revision,'reorder_point_pcs',row.reorder_point_pcs,
  'evaluation',(select to_jsonb(e)from cp7_stock_formula.evaluations e where e.root_id=root));
end $$;
create function cp7_stock_formula.save_settings(p jsonb,p_request uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;h text;prev cp7_stock_formula.settings;cur_rev bigint;row cp7_stock_formula.settings;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_stock_formula.access_now(true);
 if p_request is null then raise exception using errcode='22023',message='CP7_FORMULA_REQUEST_REQUIRED';end if;
 h:=encode(sha256(convert_to(coalesce(p::text,''),'UTF8')),'hex');
 perform pg_advisory_xact_lock(hashtextextended('CP7:FORMULA:FG',0));
 select*into prev from cp7_stock_formula.settings x where x.request_id=p_request;
 if found then
  if prev.actor<>auth.uid()or prev.request_hash<>h then raise exception using errcode='22023',message='CP7_FORMULA_REQUEST_REUSED';end if;
  return jsonb_build_object('replay',true,'settings',cp7_stock_formula.current_settings());
 end if;
 if jsonb_typeof(p)is distinct from'object'or not p?&array['expected_revision','service_level','window_days','reason']
  or exists(select 1 from jsonb_object_keys(p)k where k not in('expected_revision','service_level','window_days','reason'))
  or jsonb_typeof(p->'expected_revision')<>'number'or(p->>'expected_revision')!~'^[0-9]{1,9}$'
  or jsonb_typeof(p->'service_level')<>'string'or p->>'service_level'not in('0.90','0.95','0.99')
  or jsonb_typeof(p->'window_days')<>'number'or(p->>'window_days')!~'^[0-9]{1,3}$'or(p->>'window_days')::integer not between 14 and 365
  or jsonb_typeof(p->'reason')<>'string'or length(btrim(p->>'reason'))not between 1 and 500
 then raise exception using errcode='22023',message='CP7_FORMULA_SETTINGS_INVALID';end if;
 select coalesce(max(x.revision),0)into cur_rev from cp7_stock_formula.settings x;
 if cur_rev<>(p->>'expected_revision')::bigint then raise exception using errcode='40001',message='CP7_FORMULA_SETTINGS_STALE';end if;
 insert into cp7_stock_formula.settings(revision,service_level,window_days,reason,actor,request_id,request_hash)
 values(cur_rev+1,(p->>'service_level')::numeric,(p->>'window_days')::integer,btrim(p->>'reason'),auth.uid(),p_request,h)returning*into row;
 perform cp7_stock_formula.compute(clock_timestamp(),interval'1 second');
 return jsonb_build_object('replay',false,'settings',cp7_stock_formula.current_settings());
end $$;

do $$declare r record;begin
 for r in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_stock_formula'loop
  execute format('alter function %s owner to cp7_capture',r.sig);
  execute format('revoke all on function %s from public,anon,authenticated,service_role',r.sig);
 end loop;
end $$;
grant create on schema public to cp7_capture;
create function public.erp_cp7_get_fg_reorder_v1(p_query jsonb)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_stock_formula.workspace(p_query)$$;
create function public.erp_cp7_refresh_fg_reorder_v1()returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_stock_formula.refresh()$$;
create function public.erp_cp7_save_fg_reorder_manual_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_stock_formula.save_manual(p_payload,p_request)$$;
create function public.erp_cp7_save_stock_formula_settings_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_stock_formula.save_settings(p_payload,p_request)$$;
do $$declare s text;begin
 foreach s in array array['public.erp_cp7_get_fg_reorder_v1(jsonb)','public.erp_cp7_refresh_fg_reorder_v1()',
  'public.erp_cp7_save_fg_reorder_manual_v1(jsonb,uuid)','public.erp_cp7_save_stock_formula_settings_v1(jsonb,uuid)']loop
  execute format('alter function %s owner to cp7_capture',s);
  execute format('revoke all on function %s from public,anon,authenticated,service_role',s);
  execute format('grant execute on function %s to authenticated',s);
 end loop;
end $$;
revoke create on schema public from cp7_capture;
