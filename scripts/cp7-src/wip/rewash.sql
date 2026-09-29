-- Range records prove reuse of the same input. They never add a new pool.
create function cp7_wip.redispatch_valid(f jsonb) returns boolean
language sql immutable security invoker set search_path='' as $$
with events as(select * from jsonb_to_recordset(f->'redispatch') as x(id uuid,event_type text,source_id uuid,successor_id uuid,
 qty_pcs numeric,source_offset_pcs bigint,successor_offset_pcs bigint,releases_allocation_event_id uuid)),
active as(select * from events e where e.event_type='ALLOCATE' and not exists(select 1 from events z where z.event_type='RELEASE' and z.releases_allocation_event_id=e.id)),
sizes as(select * from jsonb_to_recordset(f->'delivery_sizes') as x(id uuid,delivery_line_id uuid,batch_id uuid,size_id uuid,qty_pcs numeric,group_id uuid)),
deliveries as(select * from jsonb_to_recordset(f->'deliveries') as x(id uuid,delivery_id uuid,status text)),
failed as(select * from jsonb_to_recordset(f->'failed') as x(id uuid,receipt_line_id uuid,custody_outcome text)),
failed_sizes as(select * from jsonb_to_recordset(f->'failed_sizes') as x(attempt_id uuid,delivery_size_id uuid,qty_pcs numeric)),
receipts as(select * from jsonb_to_recordset(f->'receipts') as x(id uuid,status text)),
invalid as(
 select e.id from active e left join sizes s on s.id=e.source_id left join sizes d on d.id=e.successor_id
 left join deliveries sd on sd.id=s.delivery_line_id left join deliveries dd on dd.id=d.delivery_line_id
 where s.id is null or d.id is null or s.batch_id is distinct from d.batch_id or s.size_id is distinct from d.size_id
  or s.group_id is distinct from d.group_id or sd.status is distinct from 'REVERSED' or dd.status is null or dd.status in ('DRAFT','REVERSED')
  or e.qty_pcs is null or e.source_offset_pcs is null or e.successor_offset_pcs is null
  or e.qty_pcs<=0 or e.source_offset_pcs<0 or e.successor_offset_pcs<0
  or e.source_offset_pcs+e.qty_pcs>s.qty_pcs or e.successor_offset_pcs+e.qty_pcs>d.qty_pcs
  or not exists(select 1 from failed_sizes fs join failed fa on fa.id=fs.attempt_id join receipts r on r.id=fa.receipt_line_id
    where fs.delivery_size_id=s.id and fs.qty_pcs=s.qty_pcs and fa.custody_outcome='RETURN_UNPROCESSED' and r.status='POSTED')
),overlap as(
 select e.id from active e join active other on other.id>e.id
 where (e.source_id=other.source_id and numrange(e.source_offset_pcs,e.source_offset_pcs+e.qty_pcs,'[)') && numrange(other.source_offset_pcs,other.source_offset_pcs+other.qty_pcs,'[)'))
  or (e.successor_id=other.successor_id and numrange(e.successor_offset_pcs,e.successor_offset_pcs+e.qty_pcs,'[)') && numrange(other.successor_offset_pcs,other.successor_offset_pcs+other.qty_pcs,'[)'))
)
select not exists(select 1 from invalid) and not exists(select 1 from overlap)
$$;
