create or replace function cp7_stock_formula.compute_materials(p_at timestamptz)returns jsonb
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
