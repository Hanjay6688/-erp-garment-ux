create function cp7_credit.current_leaf_assignment(p_sale uuid)
returns table(root_sale_id uuid,current_leaf_id uuid,customer_id uuid,requested_status text)
language plpgsql stable security definer set search_path='' as $$
declare roots uuid[];ids uuid[];previous uuid;root uuid;revision bigint:=0;r record;h erp.sales_headers;
begin
 select * into strict h from erp.sales_headers where id=p_sale;
 select array_agg(distinct x.root_sale_id) into roots from cp7_note.revisions x
  where p_sale in(x.root_sale_id,x.previous_sale_id,x.replacement_sale_id);
 if cardinality(roots)>1 then raise exception 'CP7_CREDIT_NOTE_ROOT_AMBIGUOUS';end if;
 root:=coalesce(roots[1],p_sale);previous:=root;ids:=array[root];
 for r in select *from cp7_note.revisions x where x.root_sale_id=root order by x.revision loop
  revision:=revision+1;
  if r.revision<>revision or r.previous_sale_id<>previous or r.replacement_sale_id=any(ids)then
   raise exception 'CP7_CREDIT_NOTE_CHAIN_INVALID';end if;
  ids:=ids||r.replacement_sale_id;previous:=r.replacement_sale_id;
 end loop;
 if not p_sale=any(ids)or exists(select 1 from unnest(ids)x left join erp.sales_headers s on s.id=x
  where s.id is null or s.customer_id is distinct from h.customer_id)then
  raise exception 'CP7_CREDIT_NOTE_MEMBERSHIP_UNPROVEN';end if;
 if h.status in('POSTED','PARTIAL_PAID','PAID')and(p_sale<>previous or exists(
  select 1 from erp.sales_headers s where s.id=any(ids)and s.id<>p_sale
   and s.status in('POSTED','PARTIAL_PAID','PAID')))then
  raise exception 'CP7_CREDIT_ACTIVE_LEAF_AMBIGUOUS';end if;
 return query select root,previous,h.customer_id,h.status::text;
end $$;

create function cp7_credit.consumer_dependency_graph_v1(p_sale uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare customer uuid;members uuid[];roots uuid[]:='{}';leaves uuid[]:='{}';
 cohorts uuid[];families uuid[];node uuid;a record;facts jsonb;answer jsonb;
begin
 select customer_id into strict customer from erp.sales_headers where id=p_sale;
 with recursive edges(a,b)as(
  select root_sale_id,previous_sale_id from cp7_note.revisions
  union select root_sale_id,replacement_sale_id from cp7_note.revisions
  union select f.family_root_sale_id,c.source_sale_id from cp7_credit.cohorts c
   join cp7_credit.return_families f on f.id=c.family_id
  union select f.family_root_sale_id,e.target_sale_id from cp7_credit.consumption_events e
   join cp7_credit.cohorts c on c.id=e.cohort_id
   join cp7_credit.return_families f on f.id=c.family_id
   where e.event_kind='APPLY'
 ),connected(id)as(
  select p_sale union
  select case when e.a=g.id then e.b else e.a end from connected g
   join edges e on e.a=g.id or e.b=g.id
 )select array_agg(id order by id)into members from connected;
 foreach node in array members loop
  select *into strict a from cp7_credit.current_leaf_assignment(node);
  if a.customer_id is distinct from customer then
   raise exception 'CP7_CREDIT_CONSUMER_GRAPH_CUSTOMER_CHANGED';end if;
  roots:=roots||a.root_sale_id;leaves:=leaves||a.current_leaf_id;
 end loop;
 select array_agg(distinct x order by x)into roots from unnest(roots)x;
 select array_agg(distinct x order by x)into leaves from unnest(leaves)x;
 select coalesce(array_agg(id order by id),'{}')into families
  from cp7_credit.return_families where family_root_sale_id=any(roots);
 select coalesce(array_agg(id order by id),'{}')into cohorts
  from cp7_credit.cohorts where family_id=any(families);
 if exists(select 1 from cp7_credit.cohorts c join cp7_credit.return_families f on f.id=c.family_id
  cross join lateral cp7_credit.current_leaf_assignment(c.source_sale_id)m
  where c.id=any(cohorts)and(c.customer_id is distinct from customer
   or m.root_sale_id is distinct from f.family_root_sale_id))then
  raise exception 'CP7_CREDIT_CONSUMER_GRAPH_COHORT_ROOT_CHANGED';end if;
 facts:=jsonb_build_object(
  'headers',(select coalesce(jsonb_agg(to_jsonb(h)order by h.id),'[]')from erp.sales_headers h where h.id=any(members)),
  'revisions',(select coalesce(jsonb_agg(to_jsonb(r)order by r.root_sale_id,r.revision),'[]')from cp7_note.revisions r where r.root_sale_id=any(roots)),
  'families',(select coalesce(jsonb_agg(to_jsonb(f)order by f.id),'[]')from cp7_credit.return_families f where f.id=any(families)),
  'cohorts',(select coalesce(jsonb_agg(to_jsonb(c)order by c.id),'[]')from cp7_credit.cohorts c where c.id=any(cohorts)),
  'consumptions',(select coalesce(jsonb_agg(to_jsonb(e)order by e.id),'[]')from cp7_credit.consumption_events e where e.cohort_id=any(cohorts)));
 answer:=jsonb_build_object('contract_version','ow04.consumer-dependency-graph.v1',
  'requested_sale_id',p_sale,'customer_id',customer,'sale_ids',members,
  'root_sale_ids',roots,'current_leaf_ids',leaves,'family_ids',families,'cohort_ids',cohorts,
  'facts',facts,'facts_sha256',cp7_credit.pg_jsonb_sha256(facts),
  'source_authority_proven',false,'all_signed_consumer_history_included',true);
 return answer;
end $$;

create function cp7_credit.source_hpp_lot_ids_v1(p_sale uuid)returns uuid[]
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select coalesce(array_agg(l.id order by l.id),'{}'::uuid[])from erp.fg_lots l
 where l.product_id in(select i.product_id from erp.sales_items i where i.sale_id=p_sale)
  or l.po_id in(select l0.po_id from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id
   join erp.fg_lots l0 on l0.id=a.lot_id where i.sale_id=p_sale)
$$;

create function cp7_credit.initial_hpp_account_facts_v1()returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $function$
 select jsonb_build_object('mappings',(select jsonb_agg(to_jsonb(m)order by m.mapping_key)from erp.accounting_account_mappings m
  where m.mapping_key in('FG_INVENTORY','COGS','OTHER_EXPENSE','OTHER_INCOME')),
  'accounts',(select jsonb_agg(to_jsonb(c)order by c.id)from erp.chart_accounts c where c.id in(
   select m.account_id from erp.accounting_account_mappings m where m.mapping_key in('FG_INVENTORY','COGS','OTHER_EXPENSE','OTHER_INCOME'))))
$function$;

create function cp7_credit.source_first_nonpo_hpp_alignment_v1(p_snapshot jsonb)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare product uuid;fg uuid;cogs uuid;expense uuid;income uuid;t jsonb;b jsonb;rows jsonb:='[]';
begin
 select(x->>'account_id')::uuid into strict fg from jsonb_array_elements(p_snapshot#>'{hpp_accounts,mappings}')x where x->>'mapping_key'='FG_INVENTORY';
 select(x->>'account_id')::uuid into strict cogs from jsonb_array_elements(p_snapshot#>'{hpp_accounts,mappings}')x where x->>'mapping_key'='COGS';
 select(x->>'account_id')::uuid into strict expense from jsonb_array_elements(p_snapshot#>'{hpp_accounts,mappings}')x where x->>'mapping_key'='OTHER_EXPENSE';
 select(x->>'account_id')::uuid into strict income from jsonb_array_elements(p_snapshot#>'{hpp_accounts,mappings}')x where x->>'mapping_key'='OTHER_INCOME';
 if exists(select 1 from jsonb_array_elements(p_snapshot->'fg_lots')x where x->>'po_id'is not null)then
  raise exception 'CP7_CREDIT_SOURCE_PO_HPP_INVERSE_UNQUALIFIED';end if;
 for product in select distinct(x->>'product_id')::uuid from jsonb_array_elements(p_snapshot->'fg_lots')x loop
  select to_jsonb(v)into strict t from erp.compute_non_po_product_hpp_targets_v2620f(product)v;
  select jsonb_build_object('hpp_total_cost',q.f+q.c+q.o,'fg_value',q.f,'cogs_value',q.c,'other_out_value',q.o)into b
   from(select coalesce(sum(l.debit-l.credit)filter(where l.account_id=fg),0)f,
    coalesce(sum(l.debit-l.credit)filter(where l.account_id=cogs),0)c,
    coalesce(sum(l.debit-l.credit)filter(where l.account_id in(expense,income)),0)o
    from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
    left join erp.journal_entries original on original.id=j.reversal_of_id
    where l.product_id=product and l.po_id is null and j.status in('POSTED','REVERSED')
     and(j.source_type<>'PRODUCT_CONVERSION'or erp.be_nonpo_admitted_v1(j.source_id))
     and(j.source_type<>'JOURNAL_REVERSAL'or original.source_type is distinct from'PRODUCT_CONVERSION'
      or erp.be_nonpo_admitted_v1(original.source_id)))q;
  if t is distinct from b then raise exception 'CP7_CREDIT_SOURCE_NATIVE_HPP_TARGET_BOOK_UNQUALIFIED';end if;
  rows:=rows||jsonb_build_array(jsonb_build_object('product_id',product,'target',t,'book',b));
 end loop;
 return rows;
end $$;

create function cp7_credit.pg_jsonb_sha256(p jsonb) returns text
language sql immutable security invoker set search_path='' as $$
 select encode(pg_catalog.sha256(convert_to(p::text,'UTF8')),'hex')
$$;

