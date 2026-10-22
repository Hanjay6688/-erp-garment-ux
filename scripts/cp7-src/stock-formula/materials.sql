-- SS-2 and SS-3 (owner D17-9, 20 Oct 2026): the reorder point of each fabric, with the same formula as the finished goods
-- (formula.sql): ceil to 0.01 of (D x L + z(service level) x sigma x sqrt(L)), in the material's own unit. Owner D17-10:
-- accessories use no formula, only a minimum set by hand ("aksesoris pake batas minimum manual aja"). Owner D17-12: the
-- app works that minimum out from the owner's own numbers per accessory (perkiraan pemakaian per bulan, lama kirim,
-- cadangan; MOQ kept for the order), ceil to 0.01 of usage_month x (lead + buffer) / 30, multiplied before dividing so a
-- whole cent is never pushed up (basis ESTIMATE); a minimum typed
-- directly wins. The usage the ERP measures is shown next to the estimate, never used by itself.
-- * Usage per complete WIB day of the window (settings of formula.sql), posted movements only, a movement that has an
--   inverse and the inverse itself not counted (the accepted STK01 rule of Bahan & Roll):
--   FABRIC: issued to cutting (CUTTING_ISSUE) less returned from cutting (CUTTING_RETURN), factory use (INTERNAL_USE,
--   pocket fabric) and material handed to a contractor (CONTRACTOR_ISSUE);
--   ACCESSORY: handed to a contractor (CONTRACTOR_ISSUE, the nota mandor) and factory use (INTERNAL_USE), less a returned
--   nota credited back as usable (ADJUSTMENT from BC_NOTE_RETURN_CREDIT into a warehouse; credited as damaged it goes to the
--   damaged area and was used up). Sewing posts no accessory movement.
--   A day counts when material was used that day or the day started with stock (a day without stock is not zero use).
-- * Stock: FABRIC every location (the Ringkasan Gudang and minimum rule); ACCESSORY what Bahan & Roll shows as on hand:
--   active raw-material warehouses that are not a service zone (pos servis, area periksa, area rusak are SPECIAL_ZONE
--   there, cp7_material.workspace). On order: FABRIC the remaining opening purchase commitments
--   (erp.bb_commitment_line_remaining_v1, the fabric analysis' own source); ACCESSORY none (no commitment source).
-- * Lead time: the supplier's delivery time is not recorded in the ERP (owner 20 Oct), so it is a per-material setting
--   "lama kirim (hari)" of Owner/Admin (material_settings); empty: no formula for that fabric (NOT_ENOUGH_DATA), no estimate
--   for that accessory. MOQ, monthly use and buffer (D17-12) are accessory settings only.
-- * A manual number: FABRIC the minimum of Kain & Benchmark (fabric_master_profiles, unchanged), which replaces the formula
--   and keeps the Ringkasan Gudang rule (free stock under the minimum); ACCESSORY the minimum here (manual_point, 0 = never),
--   which replaces the estimate; neither: NOT_SET, no reminder.
-- * Alerts: the fabrics on the formula (stock + on order <= point) are rows of FABRIC_BELOW_MINIMUM "Stok kain di bawah
--   minimum" next to the fabrics with a minimum (D17-10, cp7_alert_native.fabric_kind_source); ACCESSORY_AT_REORDER_POINT
--   "Stok aksesori menipis": stock <= the minimum (typed or worked out from the owner's numbers).
-- OW14b/D17-16: an explicit per-fabric choice supersedes the old presence rule.
-- FORMULA keeps the Native minimum as a read-only reference; LEGACY_MINIMUM
-- pins the reviewed Native number in its immutable setting revision. No choice
-- preserves the previous rule. The fabric kind emits one active source only.
grant select(id,movement_type,reversal_of_id,source_type)on erp.material_stock_movements to cp7_capture;
grant select(material_id,minimum_stock_qty)on erp.fabric_master_profiles to cp7_capture;
grant select(location_id)on erp.bc_accessory_zones_v1 to cp7_capture;

create table cp7_stock_formula.material_settings(
 material_id uuid not null,revision integer not null check(revision>0),
 fabric_rule text check(fabric_rule in('LEGACY_MINIMUM','FORMULA')),
 lead_days numeric(6,2)check(lead_days is null or(lead_days>0 and lead_days<=365)),
 manual_point numeric(18,4)check(manual_point is null or manual_point>=0),
 moq numeric(18,4)check(moq is null or moq>0),usage_month_qty numeric(18,4)check(usage_month_qty is null or usage_month_qty>0),
 buffer_days numeric(6,2)check(buffer_days is null or(buffer_days>=0 and buffer_days<=365)),
 reason text not null check(length(btrim(reason))between 1 and 500),actor uuid not null,request_id uuid not null unique,
 request_hash text not null check(request_hash~'^[0-9a-f]{64}$'),recorded_at timestamptz not null default clock_timestamp(),
 primary key(material_id,revision),check(fabric_rule is distinct from'LEGACY_MINIMUM'or manual_point is not null),
 check(fabric_rule is distinct from'FORMULA'or manual_point is null));
create table cp7_stock_formula.material_evaluations(
 material_id uuid primary key,material_type text not null check(material_type in('FABRIC','ACCESSORY')),sku text not null,name text not null,
 unit_code text,free_qty numeric not null,on_order_qty numeric not null,usage_qty numeric not null,counted_days integer not null,
 use_days integer not null,daily_mean numeric,daily_sd numeric,lead_days numeric,setting_revision integer,z numeric not null,safety_qty numeric,
 formula_point numeric,manual_point numeric,manual_source text check(manual_source in('FABRIC_MINIMUM','ACCESSORY_MANUAL')),point numeric,
 moq numeric,usage_month_qty numeric,buffer_days numeric,estimate_point numeric,
 legacy_minimum_qty numeric,fabric_rule text check(fabric_rule in('LEGACY_MINIMUM','FORMULA')),
 basis text not null check(basis in('MANUAL','FORMULA','ESTIMATE','NOT_ENOUGH_DATA','NO_USAGE','NOT_SET')),reason text check(length(reason)<=80),
 state text not null check(state in('AT_OR_BELOW','ABOVE','NO_POINT')),changed_at timestamptz not null,
 check((basis in('MANUAL','FORMULA','ESTIMATE'))=(point is not null)),check((manual_source is null)=(manual_point is null)));
do $$declare t text;begin
 foreach t in array array['material_settings','material_evaluations']loop
  execute format('alter table cp7_stock_formula.%I owner to cp7_capture',t);
  execute format('alter table cp7_stock_formula.%I enable row level security',t);
  execute format('create policy formula_no_access on cp7_stock_formula.%I for all to public using(false)with check(false)',t);
  execute format('revoke all on cp7_stock_formula.%I from public,anon,authenticated,service_role',t);
 end loop;end $$;
create trigger material_settings_append_only before update or delete on cp7_stock_formula.material_settings
 for each row execute function cp7_stock_formula.append_only();

-- Every active fabric and accessory evaluated at p_at, in one statement; a row is written only when a value changed.
create function cp7_stock_formula.compute_materials(p_at timestamptz)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'set jit=off as $$
declare cfg jsonb:=cp7_stock_formula.current_settings();zv numeric;w integer;today date;d0 date;t0 timestamptz;t1 timestamptz;n integer;low integer;
begin
 zv:=cp7_stock_formula.z((cfg->>'service_level')::numeric);w:=(cfg->>'window_days')::integer;
 today:=(p_at at time zone'Asia/Jakarta')::date;d0:=today-w;
 t0:=d0::timestamp at time zone'Asia/Jakarta';t1:=today::timestamp at time zone'Asia/Jakarta';
 with items as materialized(
  select m.id material_id,m.material_type::text material_type,m.material_sku::text sku,m.material_name::text name,m.unit_code::text unit_code
  from erp.materials m where m.is_active and m.material_type in('FABRIC','ACCESSORY')),
 counted_moves as materialized(
  select s.material_id,s.qty_signed::numeric qty,s.physical_at
  from erp.material_stock_movements s join items i on i.material_id=s.material_id
  left join erp.locations l on l.id=s.location_id
  where s.physical_at<=p_at and s.system_created_at<=p_at
   and(i.material_type='FABRIC'or(l.location_type='RAW_MATERIAL_WAREHOUSE'and l.is_active
    and not exists(select 1 from erp.bc_accessory_zones_v1 z where z.location_id=l.id)))),
 bal as materialized(
  select c.material_id,sum(c.qty)free,coalesce(sum(c.qty)filter(where c.physical_at<t0),0)opening from counted_moves c group by 1),
 net as materialized(
  select c.material_id,(c.physical_at at time zone'Asia/Jakarta')::date as day,sum(c.qty)qty from counted_moves c
  where c.physical_at>=t0 and c.physical_at<t1 group by 1,2),
 used as materialized(
  select s.material_id,(s.physical_at at time zone'Asia/Jakarta')::date as day,sum(-s.qty_signed)::numeric qty
  from erp.material_stock_movements s join items i on i.material_id=s.material_id
  where s.physical_at>=t0 and s.physical_at<t1 and s.system_created_at<=p_at and s.reversal_of_id is null
   and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=s.id and rv.physical_at<=p_at and rv.system_created_at<=p_at)
   and((i.material_type='FABRIC'and s.movement_type in('CUTTING_ISSUE','CUTTING_RETURN','INTERNAL_USE','CONTRACTOR_ISSUE'))
    or(i.material_type='ACCESSORY'and(s.movement_type in('CONTRACTOR_ISSUE','INTERNAL_USE')
     or(s.movement_type='ADJUSTMENT'and s.source_type='BC_NOTE_RETURN_CREDIT'
      and not exists(select 1 from erp.bc_accessory_zones_v1 z where z.location_id=s.location_id)))))
  group by 1,2),
 series as(
  select x.material_id,x.day,coalesce(u.qty,0)qty,
   coalesce(b.opening,0)+coalesce(sum(coalesce(n.qty,0))over(partition by x.material_id order by x.day rows between unbounded preceding and 1 preceding),0)start_qty,
   u.material_id is not null had_use
  from(select r.material_id,g::date as day from(select distinct material_id from used)r cross join generate_series(d0,today-1,interval'1 day')g)x
  left join used u on u.material_id=x.material_id and u.day=x.day left join net n on n.material_id=x.material_id and n.day=x.day
  left join bal b on b.material_id=x.material_id),
 stats as materialized(
  select y.material_id,count(*)filter(where y.had_use or y.start_qty>0)counted,count(*)filter(where y.qty>0)use_days,sum(y.qty)total,
   avg(y.qty)filter(where y.had_use or y.start_qty>0)mean,stddev_samp(y.qty)filter(where y.had_use or y.start_qty>0)sd
  from series y group by y.material_id),
 ordered as materialized(
  select l.material_id,sum(r.remaining)qty from erp.bb_purchase_commitment_lines_v1 l
  cross join lateral(select erp.bb_commitment_line_remaining_v1(l.id,null)remaining)r
  where l.material_id in(select i.material_id from items i where i.material_type='FABRIC')and r.remaining>0 group by 1),
 setting as materialized(
  select distinct on(x.material_id)x.material_id,x.revision,x.lead_days,x.manual_point,x.moq,x.usage_month_qty,x.buffer_days,x.fabric_rule
  from cp7_stock_formula.material_settings x order by x.material_id,x.revision desc),
 calc as(
  select i.*,coalesce(b.free,0)free,case when i.material_type='FABRIC'then coalesce(o.qty,0)else 0 end on_order,coalesce(st.total,0)usage,
   coalesce(st.counted,0)counted,coalesce(st.use_days,0)use_days,st.mean,case when st.counted>=2 then st.sd end sd,
   s.lead_days,s.revision setting_revision,
   case when i.material_type='ACCESSORY'then s.moq end moq,case when i.material_type='ACCESSORY'then s.usage_month_qty end usage_month_qty,
   case when i.material_type='ACCESSORY'then s.buffer_days end buffer_days,
   case when i.material_type='FABRIC'then fp.minimum_stock_qty end legacy_minimum_qty,
   case when i.material_type='FABRIC'then s.fabric_rule end fabric_rule,
   case when i.material_type='FABRIC'then case s.fabric_rule when'FORMULA'then null when'LEGACY_MINIMUM'then s.manual_point
    else nullif(fp.minimum_stock_qty,0)end else s.manual_point end manual_point,
   case when i.material_type='FABRIC'and(s.fabric_rule='LEGACY_MINIMUM'or(s.fabric_rule is null and fp.minimum_stock_qty>0))then'FABRIC_MINIMUM'
    when i.material_type='ACCESSORY'and s.manual_point is not null then'ACCESSORY_MANUAL'end manual_source
  from items i left join bal b on b.material_id=i.material_id left join stats st on st.material_id=i.material_id
  left join ordered o on o.material_id=i.material_id left join setting s on s.material_id=i.material_id
  left join erp.fabric_master_profiles fp on fp.material_id=i.material_id and i.material_type='FABRIC'),
 formula as(
  select c.*,case when c.material_type='FABRIC'and c.usage>0 and c.counted>=14 and c.lead_days is not null
   then zv*coalesce(c.sd,0)*sqrt(c.lead_days)end safety,
   case when c.material_type='ACCESSORY'and c.usage_month_qty is not null and c.lead_days is not null and c.buffer_days is not null
   then ceil(c.usage_month_qty*(c.lead_days+c.buffer_days)*100/30)/100 end estimate_point from calc c),
 final as(
  select f.*,case when f.safety is not null then greatest(ceil((f.usage*f.lead_days/f.counted+f.safety)*100)/100,0)end formula_point,
   case when f.manual_source is not null then'MANUAL'when f.estimate_point is not null then'ESTIMATE'when f.material_type='ACCESSORY'then'NOT_SET'
    when f.usage<=0 then'NO_USAGE'when f.counted<14 or f.lead_days is null then'NOT_ENOUGH_DATA'else'FORMULA'end basis,
   case when f.manual_source is not null or f.estimate_point is not null then null when f.material_type='ACCESSORY'then'NO_MINIMUM_OR_ESTIMATE'
    when f.usage<=0 then'NO_POSTED_USAGE_IN_WINDOW'when f.counted<14 then'FEWER_THAN_14_COUNTED_DAYS'when f.lead_days is null then'NO_LEAD_TIME'end reason
  from formula f),
 scored as(
  select x.*,case x.basis when'MANUAL'then x.manual_point when'FORMULA'then x.formula_point when'ESTIMATE'then x.estimate_point end point from final x),
 stated as(
  select x.*,case when x.point is null or x.point<=0 then'NO_POINT'
   when x.manual_source='FABRIC_MINIMUM'then case when x.free<x.point then'AT_OR_BELOW'else'ABOVE'end
   when x.free+x.on_order<=x.point then'AT_OR_BELOW'else'ABOVE'end state from scored x),
 ins as(
  insert into cp7_stock_formula.material_evaluations as e(material_id,material_type,sku,name,unit_code,free_qty,on_order_qty,usage_qty,counted_days,
   use_days,daily_mean,daily_sd,lead_days,setting_revision,z,safety_qty,formula_point,manual_point,manual_source,point,moq,usage_month_qty,buffer_days,
   estimate_point,basis,reason,state,changed_at,legacy_minimum_qty,fabric_rule)
  select x.material_id,x.material_type,x.sku,x.name,x.unit_code,x.free,x.on_order,x.usage,x.counted,x.use_days,round(x.mean,4),round(x.sd,4),x.lead_days,
   x.setting_revision,zv,round(x.safety,4),x.formula_point,x.manual_point,x.manual_source,x.point,x.moq,x.usage_month_qty,x.buffer_days,x.estimate_point,
   x.basis,x.reason,x.state,p_at,x.legacy_minimum_qty,x.fabric_rule from stated x
  on conflict(material_id)do update set material_type=excluded.material_type,sku=excluded.sku,name=excluded.name,unit_code=excluded.unit_code,
   free_qty=excluded.free_qty,on_order_qty=excluded.on_order_qty,usage_qty=excluded.usage_qty,counted_days=excluded.counted_days,use_days=excluded.use_days,
   daily_mean=excluded.daily_mean,daily_sd=excluded.daily_sd,lead_days=excluded.lead_days,setting_revision=excluded.setting_revision,z=excluded.z,
   safety_qty=excluded.safety_qty,formula_point=excluded.formula_point,manual_point=excluded.manual_point,manual_source=excluded.manual_source,
   point=excluded.point,moq=excluded.moq,usage_month_qty=excluded.usage_month_qty,buffer_days=excluded.buffer_days,estimate_point=excluded.estimate_point,
   basis=excluded.basis,reason=excluded.reason,state=excluded.state,changed_at=p_at,
   legacy_minimum_qty=excluded.legacy_minimum_qty,fabric_rule=excluded.fabric_rule
  where(e.material_type,e.sku,e.name,e.unit_code,e.free_qty,e.on_order_qty,e.usage_qty,e.counted_days,e.use_days,e.daily_mean,e.daily_sd,e.lead_days,
   e.setting_revision,e.z,e.safety_qty,e.formula_point,e.manual_point,e.manual_source,e.point,e.moq,e.usage_month_qty,e.buffer_days,e.estimate_point,
   e.basis,e.reason,e.state,e.legacy_minimum_qty,e.fabric_rule)is distinct from(
   excluded.material_type,excluded.sku,excluded.name,excluded.unit_code,excluded.free_qty,excluded.on_order_qty,excluded.usage_qty,excluded.counted_days,
   excluded.use_days,excluded.daily_mean,excluded.daily_sd,excluded.lead_days,excluded.setting_revision,excluded.z,excluded.safety_qty,
   excluded.formula_point,excluded.manual_point,excluded.manual_source,excluded.point,excluded.moq,excluded.usage_month_qty,excluded.buffer_days,
   excluded.estimate_point,excluded.basis,excluded.reason,excluded.state,excluded.legacy_minimum_qty,excluded.fabric_rule)
  returning 1)
 delete from cp7_stock_formula.material_evaluations e where not exists(select 1 from items i where i.material_id=e.material_id);
 select count(*),count(*)filter(where state='AT_OR_BELOW')into n,low from cp7_stock_formula.material_evaluations;
 return jsonb_build_object('materials',n,'materials_at_or_below',low);
end $$;

-- One evaluation per client command: the first caller that takes the module lock evaluates everything (finished goods and
-- materials) and marks the command (its statement_timestamp, kept for the transaction); a later source of the same
-- command (the other kinds of one collect tick) reads that evaluation, and the next command evaluates again, so a
-- recheck after stock moved never reads a stale evaluation. False: another session holds the lock (the caller then
-- checks against the stock now and writes nothing).
create function cp7_stock_formula.ensure_computed()returns boolean
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
begin
 if current_setting('cp7_formula.evaluated',true)=statement_timestamp()::text then return true;end if;
 if not pg_try_advisory_xact_lock(hashtextextended('CP7:FORMULA:FG',0))then return false;end if;
 perform cp7_stock_formula.compute(clock_timestamp(),interval'2 seconds');
 perform set_config('cp7_formula.evaluated',statement_timestamp()::text,true);
 return true;
end $$;

-- A material as Pengingat sistem shows it: numbers only, no time.
create function cp7_stock_formula.material_alert_row(e jsonb,p_level numeric)returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('subject_key',e->>'material_id',
  'title',case e->>'material_type'when'FABRIC'then'Stok kain di bawah minimum: 'else'Stok aksesori menipis: 'end||(e->>'name'),
  'detail',jsonb_build_object('material_id',e->'material_id','material_type',e->'material_type','sku',e->'sku','name',e->'name','unit_code',e->'unit_code',
   'free_qty',(e->>'free_qty')::numeric::text,'on_order_qty',(e->>'on_order_qty')::numeric::text,'reorder_point_qty',(e->>'point')::numeric::text,
   'basis',e->'basis','daily_mean',round((e->>'daily_mean')::numeric,2)::text,'lead_days',(e->>'lead_days')::numeric::text,
   'safety_qty',case when e->>'basis'='FORMULA'then round((e->>'safety_qty')::numeric,2)::text end,
   'service_level',case when e->>'basis'='FORMULA'then p_level::text end),
  'party_names','[]'::jsonb)$$;
-- FABRIC: formula and explicitly selected pinned minima, read into FABRIC_BELOW_MINIMUM.
-- An unreviewed prior minimum is delegated to the retained Native reference rule;
-- explicit choices are never delegated back. ACCESSORY: ACCESSORY_AT_REORDER_POINT. Each
-- with the permissions of its screen.
create function cp7_stock_formula.material_source(p_type text)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare r jsonb;lvl numeric:=(cp7_stock_formula.current_settings()->>'service_level')::numeric;t timestamptz:=clock_timestamp();
begin
 if p_type='FABRIC'then
  if erp.has_permission('warehouse.material.view')is not true or erp.has_permission('master.fabric.view')is not true then
   raise exception using errcode='42501',message='CP7_FORMULA_MATERIAL_SOURCE_DENIED';end if;
 elsif p_type='ACCESSORY'then
  if erp.has_permission('warehouse.accessory.view')is not true then raise exception using errcode='42501',message='CP7_FORMULA_MATERIAL_SOURCE_DENIED';end if;
 else raise exception 'CP7_FORMULA_MATERIAL_TYPE';end if;
 if cp7_stock_formula.ensure_computed()then
  select jsonb_build_object(
   'rows',coalesce(jsonb_agg(cp7_stock_formula.material_alert_row(to_jsonb(e),lvl)order by e.sku,e.material_id)
    filter(where e.state='AT_OR_BELOW'and(p_type='ACCESSORY'or e.basis='FORMULA'or e.fabric_rule='LEGACY_MINIMUM')),'[]'),
   'states',coalesce(jsonb_object_agg(e.material_id::text,case when e.manual_source='FABRIC_MINIMUM'and e.fabric_rule is null then'MANUAL_MINIMUM_IN_FORCE'
     when e.state='ABOVE'then'ABOVE_REORDER_POINT'else'NO_REORDER_POINT'end)
    filter(where not(e.state='AT_OR_BELOW'and(p_type='ACCESSORY'or e.basis='FORMULA'or e.fabric_rule='LEGACY_MINIMUM'))),'{}'))
  into r from cp7_stock_formula.material_evaluations e where e.material_type=p_type;
  return r;
 end if;
 -- Busy: the materials at or under their point in the last evaluation, against the stock now (same locations), with that
 -- evaluation's point and on-order quantity.
 with low as(select e.*,to_jsonb(e)j from cp7_stock_formula.material_evaluations e
   where e.material_type=p_type and e.state='AT_OR_BELOW'and(p_type='ACCESSORY'or e.basis='FORMULA'or e.fabric_rule='LEGACY_MINIMUM')),
 live as(select l.material_id,l.sku,l.point,l.on_order_qty,l.manual_source,l.j,coalesce((select sum(s.qty_signed)from erp.material_stock_movements s
   left join erp.locations x on x.id=s.location_id where s.material_id=l.material_id and s.physical_at<=t and s.system_created_at<=t
    and(p_type='FABRIC'or(x.location_type='RAW_MATERIAL_WAREHOUSE'and x.is_active
     and not exists(select 1 from erp.bc_accessory_zones_v1 z where z.location_id=x.id)))),0)::numeric free from low l),
 now_state as(select v.*,case when v.manual_source='FABRIC_MINIMUM'then v.free<v.point else v.free+v.on_order_qty<=v.point end still from live v)
 select jsonb_build_object(
  'rows',coalesce(jsonb_agg(cp7_stock_formula.material_alert_row(n.j||jsonb_build_object('free_qty',n.free),lvl)order by n.sku,n.material_id)
   filter(where n.still),'[]'),
  'states',coalesce(jsonb_object_agg(n.material_id::text,'ABOVE_REORDER_POINT')filter(where not n.still),'{}'))into r from now_state n;
 return jsonb_set(r,'{states}',(r->'states')||coalesce((select jsonb_object_agg(e.material_id::text,case when e.manual_source='FABRIC_MINIMUM'and e.fabric_rule is null
   then'MANUAL_MINIMUM_IN_FORCE'when e.state='ABOVE'then'ABOVE_REORDER_POINT'else'NO_REORDER_POINT'end)
  from cp7_stock_formula.material_evaluations e where e.material_type=p_type
   and not(e.state='AT_OR_BELOW'and(p_type='ACCESSORY'or e.basis='FORMULA'or e.fabric_rule='LEGACY_MINIMUM'))),'{}'));
end $$;

-- ----------------------------------------------------------- material RPCs --
-- Read: the screen's permissions (fabric: Bahan & Roll and Kain & Benchmark; accessory: Aksesori). Change: Owner/Admin.
create function cp7_stock_formula.material_access_now(p_type text,p_manage boolean)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;
begin
 if auth.uid()is null or coalesce(auth.jwt()->>'role','')<>'authenticated'then raise exception using errcode='42501',message='CP7_FORMULA_ACCESS_DENIED';end if;
 a:=erp.get_my_access_v1();
 if a->'allowed'is distinct from'true'::jsonb or p_type is null or p_type not in('FABRIC','ACCESSORY')
  or(p_type='FABRIC'and(erp.has_permission('warehouse.material.view')is not true or erp.has_permission('master.fabric.view')is not true))
  or(p_type='ACCESSORY'and erp.has_permission('warehouse.accessory.view')is not true)
  or(p_manage and coalesce(a->'profile'->>'role_code','')not in('OWNER','ADMIN'))then
  raise exception using errcode='42501',message='CP7_FORMULA_ACCESS_DENIED';end if;
 return a;
end $$;
create function cp7_stock_formula.material_workspace(p jsonb)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;typ text;q text;f text;off integer;n integer;total bigint;rows jsonb;
begin
 if jsonb_typeof(p)is distinct from'object'or exists(select 1 from jsonb_object_keys(p)k where k not in('material_type','q','filter','offset','limit'))
  or jsonb_typeof(p->'material_type')is distinct from'string'
  or(p?'q'and jsonb_typeof(p->'q')<>'string')or(p?'filter'and(jsonb_typeof(p->'filter')<>'string'
   or p->>'filter'not in('ALL','AT_OR_BELOW','MANUAL','ESTIMATE','NOT_ENOUGH_DATA','NOT_SET')))
  or(p?'offset'and(jsonb_typeof(p->'offset')<>'number'or(p->>'offset')!~'^[0-9]{1,7}$'))
  or(p?'limit'and(jsonb_typeof(p->'limit')<>'number'or(p->>'limit')!~'^[0-9]{1,3}$'))then raise exception using errcode='22023',message='CP7_FORMULA_QUERY';end if;
 typ:=p->>'material_type';a:=cp7_stock_formula.material_access_now(typ,false);
 q:=lower(btrim(coalesce(p->>'q','')));f:=coalesce(p->>'filter','ALL');off:=coalesce((p->>'offset')::integer,0);n:=coalesce((p->>'limit')::integer,25);
 if length(q)>120 or n not between 1 and 100 then raise exception using errcode='22023',message='CP7_FORMULA_QUERY';end if;
 select count(*)into total from cp7_stock_formula.material_evaluations e where e.material_type=typ
  and(q=''or strpos(lower(concat_ws(' ',e.sku,e.name)),q)>0)
  and(f='ALL'or(f='AT_OR_BELOW'and e.state='AT_OR_BELOW')or(f='MANUAL'and e.basis='MANUAL')or(f='NOT_ENOUGH_DATA'and e.basis='NOT_ENOUGH_DATA')
   or(f='NOT_SET'and e.basis='NOT_SET')or(f='ESTIMATE'and e.basis='ESTIMATE'));
 select coalesce(jsonb_agg((to_jsonb(x)-'ord')||jsonb_build_object('legacy_minimum_qty',x.legacy_minimum_qty::text,
  'point',x.point::text,'manual_point',x.manual_point::text)order by x.ord,x.sku,x.material_id),'[]')into rows from(
  select e.*,case e.state when'AT_OR_BELOW'then 0 when'ABOVE'then 1 else 2 end ord from cp7_stock_formula.material_evaluations e
  where e.material_type=typ and(q=''or strpos(lower(concat_ws(' ',e.sku,e.name)),q)>0)
   and(f='ALL'or(f='AT_OR_BELOW'and e.state='AT_OR_BELOW')or(f='MANUAL'and e.basis='MANUAL')or(f='NOT_ENOUGH_DATA'and e.basis='NOT_ENOUGH_DATA')
    or(f='NOT_SET'and e.basis='NOT_SET')or(f='ESTIMATE'and e.basis='ESTIMATE'))
  order by ord,e.sku,e.material_id limit n offset off)x;
 return jsonb_build_object('contract_version','cp7.material-reorder.v2','material_type',typ,'read_at',statement_timestamp(),
  'settings',cp7_stock_formula.current_settings(),'run',(select to_jsonb(r)-'id'from cp7_stock_formula.runs r),
  'can_manage',coalesce(a->'profile'->>'role_code','')in('OWNER','ADMIN'),
  'counts',(select jsonb_build_object('items',count(*),'at_or_below',count(*)filter(where e.state='AT_OR_BELOW'),'manual',count(*)filter(where e.basis='MANUAL'),
    'formula',count(*)filter(where e.basis='FORMULA'),'not_enough_data',count(*)filter(where e.basis='NOT_ENOUGH_DATA'),'no_usage',count(*)filter(where e.basis='NO_USAGE'),
    'not_set',count(*)filter(where e.basis='NOT_SET'),'estimate',count(*)filter(where e.basis='ESTIMATE'))
   from cp7_stock_formula.material_evaluations e where e.material_type=typ),
  'page',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',n,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows)end));
end $$;
create function cp7_stock_formula.material_refresh(p_type text)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 perform cp7_stock_formula.material_access_now(p_type,false);
 if not pg_try_advisory_xact_lock(hashtextextended('CP7:FORMULA:FG',0))then raise exception using errcode='55P03',message='CP7_FORMULA_BUSY';end if;
 return cp7_stock_formula.compute(clock_timestamp(),interval'1 second');
end $$;
-- Lead time (all), manual minimum and the owner's estimate (accessories only, D17-10/D17-12: MOQ, monthly use, buffer
-- days; a fabric's manual number is its minimum in Kain & Benchmark). The estimate keys may be left out (null).
create function cp7_stock_formula.save_material(p jsonb,p_request uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;h text;prev cp7_stock_formula.material_settings;mat record;cur_rev integer;row cp7_stock_formula.material_settings;lead numeric;manual numeric;
 moq numeric;usage_month numeric;buffer numeric;rule text;previous_manual numeric;legacy numeric;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 if jsonb_typeof(p)is distinct from'object'or not p?&array['material_id','expected_revision','lead_days','manual_point','reason']
  or exists(select 1 from jsonb_object_keys(p)k where k not in('material_id','expected_revision','lead_days','manual_point','reason','moq',
   'usage_month_qty','buffer_days','fabric_rule','expected_legacy_minimum_qty'))
  or((p?'fabric_rule')is distinct from(p?'expected_legacy_minimum_qty'))
  or(p?'fabric_rule'and(jsonb_typeof(p->'fabric_rule')is distinct from'string'or p->>'fabric_rule'not in('LEGACY_MINIMUM','FORMULA')))
  or(p?'expected_legacy_minimum_qty'and(jsonb_typeof(p->'expected_legacy_minimum_qty')not in('string','null')
   or coalesce(p->>'expected_legacy_minimum_qty','0')!~'^[0-9]{1,14}(\.[0-9]{1,4})?$'))
  or jsonb_typeof(p->'material_id')<>'string'or(p->>'material_id')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or jsonb_typeof(p->'expected_revision')<>'number'or(p->>'expected_revision')!~'^[0-9]{1,9}$'
  or jsonb_typeof(p->'lead_days')not in('string','null')or coalesce(p->>'lead_days','1')!~'^[0-9]{1,3}(\.[0-9]{1,2})?$'
  or jsonb_typeof(p->'manual_point')not in('string','null')or coalesce(p->>'manual_point','0')!~'^[0-9]{1,13}(\.[0-9]{1,4})?$'
  or(p?'moq'and(jsonb_typeof(p->'moq')not in('string','null')or coalesce(p->>'moq','1')!~'^[0-9]{1,13}(\.[0-9]{1,4})?$'))
  or(p?'usage_month_qty'and(jsonb_typeof(p->'usage_month_qty')not in('string','null')or coalesce(p->>'usage_month_qty','1')!~'^[0-9]{1,13}(\.[0-9]{1,4})?$'))
  or(p?'buffer_days'and(jsonb_typeof(p->'buffer_days')not in('string','null')or coalesce(p->>'buffer_days','0')!~'^[0-9]{1,3}(\.[0-9]{1,2})?$'))
  or jsonb_typeof(p->'reason')<>'string'or length(btrim(p->>'reason'))not between 1 and 500
 then raise exception using errcode='22023',message='CP7_FORMULA_MATERIAL_INVALID';end if;
 select m.id,m.material_type::text material_type into mat from erp.materials m
  where m.id=(p->>'material_id')::uuid and m.is_active and m.material_type in('FABRIC','ACCESSORY');
 if mat.id is null then raise exception using errcode='22023',message='CP7_FORMULA_ITEM_UNKNOWN';end if;
 a:=cp7_stock_formula.material_access_now(mat.material_type,true);
 if p_request is null then raise exception using errcode='22023',message='CP7_FORMULA_REQUEST_REQUIRED';end if;
 lead:=(p->>'lead_days')::numeric;manual:=(p->>'manual_point')::numeric;
 moq:=(p->>'moq')::numeric;usage_month:=(p->>'usage_month_qty')::numeric;buffer:=(p->>'buffer_days')::numeric;
 if(lead is not null and(lead<=0 or lead>365))or(moq is not null and moq<=0)or(usage_month is not null and usage_month<=0)
  or(buffer is not null and buffer>365)
  or(mat.material_type='FABRIC'and(manual is not null or moq is not null or usage_month is not null or buffer is not null))
  or(mat.material_type='ACCESSORY'and p?'fabric_rule')then
  raise exception using errcode='22023',message='CP7_FORMULA_MATERIAL_INVALID';end if;
 h:=encode(sha256(convert_to(coalesce(p::text,''),'UTF8')),'hex');
 perform pg_advisory_xact_lock(hashtextextended('CP7:FORMULA:FG',0));
 if cp7_stock_formula.material_access_now(mat.material_type,true)is distinct from a then
  raise exception using errcode='42501',message='CP7_FORMULA_MATERIAL_ACCESS_CHANGED';end if;
 if not exists(select 1 from erp.materials m where m.id=mat.id and m.is_active and m.material_type::text=mat.material_type)then
  raise exception using errcode='22023',message='CP7_FORMULA_ITEM_UNKNOWN';end if;
 select*into prev from cp7_stock_formula.material_settings x where x.request_id=p_request;
 if found then
  if prev.actor<>auth.uid()or prev.request_hash<>h then raise exception using errcode='22023',message='CP7_FORMULA_REQUEST_REUSED';end if;
  return jsonb_build_object('replay',true,'material_id',prev.material_id,'revision',prev.revision);
 end if;
 select x.revision,x.fabric_rule,x.manual_point into cur_rev,rule,previous_manual from cp7_stock_formula.material_settings x
  where x.material_id=mat.id order by x.revision desc limit 1;
 cur_rev:=coalesce(cur_rev,0);
 if cur_rev<>(p->>'expected_revision')::integer then raise exception using errcode='40001',message='CP7_FORMULA_MATERIAL_STALE';end if;
 if mat.material_type='FABRIC'then
  if p?'fabric_rule'then
   select fp.minimum_stock_qty into legacy from erp.fabric_master_profiles fp where fp.material_id=mat.id;
   if legacy is distinct from(p->>'expected_legacy_minimum_qty')::numeric then
    raise exception using errcode='40001',message='CP7_FORMULA_FABRIC_REFERENCE_CHANGED';end if;
   rule:=p->>'fabric_rule';
   if rule='LEGACY_MINIMUM'and(legacy is null or legacy<0)then
    raise exception using errcode='22023',message='CP7_FORMULA_FABRIC_REFERENCE_NOT_SET';end if;
   manual:=case when rule='LEGACY_MINIMUM'then legacy end;
  else
   -- Older clients may update delivery time, never silently clear a choice.
   manual:=case when rule='LEGACY_MINIMUM'then previous_manual end;
  end if;
 end if;
 insert into cp7_stock_formula.material_settings(material_id,revision,lead_days,manual_point,moq,usage_month_qty,buffer_days,reason,actor,request_id,request_hash,fabric_rule)
 values(mat.id,cur_rev+1,lead,manual,moq,usage_month,buffer,btrim(p->>'reason'),auth.uid(),p_request,h,rule)returning*into row;
 perform cp7_stock_formula.compute(clock_timestamp(),interval'1 second');
 if cp7_stock_formula.material_access_now(mat.material_type,true)is distinct from a then
  raise exception using errcode='42501',message='CP7_FORMULA_MATERIAL_ACCESS_CHANGED';end if;
 return jsonb_build_object('replay',false,'material_id',row.material_id,'revision',row.revision,
  'evaluation',(select to_jsonb(e)||jsonb_build_object('legacy_minimum_qty',e.legacy_minimum_qty::text,'point',e.point::text,
   'manual_point',e.manual_point::text)from cp7_stock_formula.material_evaluations e where e.material_id=mat.id));
end $$;

do $$declare r record;begin
 for r in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_stock_formula'
  and p.proname in('compute_materials','ensure_computed','material_alert_row','material_source','material_access_now','material_workspace',
   'material_refresh','save_material')loop
  execute format('alter function %s owner to cp7_capture',r.sig);
  execute format('revoke all on function %s from public,anon,authenticated,service_role',r.sig);
 end loop;
end $$;
grant create on schema public to cp7_capture;
create function public.erp_cp7_get_material_reorder_v1(p_query jsonb)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_stock_formula.material_workspace(p_query)$$;
create function public.erp_cp7_refresh_material_reorder_v1(p_material_type text)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_stock_formula.material_refresh(p_material_type)$$;
create function public.erp_cp7_save_material_reorder_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_stock_formula.save_material(p_payload,p_request)$$;
do $$declare s text;begin
 foreach s in array array['public.erp_cp7_get_material_reorder_v1(jsonb)','public.erp_cp7_refresh_material_reorder_v1(text)',
  'public.erp_cp7_save_material_reorder_v1(jsonb,uuid)']loop
  execute format('alter function %s owner to cp7_capture',s);
  execute format('revoke all on function %s from public,anon,authenticated,service_role',s);
  execute format('grant execute on function %s to authenticated',s);
 end loop;
end $$;
revoke create on schema public from cp7_capture;
