create or replace function cp7_stock_formula.compute(p_at timestamptz,p_budget interval)returns jsonb
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
 target_kernel as materialized(
  -- OW10: ROP is the L horizon of the production target kernel (review=0).
  -- Supply/WIP allocation remains separate; no stock is subtracted here.
  select c.*,zv z,
   case when c.sales_pcs>0 and c.counted>=14 and c.lead_days is not null then
    cp7_baseline.target(jsonb_build_object('contract_version','cp7.target-input.v2','snapshot_id',md5(p_at::text),
     'scope_id','GLOBAL_CURRENT_PHYSICAL_ROOTS','mode',c.buffer_mode,'daily_total_pcs',c.sales_pcs::text,
     'counted_days',c.counted::text,'daily_sd',case when c.buffer_mode='STATISTICAL'then coalesce(c.sd,0)::text end,
     'lead_days',c.lead_days::text,'review_days','0','buffer_days',case when c.buffer_mode='DAYS'then c.buffer_days::text end,
     'service_level',case when c.buffer_mode='STATISTICAL'then sl::text end,
     'refs',jsonb_build_array(jsonb_build_object('kind','PHYSICAL_PRODUCT_VERSION','id',c.product_id::text,'revision',p_at::text))))end kernel
  from calc c),
 formula as(
  select k.*,(k.kernel->>'lead_safety_pcs')::numeric safety from target_kernel k),
 final as(
  -- Exact: total x lead / counted days (multiply before dividing), never the rounded mean times the lead time; a DAYS
  -- buffer is one product (total x (lead + buffer) / counted), so a whole number of pieces is never pushed up by one.
  select f.*,(f.kernel->>'reorder_point_pcs')::integer formula_point,
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
