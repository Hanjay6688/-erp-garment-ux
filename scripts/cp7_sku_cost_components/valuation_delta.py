"""Exact derivation of the existing SKU economic writers; Native guards stay.

The original source remains immutable. Every replacement records its inverse;
all resulting function bodies are intended for the separate cost successor.
"""
from hashlib import sha256
from pathlib import Path
import re

PARENT=Path(__file__).resolve().parent.parent/'cp7_sku_moving_average'/'valuation.sql'
PARENT_SHA256='f2868e334b1f85f6a568c3f5da51cb7f979867eb154058a8652e865222d83649'


class Derivation:
    def __init__(self,source):self.source=source;self.routes=[]
    def once(self,old,new,label):
        if self.source.count(old)!=1:raise ValueError('SKU_COST_SOURCE_CHANGED:'+label)
        self.source=self.source.replace(old,new,1);self.routes.append((old,new,label))
    def many(self,old,new,count,label):
        if self.source.count(old)!=count:raise ValueError('SKU_COST_SOURCE_CHANGED:'+label)
        self.source=self.source.replace(old,new);self.routes.append((old,new,label))
    def inverse(self):
        result=self.source
        for old,new,label in reversed(self.routes):result=result.replace(new,old)
        return result


def snapshot_sum(table,cost_table,key,where):
    return '(select sum(c.booked_value)from(select booked_value from cp7_sku_conversion.'+table+' where '+key+'='+where+\
        ' union all select booked_value from cp7_sku_conversion.'+cost_table+' where '+key+'='+where+')c)'


def derive():
    raw=PARENT.read_bytes()
    if sha256(raw).hexdigest()!=PARENT_SHA256:raise ValueError('SKU_COST_WHOLE_PARENT_VALUATION_CHANGED')
    originals={name:body for name,body in [(m.group(1),m.group(0))for m in re.finditer(r'(?ms)^create function ([^\s(]+)\([\s\S]*?\$\$;\n',raw.decode())]}
    result={};routes={}
    def edit(name):return Derivation(originals['cp7_sku_conversion.'+name])
    def save(name,d):
        key='cp7_sku_conversion.'+name
        if d.inverse()!=originals[key]:raise ValueError('SKU_COST_DERIVATION_NOT_REVERSIBLE:'+name)
        result[key]=d.source.replace('create function ','create or replace function ',1)
        routes[key]=[dict(label=label,before_sha256=sha256(old.encode()).hexdigest(),after_sha256=sha256(new.encode()).hexdigest())for old,new,label in d.routes]

    name='pool_attribution_v2';d=edit(name)
    d.once("select po_id,sum(value)::numeric value from cp7_sku_conversion.pool_components_v2(p_product,p_location,p_grade)\n  group by po_id",
        "select po_id,sum(value)::numeric value from(\n   select po_id,value from cp7_sku_conversion.pool_components_v2(p_product,p_location,p_grade)\n   union all select po_id,value from cp7_sku_conversion.pool_cost_components_v3(p_product,p_location,p_grade)\n  )a group by po_id",'pool PO values include independently sourced costs')
    save(name,d)

    name='pool_quote_v2';d=edit(name)
    d.once('v_base:=v_value;v_adjust:=0;',"v_base:=v_value;\n select coalesce(sum(c.value),0)into v_adjust from cp7_sku_conversion.pool_cost_components_v3(p_product,p_location,p_grade)c;\n v_value:=round(v_base+v_adjust,6);",'cost value without extra stock pieces')
    d.once("  'events',(select", "  'cost_components',(select coalesce(jsonb_agg(to_jsonb(c)order by c.root_lot_id),'[]'::jsonb)\n   from cp7_sku_conversion.pool_cost_components_v3(p_product,p_location,p_grade)c),\n  'cost_events',(select coalesce(jsonb_agg(to_jsonb(e)order by e.recorded_at,e.id),'[]'::jsonb)\n   from cp7_sku_conversion.cost_events_v3 e where e.product_id=p_product and e.location_id=p_location and e.quality_grade=p_grade),\n  'events',(select",'zero cost source and event revision')
    save(name,d)

    name='owned_scope_value_v2';d=edit(name)
    d.once('select coalesce(sum(x.units*h.hpp_per_pcs),0)::numeric from(',"select (coalesce(sum(x.units*h.hpp_per_pcs),0)+cp7_sku_conversion.cost_scope_value_v3(p_product,p_po,'OWNED'))::numeric from(",'current owned cost scope')
    save(name,d)

    name='prepare_sale_values_v2';d=edit(name)
    d.once('select v.sale_stock_allocation_id,c.root_lot_id,c.po_id,c.unit_value,',"select 'BASE'::text kind,v.sale_stock_allocation_id,c.root_lot_id,c.po_id,c.unit_value,",'base sale component kind')
    d.once('  ), raw as(',"""   union all
   select 'COST',v.sale_stock_allocation_id,c.root_lot_id,c.po_id,c.unit_value,
    (round(v.cumulative_qty*c.component_units/(q->>'qty')::numeric,12)
     -round((v.cumulative_qty-v.qty_pcs)*c.component_units/(q->>'qty')::numeric,12))::numeric component_units,v.effective_value
   from(select v.*,sum(v.qty_pcs)over(order by v.sale_stock_allocation_id rows unbounded preceding)cumulative_qty
    from cp7_sku_conversion.sale_allocation_values_v2 v
    where v.sale_id=p_sale and v.product_id=pool.product_id and v.location_id=pool.location_id)v
   cross join cp7_sku_conversion.pool_cost_components_v3(pool.product_id,pool.location_id,'GRADE_A')c
  ), raw as(""",'sale cost proportions with final allocation remainder')
    d.many('partition by sale_stock_allocation_id order by root_lot_id','partition by sale_stock_allocation_id order by kind,root_lot_id',3,'combined cent ordering')
    d.once('case when effective_value=0 then 0 else round(cumulative_raw*effective_value/nullif(total_raw,0),2)end',
        'case when total_raw=0 then round(cumulative_raw,2)else round(cumulative_raw*effective_value/total_raw,2)end','signed cost cent apportionment')
    d.once("  )\n  insert into cp7_sku_conversion.sale_allocation_components_v2(sale_stock_allocation_id,line_no,root_lot_id,po_id,component_units,booked_value)\n  select sale_stock_allocation_id,line_no,root_lot_id,po_id,component_units,booked_value from shares order by sale_stock_allocation_id,line_no;",
        """  ),saved_base as(
   insert into cp7_sku_conversion.sale_allocation_components_v2(sale_stock_allocation_id,line_no,root_lot_id,po_id,component_units,booked_value)
   select sale_stock_allocation_id,line_no,root_lot_id,po_id,component_units,booked_value from shares where kind='BASE'
   order by sale_stock_allocation_id,line_no returning sale_stock_allocation_id
  )insert into cp7_sku_conversion.sale_cost_components_v3(sale_stock_allocation_id,line_no,root_lot_id,po_id,component_units,booked_value)
  select sale_stock_allocation_id,line_no,root_lot_id,po_id,component_units,booked_value from shares where kind='COST'order by sale_stock_allocation_id,line_no;""",'immutable sale cost snapshots')
    d.once('(select sum(c.booked_value)from cp7_sku_conversion.sale_allocation_components_v2 c where c.sale_stock_allocation_id=v.sale_stock_allocation_id)',
        snapshot_sum('sale_allocation_components_v2','sale_cost_components_v3','sale_stock_allocation_id','v.sale_stock_allocation_id'),'complete sale amount check')
    d.once('from cp7_sku_conversion.sale_allocation_components_v2 c join allocation_ranked a using(sale_stock_allocation_id)',
        'from(select sale_stock_allocation_id,po_id,booked_value from cp7_sku_conversion.sale_allocation_components_v2\n    union all select sale_stock_allocation_id,po_id,booked_value from cp7_sku_conversion.sale_cost_components_v3)c join allocation_ranked a using(sale_stock_allocation_id)',
        'sale journal PO attribution includes signed costs')
    d.once('end $$;',' perform cp7_sku_conversion.post_sale_costs_v3(p_sale);\nend $$;','sale cost movement before Native posting')
    save(name,d)

    name='prepare_return_values_v2';d=edit(name)
    d.once('select *from cp7_sku_conversion.return_components_v2(r.sale_stock_allocation_id,r.qty_pcs,p_return)',
        "select 'BASE'::text kind,*from cp7_sku_conversion.return_components_v2(r.sale_stock_allocation_id,r.qty_pcs,p_return)\n   union all select 'COST',*from cp7_sku_conversion.return_cost_components_v3(r.sale_stock_allocation_id,r.qty_pcs,p_return)",'return original sold cost fractions')
    d.once('and(k.po_id is not null or v.product_id=r.product_id)),0)::numeric before_value',
        """and(k.po_id is not null or v.product_id=r.product_id)),0)
    +coalesce((select sum(c.component_units*cr.unit_value)from cp7_sku_conversion.return_cost_components_v3 c
      join cp7_sku_conversion.sales_return_values_v2 v using(sales_return_item_id)
      cross join lateral cp7_sku_conversion.cost_root_v3(c.root_lot_id)cr
      where v.return_id=p_return and c.po_id is not distinct from k.po_id
       and(k.po_id is not null or v.product_id=r.product_id)),0)::numeric before_value""",'draft return cost values in current scoped cent target')
    d.many('partition by c.po_id order by c.root_lot_id','partition by c.po_id order by c.kind,c.root_lot_id',1,'return scoped cost ordering')
    d.once('row_number()over(order by root_lot_id)::integer line_no,root_lot_id,po_id,component_units,',
        'row_number()over(order by kind,root_lot_id)::integer line_no,kind,root_lot_id,po_id,component_units,','return component kind in immutable plan')
    d.once('partition by po_id order by root_lot_id','partition by po_id order by kind,root_lot_id','return cent remainder across cost and base')
    d.once('as c(line_no integer,root_lot_id uuid,po_id uuid,component_units numeric,booked_value numeric)order by c.line_no;',
        """as c(line_no integer,kind text,root_lot_id uuid,po_id uuid,component_units numeric,booked_value numeric)where c.kind='BASE'order by c.line_no;
  insert into cp7_sku_conversion.return_cost_components_v3(sales_return_item_id,line_no,root_lot_id,po_id,component_units,booked_value)
  select r.id,c.line_no,c.root_lot_id,c.po_id,c.component_units,c.booked_value from jsonb_to_recordset(v_components)
   as c(line_no integer,kind text,root_lot_id uuid,po_id uuid,component_units numeric,booked_value numeric)where c.kind='COST'order by c.line_no;""",'separate return cost snapshots')
    d.once('(select sum(c.booked_value)from cp7_sku_conversion.sales_return_components_v2 c where c.sales_return_item_id=r.id)',
        snapshot_sum('sales_return_components_v2','return_cost_components_v3','sales_return_item_id','r.id'),'complete return amount check')
    d.once('select po_id,sum(booked_value)::numeric effective from cp7_sku_conversion.sales_return_components_v2 where sales_return_item_id=r.id group by po_id',
        'select po_id,sum(booked_value)::numeric effective from(\n    select po_id,booked_value from cp7_sku_conversion.sales_return_components_v2 where sales_return_item_id=r.id\n    union all select po_id,booked_value from cp7_sku_conversion.return_cost_components_v3 where sales_return_item_id=r.id)c group by po_id',
        'return cost journal attribution')
    d.once('end $$;',' perform cp7_sku_conversion.post_return_costs_v3(p_return);\nend $$;','return cost movement before Native posting')
    save(name,d)

    name='prepare_valuation_v2';d=edit(name)
    d.once('select c.line_no,c.root_lot_id,c.po_id,c.hpp_version_id,',"select 'BASE'::text kind,c.line_no,c.root_lot_id,c.po_id,c.hpp_version_id,",'base conversion contributors')
    d.once(' ), ranked as(',"""  union all
  select 'COST',c.line_no,c.root_lot_id,c.po_id,c.hpp_version_id,c.component_units,c.unit_value,c.value,
   round(c.component_units*v_qty/(s->>'qty')::numeric,12),round(c.component_units*v_qty/(s->>'qty')::numeric,12)*c.unit_value
  from cp7_sku_conversion.pool_cost_components_v3((p_preview->>'source_product_id')::uuid,(p_preview->>'location_id')::uuid,'GRADE_A')c
 ), ranked as(""",'cost ownership follows conversion even while zero')
    d.many('over(order by line_no','over(order by kind,line_no',2,'conversion combined cents order')
    d.once('sum(transfer_raw_value)over() total_raw_value',
        "sum(transfer_raw_value)over() total_raw_value,\n   bool_or(transfer_raw_value<0)over() signed_components,\n   row_number()over(order by kind,line_no) component_position,count(*)over() component_count",
        'signed contributor cents must not scale positive base value by a net-of-recovery denominator')
    d.once('case when v_transfer=0 then 0 else round(cumulative_value*v_transfer/nullif(total_raw_value,0),2)end',
        'case when signed_components then case when component_position=component_count then v_transfer else round(cumulative_value,2)end\n    when total_raw_value=0 then round(cumulative_value,2)else round(cumulative_value*v_transfer/total_raw_value,2)end',
        'signed cumulative raw cents preserve base ownership and assign only the final quoted residual')
    d.once(" )\n insert into cp7_sku_conversion.valuation_contributors_v2(group_id,line_no,root_lot_id,po_id,hpp_version_id,pool_component_units,transfer_units,unit_value,contributed_value,transfer_value)\n select p_group,line_no,root_lot_id,po_id,hpp_version_id,pool_component_units,transfer_units,unit_value,contributed_value,transfer_share from shares order by line_no;",
        """ ),saved_base as(
  insert into cp7_sku_conversion.valuation_contributors_v2(group_id,line_no,root_lot_id,po_id,hpp_version_id,pool_component_units,transfer_units,unit_value,contributed_value,transfer_value)
  select p_group,line_no,root_lot_id,po_id,hpp_version_id,pool_component_units,transfer_units,unit_value,contributed_value,transfer_share from shares where kind='BASE'order by line_no returning group_id
 )insert into cp7_sku_conversion.cost_contributors_v3(group_id,line_no,root_lot_id,po_id,hpp_version_id,pool_component_units,transfer_units,unit_value,contributed_value,transfer_value)
 select p_group,line_no,root_lot_id,po_id,hpp_version_id,pool_component_units,transfer_units,unit_value,contributed_value,transfer_share from shares where kind='COST'and transfer_units>0 order by line_no;""",'immutable conversion cost contributors')
    d.once('(select coalesce(sum(transfer_value),0)from cp7_sku_conversion.valuation_contributors_v2 where group_id=p_group)',
        '(select coalesce(sum(transfer_value),0)from(\n  select transfer_value from cp7_sku_conversion.valuation_contributors_v2 where group_id=p_group\n  union all select transfer_value from cp7_sku_conversion.cost_contributors_v3 where group_id=p_group)c)',
        'complete conversion transfer amount')
    save(name,d)

    name='finalize_valuation_v2';d=edit(name)
    d.once('select po_id,sum(transfer_value)::numeric effective from cp7_sku_conversion.valuation_contributors_v2 where group_id=p_group group by po_id',
        'select po_id,sum(transfer_value)::numeric effective from(\n  select po_id,transfer_value from cp7_sku_conversion.valuation_contributors_v2 where group_id=p_group\n  union all select po_id,transfer_value from cp7_sku_conversion.cost_contributors_v3 where group_id=p_group)c group by po_id',
        'conversion native journal correction by complete source PO')
    d.once('end $$;',' perform cp7_sku_conversion.finalize_costs_v3(p_group);\nend $$;','post all native zero cost allocation roots')
    save(name,d)

    name='reverse_valuation_v2';d=edit(name)
    d.once("v_lines jsonb:='[]'::jsonb;r record;", "v_lines jsonb:='[]'::jsonb;r record;v_inverse_before jsonb;",'current inverse proof state')
    d.once(' v_delta:=-p.correction_value;', ' v_inverse_before:=cp7_sku_conversion.capture_group_inverse_v3(p_group);\n v_delta:=-p.correction_value;',
        'require exact books after retained Native inverse and before historical correction')
    d.once('end $$;'," perform cp7_sku_conversion.reverse_costs_v3('SKU_CONVERSION',p_group);\nend $$;",'append exact inverse cost events')
    d.once('end $$;', ' perform cp7_sku_conversion.rebalance_group_inverse_v3(p_group,v_inverse_before);\nend $$;',
        'zero source change and balanced current inverse after immutable historical reversal')
    save(name,d)

    name='status_component_reverse_v2';d=edit(name)
    d.once("v_type:=case when tg_table_name='sales_headers'then'SALE'else'SALES_RETURN'end;v_id:=new.id;",
        "v_type:=case when tg_table_name='sales_headers'then'SALE'else'SALES_RETURN'end;v_id:=new.id;\n perform cp7_sku_conversion.reverse_costs_v3(v_type,v_id);",'status reversal includes cost facts before early return')
    save(name,d)

    name='hpp_scope_lot_ids_v2';d=edit(name)
    d.once(")select coalesce(array_agg(id order by id),'{}'::uuid[])from roots", """ union select e.root_lot_id from cp7_sku_conversion.cost_events_v3 e join erp.fg_lots l on l.id=e.root_lot_id
  where(p_po is null and l.po_id is null and e.product_id=p_product)or l.po_id=p_po
 union select c.root_lot_id from cp7_sku_conversion.sale_cost_components_v3 c
  join cp7_sku_conversion.sale_allocation_values_v2 v using(sale_stock_allocation_id)
  where(p_po is null and c.po_id is null and v.product_id=p_product)or c.po_id=p_po
 union select c.root_lot_id from cp7_sku_conversion.return_cost_components_v3 c
  join cp7_sku_conversion.sales_return_values_v2 v using(sales_return_item_id)
  where(p_po is null and c.po_id is null and v.product_id=p_product)or c.po_id=p_po
 )select coalesce(array_agg(id order by id),'{}'::uuid[])from roots""",'source lock closure includes cost roots')
    save(name,d)
    return result,routes


if __name__=='__main__':
    import json,sys
    definitions,routes=derive()
    Path(sys.argv[1]).write_text(json.dumps(dict(definitions=definitions,routes=routes),sort_keys=True)+'\n')
    print(json.dumps(dict(status='REVERSIBLE_COST_VALUATION_DEFINITIONS_PREPARED',functions=len(definitions),routes=sum(map(len,routes.values())),actual_ERP_cases=0)))
