-- Owning correction of a posted material receipt ("Benerin penerimaan").
-- The posted receipt, its lines, rolls and stock/journal facts stay immutable
-- history: the receipt is reversed at its own physical time and an exact
-- replacement document takes its place at that same time. Rolls of the same
-- material keep their identity (cutting, transfers and cards keep pointing at
-- the same physical roll); a roll recorded under the wrong material moves its
-- cutting use, at each use's own time, to a roll of the right material.
-- Every stock, cost, HPP and journal effect uses accepted Native writers in
-- this one transaction. No Native definition, owner or ACL is changed.
create schema cp7_receipt_fix authorization cp7_procure_write;
revoke all on schema cp7_receipt_fix from public,anon,authenticated,service_role,cp7_capture;
create table cp7_receipt_fix.requests(
 actor uuid not null,request_id uuid not null,payload jsonb not null,expected_version text not null,
 response jsonb,primary key(actor,request_id)
);
create table cp7_receipt_fix.revisions(
 id uuid primary key default gen_random_uuid(),
 root_purchase_id uuid not null references erp.material_purchase_headers,
 previous_purchase_id uuid not null unique references erp.material_purchase_headers,
 replacement_purchase_id uuid not null unique references erp.material_purchase_headers,
 revision bigint not null,actor uuid not null,request_id uuid not null,reason text not null,
 effective_at timestamptz not null,recorded_at timestamptz not null default clock_timestamp(),
 previous_document jsonb not null,corrected_document jsonb not null,
 unique(root_purchase_id,revision),unique(actor,request_id)
);
-- Physical roll lineage. REPARENTED keeps the roll id; MATERIAL_MOVED links the
-- wrong-material roll to its right-material successor; REMOVED/ADDED close and
-- open rolls that the corrected document does (not) contain.
create table cp7_receipt_fix.roll_lineage(
 correction_id uuid not null references cp7_receipt_fix.revisions(id) deferrable initially deferred,
 kind text not null check(kind in('REPARENTED','MATERIAL_MOVED','REMOVED','ADDED')),
 old_roll_id uuid references erp.material_rolls,new_roll_id uuid references erp.material_rolls,
 old_material_id uuid references erp.materials,new_material_id uuid references erp.materials,
 old_purchase_item_id uuid references erp.material_purchase_items,new_purchase_item_id uuid references erp.material_purchase_items,
 old_qty numeric(18,6),new_qty numeric(18,6),roll_number text not null,
 recorded_at timestamptz not null default clock_timestamp(),
 check((kind='ADDED')=(old_roll_id is null)),check((kind='REMOVED')=(new_roll_id is null))
);
create index receipt_fix_roll_old on cp7_receipt_fix.roll_lineage(old_roll_id);
create index receipt_fix_roll_new on cp7_receipt_fix.roll_lineage(new_roll_id);
-- A cutting use recorded against a wrong-material roll keeps its single row,
-- quantity, physical/recorded time, cost basis and cutting source. Only its
-- material/roll attribute follows the corrected roll; the prior attribute is
-- kept here. (A reverse-and-reissue pair would be counted twice by the frozen
-- per-PO WIP conservation check, or dropped by the frozen HPP rebuild.)
create table cp7_receipt_fix.movement_lineage(
 movement_id uuid not null references erp.material_stock_movements,
 correction_id uuid not null references cp7_receipt_fix.revisions(id) deferrable initially deferred,
 old_material_id uuid not null references erp.materials,old_roll_id uuid not null references erp.material_rolls,
 new_material_id uuid not null references erp.materials,new_roll_id uuid not null references erp.material_rolls,
 qty_signed numeric(18,6) not null,physical_at timestamptz not null,source_type text not null,source_id uuid not null,
 recorded_at timestamptz not null default clock_timestamp(),primary key(movement_id,correction_id)
);
create table cp7_receipt_fix.journal_restatements(
 inverse_journal_id uuid primary key references erp.journal_entries,
 source_journal_id uuid not null unique references erp.journal_entries,
 previous_purchase_id uuid not null references erp.material_purchase_headers,
 neutral_journal_id uuid not null unique references erp.journal_entries,
 effective_journal_id uuid not null unique references erp.journal_entries,
 native_economic_date date not null,corrected_economic_date date not null,
 recorded_at timestamptz not null default clock_timestamp()
);
-- Every real supplier payment is replayed at its own date, cash account and
-- amount. A payment larger than the corrected payable is split: the corrected
-- receipt first, the excess as supplier credit on other receipts of the same
-- supplier chosen by the owner (owner decision 2 Oct 2026: "retur bayangan",
-- goods never received; the credit is cut from any next nota).
create table cp7_receipt_fix.payment_replays(
 replacement_payment_id uuid primary key references erp.supplier_payments,
 previous_payment_id uuid not null references erp.supplier_payments,
 correction_id uuid not null references cp7_receipt_fix.revisions(id) deferrable initially deferred,
 target_purchase_id uuid not null references erp.material_purchase_headers,
 kind text not null check(kind in('CORRECTED_RECEIPT','CREDIT_TO_OTHER_RECEIPT')),
 amount numeric(20,2) not null check(amount>0),
 recorded_at timestamptz not null default clock_timestamp()
);
create index receipt_fix_payment_previous on cp7_receipt_fix.payment_replays(previous_payment_id);
-- Main material card grouping: each compensating receipt movement is shown
-- under the original receipt row it corrects (effective quantity), while the
-- raw immutable rows stay available as audit members.
create table cp7_receipt_fix.ledger_links(
 member_id uuid primary key references erp.material_stock_movements,
 origin_id uuid not null references erp.material_stock_movements,
 correction_id uuid not null references cp7_receipt_fix.revisions(id) deferrable initially deferred,
 recorded_at timestamptz not null default clock_timestamp()
);
create index receipt_fix_ledger_origin on cp7_receipt_fix.ledger_links(origin_id);
-- A supplier invoice of the corrected receipt is reversed by the Native writer
-- and posted again, with the corrected lines, at its own invoice/book date.
create table cp7_receipt_fix.invoice_replays(
 previous_invoice_id uuid primary key references erp.material_supplier_invoices,
 replacement_invoice_id uuid not null unique references erp.material_supplier_invoices,
 correction_id uuid not null references cp7_receipt_fix.revisions(id) deferrable initially deferred,
 previous_lines jsonb not null,corrected_lines jsonb not null,
 recorded_at timestamptz not null default clock_timestamp()
);
-- The Native invoice reversal is dated today. Its exact effect is moved, per
-- account/dimension, to the dates the same invoice posts on at its own book
-- date under the current facts (measured by a rolled-back Native dry run).
create table cp7_receipt_fix.invoice_restatements(
 journal_id uuid primary key references erp.journal_entries,
 invoice_id uuid not null references erp.material_supplier_invoices,
 correction_id uuid not null references cp7_receipt_fix.revisions(id) deferrable initially deferred,
 economic_date date not null,native_journal_ids uuid[] not null,
 recorded_at timestamptz not null default clock_timestamp()
);
create table cp7_receipt_fix.context(
 backend_pid integer not null,transaction_id bigint not null,actor uuid not null,
 source_purchase_id uuid not null,primary key(backend_pid,transaction_id)
);
do $own$
declare t text;
begin
 foreach t in array array['requests','revisions','roll_lineage','movement_lineage','journal_restatements','payment_replays','ledger_links','invoice_replays','invoice_restatements','context']loop
  execute format('alter table cp7_receipt_fix.%I owner to postgres',t);
  execute format('alter table cp7_receipt_fix.%I enable row level security',t);
  execute format('create policy private_%s on cp7_receipt_fix.%I for all using(false)with check(false)',t,t);
 end loop;
end $own$;
revoke all on all tables in schema cp7_receipt_fix from public,anon,authenticated,service_role,cp7_capture;

create function cp7_receipt_fix.immutable()returns trigger
language plpgsql security invoker set search_path=''as $$
begin raise exception 'CP7_RECEIPT_FIX_HISTORY_IMMUTABLE';end $$;
create trigger immutable_revision before update or delete on cp7_receipt_fix.revisions for each row execute function cp7_receipt_fix.immutable();
create trigger immutable_roll_lineage before update or delete on cp7_receipt_fix.roll_lineage for each row execute function cp7_receipt_fix.immutable();
create trigger immutable_movement_lineage before update or delete on cp7_receipt_fix.movement_lineage for each row execute function cp7_receipt_fix.immutable();
create trigger immutable_journal_restatement before update or delete on cp7_receipt_fix.journal_restatements for each row execute function cp7_receipt_fix.immutable();
create trigger immutable_payment_replay before update or delete on cp7_receipt_fix.payment_replays for each row execute function cp7_receipt_fix.immutable();
create trigger immutable_ledger_link before update or delete on cp7_receipt_fix.ledger_links for each row execute function cp7_receipt_fix.immutable();
create trigger immutable_invoice_replay before update or delete on cp7_receipt_fix.invoice_replays for each row execute function cp7_receipt_fix.immutable();
create trigger immutable_invoice_restatement before update or delete on cp7_receipt_fix.invoice_restatements for each row execute function cp7_receipt_fix.immutable();

create function cp7_receipt_fix.access_now()returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare a jsonb;k text;
begin
 if auth.uid()is null or coalesce(auth.jwt()->>'role','')<>'authenticated'
  then raise exception using errcode='42501',message='CP7_RECEIPT_FIX_ACCESS_DENIED';end if;
 a:=erp.get_my_access_v1();
 if a->'allowed'is distinct from'true'::jsonb or erp.has_permission('warehouse.procurement.view')is distinct from true then
  raise exception using errcode='42501',message='CP7_RECEIPT_FIX_ACCESS_DENIED';end if;
 if coalesce(a->'profile'->>'role_code','')not in('OWNER','ADMIN')then
  raise exception using errcode='42501',message='CP7_RECEIPT_FIX_OWNER_ADMIN_REQUIRED';end if;
 foreach k in array array['warehouse.procurement.create','warehouse.procurement.post','warehouse.procurement.reverse','finance.ap.view']loop
  if erp.has_permission(k)is distinct from true then raise exception using errcode='42501',message='CP7_RECEIPT_FIX_ACCESS_DENIED';end if;
 end loop;
 return a;
end $$;

-- Native writers admit an authenticated caller only inside a declared,
-- transaction/actor-bound procurement context. This command owns that context
-- for its own duration and switches it per writer (draft save vs posting).
create function cp7_receipt_fix.admit(p_action text)returns void
language plpgsql volatile security definer set search_path=''as $$
begin
 if not exists(select 1 from cp7_receipt_fix.context where backend_pid=pg_backend_pid()
  and transaction_id=txid_current()and actor=auth.uid())then
  raise exception using errcode='42501',message='CP7_RECEIPT_FIX_PRIVATE_CONTEXT_REQUIRED';end if;
 delete from cp7_procurement.execution_context where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 if p_action is not null then
  insert into cp7_procurement.execution_context values(pg_backend_pid(),txid_current(),auth.uid(),p_action,
   case p_action when 'SAVE_DRAFT' then 'warehouse.procurement.create' else 'warehouse.procurement.post' end);
 end if;
end $$;

-- Exact receipt state the reviewer saw: header, lines, rolls, every stock
-- movement on its rolls/lines, cutting use, payments and dependent documents.
create function cp7_receipt_fix.review_token(p_purchase uuid)returns text
language sql stable security definer set search_path='' set "TimeZone"='UTC' as $$
 with items as(select*from erp.material_purchase_items where purchase_id=p_purchase),
 rolls as(select r.*from erp.material_rolls r join items i on i.id=r.purchase_item_id),
 moves as(select m.*from erp.material_stock_movements m where m.roll_id in(select id from rolls)
  or(m.source_type='MATERIAL_PURCHASE_ITEM'and m.source_id in(select id from items)))
 select md5(jsonb_build_object(
  'h',(select jsonb_build_array(h.row_version,h.status,h.payment_status,h.physical_at,h.supplier_id,h.location_id)from erp.material_purchase_headers h where h.id=p_purchase),
  'i',(select coalesce(jsonb_agg(jsonb_build_array(i.id,i.material_id,i.qty,i.unit_price,i.price_state,i.price_source,i.invoice_match_state)order by i.id),'[]')from items i),
  'r',(select coalesce(jsonb_agg(jsonb_build_array(r.id,r.material_id,r.roll_number,r.original_qty,r.status)order by r.id),'[]')from rolls r),
  'm',(select coalesce(jsonb_agg(jsonb_build_array(m.id,m.material_id,m.roll_id,m.qty_signed,m.physical_at,m.reversal_of_id)order by m.id),'[]')from moves m),
  'c',(select coalesce(jsonb_agg(jsonb_build_array(c.id,c.cutting_group_id,c.roll_id,c.qty_issued,c.qty_consumed,c.qty_physically_returned)order by c.id),'[]')
   from erp.cutting_group_rolls c where c.roll_id in(select id from rolls)),
  'p',(select coalesce(jsonb_agg(jsonb_build_array(p.id,p.status,p.amount,p.payment_date)order by p.id),'[]')from erp.supplier_payments p where p.purchase_id=p_purchase),
  'v',(select coalesce(jsonb_agg(jsonb_build_array(l.id,v.id,v.status)order by l.id),'[]')from erp.material_supplier_invoice_lines l
   join erp.material_supplier_invoices v on v.id=l.invoice_id where l.purchase_item_id in(select id from items)),
  'x',(select coalesce(jsonb_agg(jsonb_build_array(x.id,s.id,s.status)order by x.id),'[]')from erp.material_supplier_return_items x
   join erp.material_supplier_returns s on s.id=x.return_id where x.purchase_item_id in(select id from items)),
  'k',(select coalesce(jsonb_agg(jsonb_build_array(k.id,k.status)order by k.id),'[]')from erp.material_purchase_cost_corrections k where k.purchase_id=p_purchase),
  'b',(select coalesce(jsonb_agg(jsonb_build_array(b.id)order by b.id),'[]')from erp.bf_supplier_credit_moves_v1 b where p_purchase in(b.source_purchase_id,b.target_purchase_id)),
  'o',(select coalesce(jsonb_agg(jsonb_build_array(o.usage_id,o.purchase_item_id)order by o.usage_id,o.purchase_item_id),'[]')from erp.be_pocket_receipt_origins_v1 o where o.purchase_item_id in(select id from items))
 )::text)$$;

-- Physical use of one roll at the receipt location, after its own receipt:
-- every active non-receipt movement and the deepest running use. A corrected
-- quantity below that use would contradict the physical history.
create function cp7_receipt_fix.roll_use(p_roll uuid,p_location uuid)returns jsonb
language sql stable security definer set search_path=''as $$
 with active as(
  select m.*from erp.material_stock_movements m where m.roll_id=p_roll and m.reversal_of_id is null
   and m.source_type not in('MATERIAL_PURCHASE_ROLL','MATERIAL_PURCHASE_ITEM')
   and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=m.id)
 ),here as(
  select sum(qty_signed)over(order by physical_at,system_created_at,id rows unbounded preceding)prefix from active where location_id=p_location
 )
 select jsonb_build_object(
  'used_qty',coalesce((select -sum(qty_signed)from active where location_id=p_location),0)::text,
  'min_qty',greatest(0,-coalesce((select min(prefix)from here),0))::text,
  'uses',coalesce((select jsonb_agg(jsonb_build_object('source_type',source_type,'movement_type',movement_type,'count',n)order by source_type,movement_type)
   from(select source_type,movement_type,count(*)n from active group by 1,2)u),'[]'),
  'movable',not exists(select 1 from active where source_type not in('CUTTING_GROUP','CUTTING_GROUP_RETURN')))$$;

create function cp7_receipt_fix.blockers(p_purchase uuid)returns jsonb
language sql stable security definer set search_path=''as $$
 select coalesce(jsonb_agg(b order by b->>'code'),'[]')from(
  select jsonb_build_object('code','CP7_RECEIPT_FIX_INVOICE_SHARED','count',count(*))b from erp.material_supplier_invoices v
   where v.status='POSTED'and v.id in(select l.invoice_id from erp.material_supplier_invoice_lines l join erp.material_purchase_items i on i.id=l.purchase_item_id where i.purchase_id=p_purchase)
    and v.id in(select l.invoice_id from erp.material_supplier_invoice_lines l join erp.material_purchase_items i on i.id=l.purchase_item_id where i.purchase_id<>p_purchase)
   having count(*)>0
  union all select jsonb_build_object('code','CP7_RECEIPT_FIX_PENDING_CHILD_REVIEW_REQUIRED','count',count(*))from(
   select l.id from erp.material_supplier_invoice_lines l join erp.material_supplier_invoices v on v.id=l.invoice_id
    join erp.material_purchase_items i on i.id=l.purchase_item_id where i.purchase_id=p_purchase and v.status='DRAFT'
   union all select x.id from erp.material_supplier_return_items x join erp.material_supplier_returns s on s.id=x.return_id
    join erp.material_purchase_items i on i.id=x.purchase_item_id where i.purchase_id=p_purchase and s.status='DRAFT'
   union all select p.id from erp.supplier_payments p where p.purchase_id=p_purchase and p.status='DRAFT'
   union all select k.id from erp.material_purchase_cost_corrections k where k.purchase_id=p_purchase and k.status='DRAFT')d having count(*)>0
  union all select jsonb_build_object('code','CP7_RECEIPT_FIX_RETURN_ACTIVE','count',count(*))from erp.material_supplier_return_items x
   join erp.material_supplier_returns s on s.id=x.return_id join erp.material_purchase_items i on i.id=x.purchase_item_id
   where i.purchase_id=p_purchase and s.status='POSTED' having count(*)>0
  union all select jsonb_build_object('code','CP7_RECEIPT_FIX_COST_CORRECTION_ACTIVE','count',count(*))from erp.material_purchase_cost_corrections k
   where k.purchase_id=p_purchase and k.status='POSTED' having count(*)>0
  union all select jsonb_build_object('code','CP7_RECEIPT_FIX_SUPPLIER_CREDIT_ACTIVE','count',count(*))from erp.bf_supplier_credit_moves_v1 b
   where p_purchase in(b.source_purchase_id,b.target_purchase_id)having count(*)>0
  union all select jsonb_build_object('code','CP7_RECEIPT_FIX_POCKET_ORIGIN_ACTIVE','count',count(*))from erp.be_pocket_receipt_origins_v1 o
   join erp.material_purchase_items i on i.id=o.purchase_item_id where i.purchase_id=p_purchase having count(*)>0
  union all select jsonb_build_object('code','CP7_RECEIPT_FIX_OPENING_IMPORT_USE_IMPORT_WORKFLOW','count',1)
   where exists(select 1 from erp.initial_import_receipt_headers where purchase_id=p_purchase)
 )x$$;

create function cp7_receipt_fix.workspace(p_purchase uuid)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare a jsonb;root uuid;leaf uuid;h erp.material_purchase_headers%rowtype;history jsonb;lines jsonb;pays jsonb;blocks jsonb;invoices jsonb;targets jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_receipt_fix.access_now();
 if p_purchase is null then raise exception 'CP7_RECEIPT_FIX_SOURCE_REQUIRED';end if;
 select root_purchase_id into root from cp7_receipt_fix.revisions where replacement_purchase_id=p_purchase or previous_purchase_id=p_purchase order by revision desc limit 1;
 root:=coalesce(root,p_purchase);
 select replacement_purchase_id into leaf from cp7_receipt_fix.revisions where root_purchase_id=root order by revision desc limit 1;
 leaf:=coalesce(leaf,root);
 select*into h from erp.material_purchase_headers where id=leaf;
 if h.id is null then raise exception 'CP7_RECEIPT_FIX_NOT_FOUND';end if;
 select coalesce(jsonb_agg(jsonb_build_object('revision_id',r.id,'revision',r.revision::text,'previous_purchase_id',r.previous_purchase_id,
  'previous_purchase_number',(select purchase_number from erp.material_purchase_headers where id=r.previous_purchase_id),
  'replacement_purchase_id',r.replacement_purchase_id,'replacement_purchase_number',(select purchase_number from erp.material_purchase_headers where id=r.replacement_purchase_id),
  'effective_at',r.effective_at,'recorded_at',r.recorded_at,'reason',r.reason,
  'actor_name',(select u.full_name from erp.app_users u where u.auth_user_id=r.actor limit 1),
  'previous_document',r.previous_document,'corrected_document',r.corrected_document)order by r.revision),'[]')into history
 from cp7_receipt_fix.revisions r where r.root_purchase_id=root;
 select coalesce(jsonb_agg(jsonb_build_object('item_id',i.id,'material_id',i.material_id,'material_sku',m.material_sku,'material_name',m.material_name,
  'material_type',m.material_type,'unit_code',m.unit_code,'qty',i.qty::text,'unit_price',i.unit_price::text,'line_total',i.line_total::text,
  -- An invoice-matched line is a receipt estimate; its final price lives on the supplier invoice (Native match state).
  'price_state',case when i.invoice_match_state in('PARTIAL','MATCHED')then 'ESTIMATED'else i.price_state end,
  'price_source',case when i.invoice_match_state in('PARTIAL','MATCHED')then i.receipt_price_source_snapshot else i.price_source end,
  'invoice_match_state',i.invoice_match_state,'lot_number',i.lot_number,'notes',i.notes,
  'rolls',(select coalesce(jsonb_agg(jsonb_build_object('roll_id',r.id,'roll_number',r.roll_number,'qty',r.original_qty::text,
    'cached_qty',r.cached_qty::text,'status',r.status)||cp7_receipt_fix.roll_use(r.id,h.location_id)order by r.roll_number,r.id),'[]')
   from erp.material_rolls r where r.purchase_item_id=i.id))order by i.id),'[]')into lines
 from erp.material_purchase_items i join erp.materials m on m.id=i.material_id where i.purchase_id=leaf;
 select coalesce(jsonb_agg(jsonb_build_object('payment_id',p.id,'payment_number',p.payment_number,'payment_date',p.payment_date,
  'amount',p.amount::text,'status',p.status)order by p.payment_date,p.id),'[]')into pays
 from erp.supplier_payments p where p.purchase_id=leaf and p.status in('POSTED','DRAFT');
 select coalesce(jsonb_agg(jsonb_build_object('invoice_id',v.id,'invoice_number',v.invoice_number,'invoice_date',v.invoice_date,
  'received_at',v.received_at,'due_date',v.due_date,'row_version',v.row_version::text,'notes',v.notes,
  'lines',(select jsonb_agg(jsonb_build_object('invoice_line_id',l.id,'purchase_item_id',l.purchase_item_id,'qty_invoiced',l.qty_invoiced::text,
   'unit_price',l.unit_price::text,'discount_amount',l.discount_amount::text,'net_amount',l.net_amount::text,'notes',l.notes)order by l.id)
   from erp.material_supplier_invoice_lines l where l.invoice_id=v.id))order by v.invoice_date,v.posted_at,v.id),'[]')into invoices
 from erp.material_supplier_invoices v where v.status='POSTED'and v.id in(select l.invoice_id from erp.material_supplier_invoice_lines l
  join erp.material_purchase_items i on i.id=l.purchase_item_id where i.purchase_id=leaf);
 -- Receipts of the same supplier that still owe money: where an overpayment
 -- becomes credit (retur bayangan) when the corrected total is lower.
 select coalesce(jsonb_agg(jsonb_build_object('purchase_id',t.id,'purchase_number',t.purchase_number,'physical_at',t.physical_at,
   'remaining',t.remaining::text)order by t.physical_at desc,t.id),'[]')into targets
 from(select t0.*from(select x.id,x.purchase_number,x.physical_at,(round(erp.material_purchase_payable_total(x.id),2)
   -coalesce((select sum(p.amount)from erp.supplier_payments p where p.purchase_id=x.id and p.status='POSTED'),0))::numeric(20,2)remaining
  from erp.material_purchase_headers x where x.supplier_id=h.supplier_id and x.status='POSTED'and x.id<>leaf)t0
 where t0.remaining>0 order by t0.physical_at desc,t0.id limit 50)t;
 blocks:=case when h.status<>'POSTED'then jsonb_build_array(jsonb_build_object('code','CP7_RECEIPT_FIX_ACTIVE_POSTED_ONLY','count',1))
  else cp7_receipt_fix.blockers(leaf)end;
 if cp7_receipt_fix.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_RECEIPT_FIX_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.receipt-correction-workspace.v1','read_at',clock_timestamp(),
  'root_purchase_id',root,'current_purchase_id',leaf,
  'original_purchase_number',(select purchase_number from erp.material_purchase_headers where id=root),
  'purchase',jsonb_build_object('purchase_id',h.id,'purchase_number',h.purchase_number,'status',h.status,'row_version',h.row_version::text,
   'supplier_id',h.supplier_id,'supplier_name',(select supplier_name from erp.suppliers where id=h.supplier_id),
   'location_id',h.location_id,'location_name',(select location_name from erp.locations where id=h.location_id),
   'physical_at',h.physical_at,'payment_status',h.payment_status,'supplier_invoice_number',h.supplier_invoice_number,'due_date',h.due_date,'notes',h.notes),
  'lines',lines,'invoices',invoices,'payments',pays,'credit_targets',targets,'paid_total',(select coalesce(sum(amount),0)::text from erp.supplier_payments where purchase_id=leaf and status='POSTED'),
  'blockers',blocks,'can_correct',jsonb_array_length(blocks)=0,'review_token',cp7_receipt_fix.review_token(leaf),
  'history',history,'production_go',false);
end $$;

-- Moves the exact economic effect of a today-dated generic inverse to the
-- original economic date through a source-owned neutral/effective pair. The
-- Native inverse line set, its posting fact and closed-period rule are kept.
create function cp7_receipt_fix.restate(p_inverse uuid,p_reason text)returns void
language plpgsql volatile security definer set search_path=''as $$
declare original erp.journal_entries%rowtype;inverse erp.journal_entries%rowtype;src uuid;lines jsonb;neutral uuid;effective uuid;
begin
 select source_purchase_id into strict src from cp7_receipt_fix.context
  where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid();
 select*into strict inverse from erp.journal_entries where id=p_inverse;
 select*into strict original from erp.journal_entries where id=inverse.reversal_of_id;
 if original.status<>'REVERSED'or inverse.status<>'POSTED'or inverse.source_type<>'JOURNAL_REVERSAL'or inverse.source_id<>original.id
  or not(original.source_type in('MATERIAL_PURCHASE','MATERIAL_PURCHASE_GRNI_RECLASS')and original.source_id=src
   or original.source_type='SUPPLIER_PAYMENT'and exists(select 1 from erp.supplier_payments where id=original.source_id and purchase_id=src))then
  raise exception 'CP7_RECEIPT_FIX_JOURNAL_SOURCE_CHANGED';end if;
 if original.economic_date=inverse.economic_date then return;end if;
 select jsonb_agg(jsonb_build_object('account_id',j.account_id,'debit',j.credit,'credit',j.debit,'description',j.description,
  'customer_id',j.customer_id,'vendor_id',j.vendor_id,'contractor_id',j.contractor_id,'po_id',j.po_id,'product_id',j.product_id)order by j.id)
 into lines from erp.journal_lines j where j.journal_entry_id=inverse.id;
 neutral:=erp.post_journal('RECEIPT_FIX_REVERSAL_TIME_NEUTRAL',inverse.id,inverse.economic_date,
  'Benerin penerimaan: pindahkan waktu ekonomi pembalikan | '||p_reason,lines);
 select jsonb_agg(jsonb_build_object('account_id',j.account_id,'debit',j.debit,'credit',j.credit,'description',j.description,
  'customer_id',j.customer_id,'vendor_id',j.vendor_id,'contractor_id',j.contractor_id,'po_id',j.po_id,'product_id',j.product_id)order by j.id)
 into lines from erp.journal_lines j where j.journal_entry_id=inverse.id;
 effective:=erp.post_journal('RECEIPT_FIX_REVERSAL_EFFECTIVE',inverse.id,original.economic_date,
  'Benerin penerimaan: waktu ekonomi kejadian asal | '||p_reason,lines);
 insert into cp7_receipt_fix.journal_restatements values(inverse.id,original.id,src,neutral,effective,inverse.economic_date,original.economic_date,clock_timestamp());
end $$;

create function cp7_receipt_fix.restate_all(p_reason text)returns void
language plpgsql volatile security definer set search_path=''as $$
declare src uuid;j uuid;
begin
 select source_purchase_id into strict src from cp7_receipt_fix.context
  where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid();
 for j in select v.id from erp.journal_entries v join erp.journal_entries o on o.id=v.reversal_of_id
  where v.source_type='JOURNAL_REVERSAL'and v.status='POSTED'
   and(o.source_type in('MATERIAL_PURCHASE','MATERIAL_PURCHASE_GRNI_RECLASS')and o.source_id=src
    or o.source_type='SUPPLIER_PAYMENT'and exists(select 1 from erp.supplier_payments p where p.id=o.source_id and p.purchase_id=src))
   and not exists(select 1 from cp7_receipt_fix.journal_restatements r where r.inverse_journal_id=v.id)
  order by v.id loop
  perform cp7_receipt_fix.restate(j,p_reason);
 end loop;
end $$;

-- Net journal effect per economic date, account and dimension.
create function cp7_receipt_fix.journal_net(p_ids uuid[])returns jsonb
language sql volatile security definer set search_path=''as $$
 select coalesce(jsonb_agg(jsonb_build_object('d',d,'account_id',account_id,'customer_id',customer_id,'vendor_id',vendor_id,
  'contractor_id',contractor_id,'po_id',po_id,'product_id',product_id,'amount',amount::text)
  order by d,account_id::text,customer_id::text,vendor_id::text,contractor_id::text,po_id::text,product_id::text),'[]')
 from(select j.economic_date d,l.account_id,l.customer_id,l.vendor_id,l.contractor_id,l.po_id,l.product_id,sum(l.debit-l.credit)amount
  from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.id=any(p_ids)
  group by 1,2,3,4,5,6,7 having sum(l.debit-l.credit)<>0)x$$;

-- Native reversal of one posted supplier invoice of the receipt, its effect
-- restated to the invoice's own economic dates. The dry run re-posts the same
-- invoice at its own book date right after the Native reversal and is rolled
-- back; its journals are the exact opposite of the reversal (checked per
-- account and dimension, else refused) and carry the dates of the goods.
create function cp7_receipt_fix.reverse_invoice(p_invoice uuid,p_reason text,p_fix uuid)returns void
language plpgsql volatile security definer set search_path=''as $$
declare v erp.material_supplier_invoices%rowtype;before uuid[];mid uuid[];native_ids uuid[];dry uuid;mirror jsonb;native jsonb;d date;lines jsonb;j uuid;
begin
 perform 1 from cp7_receipt_fix.context where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid();
 if not found then raise exception using errcode='42501',message='CP7_RECEIPT_FIX_PRIVATE_CONTEXT_REQUIRED';end if;
 select*into strict v from erp.material_supplier_invoices where id=p_invoice for update;
 if v.status<>'POSTED'then raise exception 'CP7_RECEIPT_FIX_INVOICE_SET';end if;
 select coalesce(array_agg(id),'{}')into before from erp.journal_entries where created_at=statement_timestamp();
 begin
  perform erp.reverse_material_supplier_invoice(v.id,p_reason);
  select coalesce(array_agg(id),'{}')into mid from erp.journal_entries where created_at=statement_timestamp();
  dry:=(erp.save_material_supplier_invoice_draft_v2(jsonb_build_object('invoice_number',left(v.invoice_number,80)||' · CP7-DRY',
   'supplier_id',v.supplier_id,'invoice_date',v.invoice_date,'received_at',v.received_at,'due_date',v.due_date,'change_reason',p_reason,
   'lines',(select jsonb_agg(jsonb_build_object('purchase_item_id',l.purchase_item_id,'qty_invoiced',l.qty_invoiced,'unit_price',l.unit_price,
     'discount_amount',l.discount_amount)order by l.id)from erp.material_supplier_invoice_lines l where l.invoice_id=v.id)),gen_random_uuid(),null)
   ->>'supplier_invoice_id')::uuid;
  perform erp.post_material_supplier_invoice(dry);
  mirror:=cp7_receipt_fix.journal_net(array(select id from erp.journal_entries where created_at=statement_timestamp()and not(id=any(mid))));
  raise exception using errcode='P0001',message='CP7_RECEIPT_FIX_DRY_RUN_COMPLETE';
 exception when others then
  if sqlerrm<>'CP7_RECEIPT_FIX_DRY_RUN_COMPLETE'then raise;end if;
 end;
 if mirror is null then raise exception 'CP7_RECEIPT_FIX_INVOICE_DRY_RUN_MISSING';end if;
 perform erp.reverse_material_supplier_invoice(v.id,p_reason);
 native_ids:=array(select id from erp.journal_entries where created_at=statement_timestamp()and not(id=any(before))order by id);
 native:=cp7_receipt_fix.journal_net(native_ids);
 if exists(select 1 from(select x->>'account_id'a,x->>'customer_id'c,x->>'vendor_id'w,x->>'contractor_id'k,x->>'po_id'p,x->>'product_id'r,(x->>'amount')::numeric n
   from jsonb_array_elements(mirror||native)x)u group by a,c,w,k,p,r having sum(n)<>0)then
  raise exception 'CP7_RECEIPT_FIX_INVOICE_RESTATEMENT_MISMATCH %',v.invoice_number;end if;
 for d in select distinct(x->>'d')::date from jsonb_array_elements(mirror||native)x order by 1 loop
  select coalesce(jsonb_agg(jsonb_build_object('account_id',a,'customer_id',c,'vendor_id',w,'contractor_id',k,'po_id',p,'product_id',r,
    'debit',greatest(n,0),'credit',greatest(-n,0),'description','Pembalikan invoice '||v.invoice_number)order by a,c,w,k,p,r),'[]')into lines
  from(select(x->>'account_id')::uuid a,(x->>'customer_id')::uuid c,(x->>'vendor_id')::uuid w,(x->>'contractor_id')::uuid k,(x->>'po_id')::uuid p,
    (x->>'product_id')::uuid r,-sum((x->>'amount')::numeric)n
   from jsonb_array_elements(mirror||native)x where(x->>'d')::date=d group by 1,2,3,4,5,6 having sum((x->>'amount')::numeric)<>0)z;
  if jsonb_array_length(lines)=0 then continue;end if;
  j:=erp.post_journal('RECEIPT_FIX_INVOICE_REVERSAL_DATE',md5(p_fix::text||':'||v.id::text||':'||d::text)::uuid,d,
   'Benerin penerimaan: pembalikan invoice '||v.invoice_number||' pada tanggal ekonomi asal | '||p_reason,lines);
  insert into cp7_receipt_fix.invoice_restatements(journal_id,invoice_id,correction_id,economic_date,native_journal_ids)values(j,v.id,p_fix,d,native_ids);
 end loop;
end $$;

create function cp7_receipt_fix.command(p_payload jsonb,p_request uuid,p_expected text)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare a jsonb;old cp7_receipt_fix.requests%rowtype;h erp.material_purchase_headers%rowtype;root uuid;rev_no bigint;
 line jsonb;roll jsonb;item record;mat record;mv record;draft jsonb;result jsonb;replaced uuid;item_map jsonb:='{}';
 lineage jsonb:='[]';old_rolls uuid[];old_items uuid[];seen_rolls uuid[]:='{}';seen_items uuid[]:='{}';mat_ids uuid[];
 old_roll erp.material_rolls%rowtype;use jsonb;new_roll uuid;new_item uuid;line_no integer:=0;roll_no integer;
 paid jsonb;payment record;new_payment uuid;corrected_total numeric:=0;why text;fix_id uuid:=gen_random_uuid();
 rev_id uuid;tmp text;previous_doc jsonb;corrected_doc jsonb;pending jsonb:='[]';
 inv_ids uuid[];inv jsonb;il jsonb;old_new jsonb:='{}';inv_lines jsonb;new_inv uuid;invoiced jsonb:='{}';
 paid_total numeric:=0;excess numeric:=0;credits jsonb:='[]';credit jsonb;target erp.material_purchase_headers%rowtype;
 left_on_receipt numeric;part numeric;piece integer:=0;queue jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_receipt_fix.access_now();
 if jsonb_typeof(p_payload)is distinct from'object'or not p_payload?&array['purchase_id','review_token','change_reason','lines']
  or exists(select 1 from jsonb_object_keys(p_payload)k where k not in('purchase_id','review_token','change_reason','lines','invoices','credit_allocations','notes'))
  or p_payload?'credit_allocations'and(jsonb_typeof(p_payload->'credit_allocations')is distinct from'array'or jsonb_array_length(p_payload->'credit_allocations')>20)
  or jsonb_typeof(p_payload->'lines')is distinct from'array'or jsonb_array_length(p_payload->'lines')not between 1 and 100
  or p_payload?'invoices'and(jsonb_typeof(p_payload->'invoices')is distinct from'array'or jsonb_array_length(p_payload->'invoices')>20)
  or exists(select 1 from jsonb_each(p_payload)e where e.key not in('lines','invoices','credit_allocations')and jsonb_typeof(e.value)not in('string','null'))
  or nullif(btrim(p_payload->>'change_reason'),'')is null or length(p_payload->>'change_reason')>500
 then raise exception using errcode='22023',message='CP7_RECEIPT_FIX_FIELDS';end if;
 if p_request is null or p_expected is null or p_expected!~'^[1-9][0-9]{0,18}$'then raise exception 'CP7_RECEIPT_FIX_REQUEST_REQUIRED';end if;
 why:=btrim(p_payload->>'change_reason');
 insert into cp7_receipt_fix.requests values(auth.uid(),p_request,p_payload,p_expected,null)on conflict do nothing;
 select*into strict old from cp7_receipt_fix.requests where actor=auth.uid()and request_id=p_request for update;
 if old.payload is distinct from p_payload or old.expected_version is distinct from p_expected then raise exception 'CP7_RECEIPT_FIX_REQUEST_CHANGED';end if;
 if cp7_receipt_fix.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_RECEIPT_FIX_ACCESS_CHANGED';end if;
 if old.response is not null then return old.response;end if;

 -- Same lock order as Native receipt/recost writers: period, mat_ids, receipt.
 perform 1 from erp.accounting_period_control where singleton_id=1 for share;
 select array_agg(distinct mats.id order by mats.id)into mat_ids from(
  select i.material_id id from erp.material_purchase_items i where i.purchase_id=(p_payload->>'purchase_id')::uuid
  union select(l->>'material_id')::uuid from jsonb_array_elements(p_payload->'lines')l where l->>'material_id'~'^[0-9a-fA-F-]{36}$')mats;
 perform 1 from erp.materials where id=any(coalesce(mat_ids,'{}'))order by id for update;
 select*into h from erp.material_purchase_headers where id=(p_payload->>'purchase_id')::uuid for update;
 if h.id is null then raise exception 'CP7_RECEIPT_FIX_NOT_FOUND';end if;
 if h.status<>'POSTED'then raise exception 'CP7_RECEIPT_FIX_ACTIVE_POSTED_ONLY';end if;
 if h.row_version::text<>p_expected or cp7_receipt_fix.review_token(h.id)<>p_payload->>'review_token'then raise exception 'CP7_RECEIPT_FIX_REVIEW_CHANGED';end if;
 if exists(select 1 from cp7_receipt_fix.revisions where previous_purchase_id=h.id)then raise exception 'CP7_RECEIPT_FIX_SOURCE_SUPERSEDED';end if;
 if jsonb_array_length(cp7_receipt_fix.blockers(h.id))>0 then
  raise exception 'CP7_RECEIPT_FIX_DEPENDENCY %',(select string_agg(b->>'code',',')from jsonb_array_elements(cp7_receipt_fix.blockers(h.id))b);end if;
 select root_purchase_id into root from cp7_receipt_fix.revisions where replacement_purchase_id=h.id;
 root:=coalesce(root,h.id);
 select coalesce(max(v.revision),0)+1 into rev_no from cp7_receipt_fix.revisions v where v.root_purchase_id=root;
 select array_agg(id order by id)into old_items from erp.material_purchase_items where purchase_id=h.id;
 select array_agg(r2.id order by r2.id)into old_rolls from erp.material_rolls r2 join erp.material_purchase_items i on i.id=r2.purchase_item_id where i.purchase_id=h.id;
 select jsonb_build_object('purchase_number',h.purchase_number,'lines',coalesce(jsonb_agg(jsonb_build_object('item_id',i.id,'material_id',i.material_id,
  'qty',i.qty::text,'unit_price',i.unit_price::text,'price_state',i.price_state,'price_source',i.price_source,
  'rolls',(select coalesce(jsonb_agg(jsonb_build_object('roll_id',r3.id,'roll_number',r3.roll_number,'qty',r3.original_qty::text)order by r3.roll_number,r3.id),'[]')
   from erp.material_rolls r3 where r3.purchase_item_id=i.id))order by i.id),'[]'))into previous_doc
 from erp.material_purchase_items i where i.purchase_id=h.id;
 select coalesce(array_agg(v.id order by v.invoice_date,v.posted_at,v.id),'{}')into inv_ids from erp.material_supplier_invoices v
  where v.status='POSTED'and v.id in(select l.invoice_id from erp.material_supplier_invoice_lines l join erp.material_purchase_items i on i.id=l.purchase_item_id where i.purchase_id=h.id);
 previous_doc:=previous_doc||jsonb_build_object('invoices',(select coalesce(jsonb_agg(jsonb_build_object('invoice_id',v.id,'invoice_number',v.invoice_number,
  'invoice_date',v.invoice_date,'lines',(select jsonb_agg(jsonb_build_object('invoice_line_id',l.id,'purchase_item_id',l.purchase_item_id,'qty_invoiced',l.qty_invoiced::text,
   'unit_price',l.unit_price::text,'discount_amount',l.discount_amount::text)order by l.id)from erp.material_supplier_invoice_lines l where l.invoice_id=v.id))
  order by v.invoice_date,v.posted_at,v.id),'[]')from erp.material_supplier_invoices v where v.id=any(inv_ids)));

 -- Validate the corrected document against the physical history it replaces.
 for line in select value from jsonb_array_elements(p_payload->'lines')loop
  line_no:=line_no+1;
  if jsonb_typeof(line)is distinct from'object'or not line?&array['material_id','unit_price','price_state','price_source','rolls']
   or exists(select 1 from jsonb_object_keys(line)k where k not in('replaces_item_id','material_id','qty','unit_price','price_state','price_source','rolls','lot_number','notes'))
   or exists(select 1 from jsonb_each(line)e where e.key<>'rolls'and jsonb_typeof(e.value)not in('string','null'))
   or jsonb_typeof(line->'rolls')is distinct from'array'or jsonb_array_length(line->'rolls')>500
  then raise exception using errcode='22023',message='CP7_RECEIPT_FIX_FIELDS';end if;
  perform cp7_procurement.decimal(line->'unit_price',false);
  select*into mat from erp.materials where id=(line->>'material_id')::uuid;
  if mat.id is null then raise exception 'CP7_RECEIPT_FIX_MATERIAL_NOT_FOUND';end if;
  if nullif(line->>'replaces_item_id','')is not null then
   if not((line->>'replaces_item_id')::uuid=any(old_items))or(line->>'replaces_item_id')::uuid=any(seen_items)then raise exception 'CP7_RECEIPT_FIX_ITEM_LINEAGE';end if;
   seen_items:=seen_items||(line->>'replaces_item_id')::uuid;
  end if;
  if mat.material_type='FABRIC'then
   if jsonb_array_length(line->'rolls')=0 or line?'qty'then raise exception 'CP7_RECEIPT_FIX_FABRIC_ROLLS_REQUIRED';end if;
   for roll in select value from jsonb_array_elements(line->'rolls')loop
    if jsonb_typeof(roll)is distinct from'object'or not roll?&array['roll_number','qty']
     or exists(select 1 from jsonb_object_keys(roll)k where k not in('replaces_roll_id','roll_number','qty','notes'))
     or exists(select 1 from jsonb_each(roll)e where jsonb_typeof(e.value)not in('string','null'))
     or nullif(btrim(roll->>'roll_number'),'')is null or length(roll->>'roll_number')>80
    then raise exception using errcode='22023',message='CP7_RECEIPT_FIX_FIELDS';end if;
    perform cp7_procurement.decimal(roll->'qty',true);
    if upper(coalesce(line->>'price_state',''))='FINAL'then corrected_total:=corrected_total+(roll->>'qty')::numeric*(line->>'unit_price')::numeric;end if;
    if nullif(roll->>'replaces_roll_id','')is not null then
     if not((roll->>'replaces_roll_id')::uuid=any(coalesce(old_rolls,'{}')))or(roll->>'replaces_roll_id')::uuid=any(seen_rolls)then raise exception 'CP7_RECEIPT_FIX_ROLL_LINEAGE';end if;
     seen_rolls:=seen_rolls||(roll->>'replaces_roll_id')::uuid;
     select*into old_roll from erp.material_rolls where id=(roll->>'replaces_roll_id')::uuid for update;
     if old_roll.status='RETURNED_SUPPLIER'then raise exception 'CP7_RECEIPT_FIX_RETURN_ACTIVE';end if;
     use:=cp7_receipt_fix.roll_use(old_roll.id,h.location_id);
     if old_roll.material_id=mat.id then
      if btrim(roll->>'roll_number')<>old_roll.roll_number then raise exception 'CP7_RECEIPT_FIX_ROLL_NUMBER_IS_IDENTITY';end if;
      if (roll->>'qty')::numeric<(use->>'min_qty')::numeric then
       raise exception 'CP7_RECEIPT_FIX_ROLL_BELOW_USE roll % corrected % used %',old_roll.roll_number,roll->>'qty',use->>'min_qty';end if;
     else
      if (select material_type from erp.materials where id=old_roll.material_id)<>mat.material_type
       or (select unit_code from erp.materials where id=old_roll.material_id)<>mat.unit_code then raise exception 'CP7_RECEIPT_FIX_MATERIAL_KIND_CHANGED';end if;
      if not mat.is_active then raise exception 'CP7_RECEIPT_FIX_MATERIAL_INACTIVE';end if;
      if (use->>'movable')::boolean is distinct from true then raise exception 'CP7_RECEIPT_FIX_ROLL_USE_UNSUPPORTED roll %',old_roll.roll_number;end if;
      if (roll->>'qty')::numeric<(use->>'min_qty')::numeric then
       raise exception 'CP7_RECEIPT_FIX_ROLL_BELOW_USE roll % corrected % used %',old_roll.roll_number,roll->>'qty',use->>'min_qty';end if;
      if exists(select 1 from erp.material_rolls where material_id=mat.id and roll_number=btrim(roll->>'roll_number'))then
       raise exception 'CP7_RECEIPT_FIX_ROLL_NUMBER_TAKEN %',btrim(roll->>'roll_number');end if;
     end if;
    end if;
   end loop;
  else
   if jsonb_array_length(line->'rolls')<>0 or not line?'qty'then raise exception 'CP7_RECEIPT_FIX_NON_ROLL_QTY_REQUIRED';end if;
   perform cp7_procurement.decimal(line->'qty',true);
   if upper(coalesce(line->>'price_state',''))='FINAL'then corrected_total:=corrected_total+(line->>'qty')::numeric*(line->>'unit_price')::numeric;end if;
  end if;
 end loop;
 -- Rolls the corrected document no longer contains must never have been used.
 for old_roll in select*from erp.material_rolls where id=any(coalesce(old_rolls,'{}'))and not(id=any(seen_rolls))order by id loop
  if (cp7_receipt_fix.roll_use(old_roll.id,h.location_id)->>'min_qty')::numeric>0
   or exists(select 1 from erp.material_stock_movements mm where mm.roll_id=old_roll.id and mm.reversal_of_id is null
    and mm.source_type not in('MATERIAL_PURCHASE_ROLL','MATERIAL_PURCHASE_ITEM')
    and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=mm.id))then
   raise exception 'CP7_RECEIPT_FIX_REMOVED_ROLL_USED roll %',old_roll.roll_number;end if;
 end loop;
 -- Every posted supplier invoice of the receipt is corrected with it: each of
 -- its lines is restated on the corrected receipt line that replaces its line.
 if cardinality(inv_ids)>0 and not p_payload?'invoices'then raise exception 'CP7_RECEIPT_FIX_INVOICE_DECISION_REQUIRED';end if;
 if(select coalesce(array_agg(x order by x),'{}')from(select(z->>'replaces_invoice_id')::uuid x from jsonb_array_elements(coalesce(p_payload->'invoices','[]'))z)q)
   is distinct from(select coalesce(array_agg(x order by x),'{}')from unnest(inv_ids)x)
  or(select count(distinct z->>'replaces_invoice_id')from jsonb_array_elements(coalesce(p_payload->'invoices','[]'))z)<>cardinality(inv_ids)
 then raise exception 'CP7_RECEIPT_FIX_INVOICE_SET';end if;
 for inv in select value from jsonb_array_elements(coalesce(p_payload->'invoices','[]'))loop
  if jsonb_typeof(inv)is distinct from'object'or not inv?&array['replaces_invoice_id','lines']
   or exists(select 1 from jsonb_object_keys(inv)k where k not in('replaces_invoice_id','lines','notes'))
   or jsonb_typeof(inv->'lines')is distinct from'array'or jsonb_array_length(inv->'lines')not between 1 and 100
   or exists(select 1 from jsonb_each(inv)e where e.key<>'lines'and jsonb_typeof(e.value)not in('string','null'))
  then raise exception using errcode='22023',message='CP7_RECEIPT_FIX_FIELDS';end if;
  if(select coalesce(array_agg(x order by x),'{}')from(select(z->>'replaces_invoice_line_id')::uuid x from jsonb_array_elements(inv->'lines')z)q)
    is distinct from(select array_agg(l.id order by l.id)from erp.material_supplier_invoice_lines l where l.invoice_id=(inv->>'replaces_invoice_id')::uuid)
  then raise exception 'CP7_RECEIPT_FIX_INVOICE_LINE_SET';end if;
  for il in select value from jsonb_array_elements(inv->'lines')loop
   if jsonb_typeof(il)is distinct from'object'or not il?&array['replaces_invoice_line_id','qty_invoiced','unit_price']
    or exists(select 1 from jsonb_object_keys(il)k where k not in('replaces_invoice_line_id','qty_invoiced','unit_price','discount_amount','notes'))
    or exists(select 1 from jsonb_each(il)e where jsonb_typeof(e.value)not in('string','null'))
   then raise exception using errcode='22023',message='CP7_RECEIPT_FIX_FIELDS';end if;
   perform cp7_procurement.decimal(il->'qty_invoiced',true);perform cp7_procurement.decimal(il->'unit_price',false);
   if nullif(il->>'discount_amount','')is not null then perform cp7_procurement.decimal(il->'discount_amount',false);end if;
   if coalesce(nullif(il->>'discount_amount','')::numeric,0)>(il->>'qty_invoiced')::numeric*(il->>'unit_price')::numeric then
    raise exception 'CP7_RECEIPT_FIX_INVOICE_DISCOUNT';end if;
   select l.purchase_item_id::text into tmp from erp.material_supplier_invoice_lines l where l.id=(il->>'replaces_invoice_line_id')::uuid;
   select value into line from jsonb_array_elements(p_payload->'lines')where value->>'replaces_item_id'=tmp;
   if line is null then raise exception 'CP7_RECEIPT_FIX_INVOICE_LINE_ORPHAN';end if;
   if upper(coalesce(line->>'price_state',''))='FINAL'then raise exception 'CP7_RECEIPT_FIX_INVOICED_LINE_ESTIMATE_REQUIRED';end if;
   invoiced:=jsonb_set(invoiced,array[tmp],to_jsonb(coalesce((invoiced->>tmp)::numeric,0)+(il->>'qty_invoiced')::numeric));
   corrected_total:=corrected_total+(il->>'qty_invoiced')::numeric*(il->>'unit_price')::numeric-coalesce(nullif(il->>'discount_amount','')::numeric,0);
  end loop;
 end loop;
 for line in select value from jsonb_array_elements(p_payload->'lines')where value->>'replaces_item_id'in(select jsonb_object_keys(invoiced))loop
  if(invoiced->>(line->>'replaces_item_id'))::numeric>(case when jsonb_array_length(line->'rolls')=0 then(line->>'qty')::numeric
    else(select sum((z->>'qty')::numeric)from jsonb_array_elements(line->'rolls')z)end)then
   raise exception 'CP7_RECEIPT_FIX_INVOICE_EXCEEDS_RECEIPT';end if;
 end loop;
 select coalesce(jsonb_agg(to_jsonb(p)order by p.payment_date,p.id),'[]')into paid from erp.supplier_payments p where p.purchase_id=h.id and p.status='POSTED';
 select coalesce(sum((v->>'amount')::numeric),0)into paid_total from jsonb_array_elements(paid)v;
 excess:=greatest(paid_total-round(corrected_total,2),0);
 -- Paid more than the corrected total: the excess becomes supplier credit cut
 -- from other receipts (nota) of the same supplier, never a refund invented here.
 for credit in select value from jsonb_array_elements(coalesce(p_payload->'credit_allocations','[]'))loop
  if jsonb_typeof(credit)is distinct from'object'or not credit?&array['purchase_id','amount']
   or exists(select 1 from jsonb_object_keys(credit)k where k not in('purchase_id','amount'))
   or exists(select 1 from jsonb_each(credit)e where jsonb_typeof(e.value)<>'string')
   or credit->>'purchase_id'!~'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
  then raise exception using errcode='22023',message='CP7_RECEIPT_FIX_FIELDS';end if;
  perform cp7_procurement.decimal(credit->'amount',true);
  if (credit->>'amount')::numeric<>round((credit->>'amount')::numeric,2)then raise exception 'CP7_RECEIPT_FIX_CREDIT_CENTS';end if;
  if (credit->>'purchase_id')::uuid=h.id or(credit->>'purchase_id')in(select x->>'purchase_id'from jsonb_array_elements(credits)x)then
   raise exception 'CP7_RECEIPT_FIX_CREDIT_TARGET_INVALID';end if;
  credits:=credits||credit;
 end loop;
 if excess>0 and jsonb_array_length(credits)=0 then
  raise exception 'CP7_RECEIPT_FIX_CREDIT_ALLOCATION_REQUIRED paid % corrected % credit %',paid_total,round(corrected_total,2),excess;end if;
 if (select coalesce(sum((x->>'amount')::numeric),0)from jsonb_array_elements(credits)x)<>excess then
  raise exception 'CP7_RECEIPT_FIX_CREDIT_ALLOCATION_MISMATCH credit % allocated %',excess,(select coalesce(sum((x->>'amount')::numeric),0)from jsonb_array_elements(credits)x);end if;
 for target in select t.*from erp.material_purchase_headers t where t.id in(select(x->>'purchase_id')::uuid from jsonb_array_elements(credits)x)order by t.id for update loop
  if target.status<>'POSTED'or target.supplier_id is distinct from h.supplier_id then raise exception 'CP7_RECEIPT_FIX_CREDIT_TARGET_INVALID';end if;
  if round(erp.material_purchase_payable_total(target.id),2)-coalesce((select sum(amount)from erp.supplier_payments where purchase_id=target.id and status='POSTED'),0)
   <(select(x->>'amount')::numeric from jsonb_array_elements(credits)x where(x->>'purchase_id')::uuid=target.id)then
   raise exception 'CP7_RECEIPT_FIX_CREDIT_TARGET_EXCEEDS_REMAINING %',target.purchase_number;end if;
 end loop;
 if (select count(*)from erp.material_purchase_headers t where t.id in(select(x->>'purchase_id')::uuid from jsonb_array_elements(credits)x))<>jsonb_array_length(credits)then
  raise exception 'CP7_RECEIPT_FIX_CREDIT_TARGET_INVALID';end if;

 -- Execute. Effects run under the receipt's own business date as economic
 -- date (accepted invoice-recost dating rules for revaluation/HPP/GL).
 insert into cp7_receipt_fix.context values(pg_backend_pid(),txid_current(),auth.uid(),h.id);
 insert into erp.invoice_recost_execution_context(transaction_id,invoice_date,source_id)values(txid_current(),erp._cp3_business_date(h.physical_at),h.id);
 perform set_config('app.change_reason',why,true);
 perform cp7_receipt_fix.admit('POST');
 for payment in select*from jsonb_to_recordset(paid)as p(id uuid)loop
  perform erp.reverse_supplier_payment(payment.id,'Benerin penerimaan: '||why);
 end loop;
 -- Supplier invoices: Native reversal, restated to their own economic dates.
 -- The Native writer owns its recost date context for this step.
 if cardinality(inv_ids)>0 then
  delete from erp.invoice_recost_execution_context where transaction_id=txid_current();
  foreach new_inv in array inv_ids loop
   perform cp7_receipt_fix.reverse_invoice(new_inv,'Benerin penerimaan: '||why,fix_id);
  end loop;
  insert into erp.invoice_recost_execution_context(transaction_id,invoice_date,source_id)values(txid_current(),erp._cp3_business_date(h.physical_at),h.id);
 end if;
 -- Source-time inverse of every receipt stock movement (Native writer), with
 -- the accepted replacement admission for a temporarily used roll.
 perform set_config('erp.allow_source_replacement_negative','on',true);
 perform erp._stage_reverse_material_purchase_stock_at_source_time(h.id,'Benerin penerimaan: '||why);
 perform set_config('erp.allow_source_replacement_negative','off',true);
 update erp.material_purchase_headers set status='REVERSED',payment_status='UNPAID',updated_at=statement_timestamp()where id=h.id;
 -- Cutting use of a wrong-material roll, collected before the replacement.
 for line in select value from jsonb_array_elements(p_payload->'lines')loop
  for roll in select value from jsonb_array_elements(line->'rolls')loop
   if nullif(roll->>'replaces_roll_id','')is null then continue;end if;
   select*into old_roll from erp.material_rolls where id=(roll->>'replaces_roll_id')::uuid;
   if old_roll.material_id=(line->>'material_id')::uuid then continue;end if;
   for mv in select mm.*from erp.material_stock_movements mm where mm.roll_id=old_roll.id and mm.reversal_of_id is null
    and mm.source_type in('CUTTING_GROUP','CUTTING_GROUP_RETURN')
    and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=mm.id)
    order by mm.physical_at,mm.system_created_at,mm.id for update loop
    pending:=pending||jsonb_build_object('movement',mv.id,'old_roll',old_roll.id,'old_material',old_roll.material_id,
     'roll_number',btrim(roll->>'roll_number'),'material',line->>'material_id');
   end loop;
  end loop;
 end loop;

 -- Replacement document through the accepted Native draft writer. Rolls of the
 -- same material are re-attached below; their placeholder draft rows exist only
 -- inside this transaction and never receive stock.
 draft:=jsonb_build_object('purchase_number',left((select purchase_number from erp.material_purchase_headers where id=root),40)||' · R'||rev_no::text||'-'||left(p_request::text,8),
  'supplier_id',h.supplier_id,'location_id',h.location_id,'physical_at',h.physical_at,
  'notes',coalesce(nullif(p_payload->>'notes',''),h.notes),'supplier_invoice_number',h.supplier_invoice_number,'due_date',h.due_date,
  'change_reason','Benerin penerimaan '||h.purchase_number||': '||why,
  'lines',(select jsonb_agg(jsonb_build_object('material_id',l->>'material_id','unit_price',l->>'unit_price','price_state',l->>'price_state',
    'price_source',l->>'price_source','lot_number',l->>'lot_number','notes',l->>'notes')
   ||case when jsonb_array_length(l->'rolls')=0 then jsonb_build_object('qty',l->>'qty')
     else jsonb_build_object('qty',(select sum((z->>'qty')::numeric)::text from jsonb_array_elements(l->'rolls')z),
      'rolls',(select jsonb_agg(jsonb_build_object('roll_number',case when nullif(z->>'replaces_roll_id','')is not null
        and(select material_id from erp.material_rolls where id=(z->>'replaces_roll_id')::uuid)=(l->>'material_id')::uuid
       then '__CP7FIX-'||(z->>'replaces_roll_id')else btrim(z->>'roll_number')end,'qty',z->>'qty','notes',z->>'notes')order by o2)
       from jsonb_array_elements(l->'rolls')with ordinality q(z,o2)))end order by o)
   from jsonb_array_elements(p_payload->'lines')with ordinality t(l,o)));
 perform cp7_receipt_fix.admit('SAVE_DRAFT');
 result:=erp.save_material_purchase_draft_v2(draft,md5(auth.uid()::text||':RECEIPT_FIX:'||p_request::text)::uuid,null);
 replaced:=(result->>'purchase_id')::uuid;
 -- Map draft lines to payload lines by order (the writer keeps payload order
 -- only through its returned ids; resolve deterministically by material/qty).
 line_no:=0;
 for line in select value from jsonb_array_elements(p_payload->'lines')loop
  line_no:=line_no+1;
  select i.id into new_item from erp.material_purchase_items i where i.purchase_id=replaced and i.material_id=(line->>'material_id')::uuid
   and not(i.id::text=any(select jsonb_object_keys(item_map)))
   and i.unit_price=(line->>'unit_price')::numeric
   and i.qty=case when jsonb_array_length(line->'rolls')=0 then(line->>'qty')::numeric else(select sum((z->>'qty')::numeric)from jsonb_array_elements(line->'rolls')z)end
   order by(select count(*)from erp.material_rolls rr where rr.purchase_item_id=i.id and rr.roll_number=any(
    select case when nullif(z->>'replaces_roll_id','')is not null then '__CP7FIX-'||(z->>'replaces_roll_id')else btrim(z->>'roll_number')end
    from jsonb_array_elements(line->'rolls')z))desc,i.id limit 1;
  if new_item is null then raise exception 'CP7_RECEIPT_FIX_DRAFT_LINE_MAPPING';end if;
  item_map:=item_map||jsonb_build_object(new_item::text,line_no);
  if nullif(line->>'replaces_item_id','')is not null then old_new:=old_new||jsonb_build_object(line->>'replaces_item_id',new_item);end if;
  for roll in select value from jsonb_array_elements(line->'rolls')loop
   if nullif(roll->>'replaces_roll_id','')is not null then
    select*into old_roll from erp.material_rolls where id=(roll->>'replaces_roll_id')::uuid;
    if old_roll.material_id=(line->>'material_id')::uuid then
     delete from erp.material_rolls where purchase_item_id=new_item and roll_number='__CP7FIX-'||old_roll.id::text;
     if not found then raise exception 'CP7_RECEIPT_FIX_DRAFT_ROLL_MAPPING';end if;
     update erp.material_rolls set purchase_item_id=new_item,original_qty=(roll->>'qty')::numeric,
      notes=coalesce(nullif(roll->>'notes',''),notes),updated_at=statement_timestamp()where id=old_roll.id;
     lineage:=lineage||jsonb_build_object('kind','REPARENTED','old_roll_id',old_roll.id,'new_roll_id',old_roll.id,'old_material_id',old_roll.material_id,
      'new_material_id',old_roll.material_id,'old_purchase_item_id',old_roll.purchase_item_id,'new_purchase_item_id',new_item,
      'old_qty',old_roll.original_qty,'new_qty',(roll->>'qty')::numeric,'roll_number',old_roll.roll_number);
    else
     select id into new_roll from erp.material_rolls where purchase_item_id=new_item and roll_number=btrim(roll->>'roll_number');
     lineage:=lineage||jsonb_build_object('kind','MATERIAL_MOVED','old_roll_id',old_roll.id,'new_roll_id',new_roll,'old_material_id',old_roll.material_id,
      'new_material_id',(line->>'material_id')::uuid,'old_purchase_item_id',old_roll.purchase_item_id,'new_purchase_item_id',new_item,
      'old_qty',old_roll.original_qty,'new_qty',(roll->>'qty')::numeric,'roll_number',btrim(roll->>'roll_number'));
    end if;
   else
    select id into new_roll from erp.material_rolls where purchase_item_id=new_item and roll_number=btrim(roll->>'roll_number');
    lineage:=lineage||jsonb_build_object('kind','ADDED','new_roll_id',new_roll,'new_material_id',(line->>'material_id')::uuid,
     'new_purchase_item_id',new_item,'new_qty',(roll->>'qty')::numeric,'roll_number',btrim(roll->>'roll_number'));
   end if;
  end loop;
 end loop;
 for old_roll in select*from erp.material_rolls where id=any(coalesce(old_rolls,'{}'))and not(id=any(seen_rolls))order by id loop
  lineage:=lineage||jsonb_build_object('kind','REMOVED','old_roll_id',old_roll.id,'old_material_id',old_roll.material_id,
   'old_purchase_item_id',old_roll.purchase_item_id,'old_qty',old_roll.original_qty,'roll_number',old_roll.roll_number);
 end loop;
 -- Native posting of the replacement at the original physical time.
 perform cp7_receipt_fix.admit('POST');
 perform erp.post_material_purchase(replaced);
 -- The same cutting use, at its own time, now reads the right-material roll.
 for mv in select*from jsonb_to_recordset(pending)as p(movement uuid,old_roll uuid,old_material uuid,roll_number text,material uuid)loop
  select r4.id into new_roll from erp.material_rolls r4 join erp.material_purchase_items i on i.id=r4.purchase_item_id
   where i.purchase_id=replaced and r4.material_id=mv.material and r4.roll_number=mv.roll_number;
  if new_roll is null then raise exception 'CP7_RECEIPT_FIX_DRAFT_ROLL_MAPPING';end if;
  update erp.material_stock_movements set material_id=mv.material,roll_id=new_roll where id=mv.movement
   returning qty_signed,physical_at,source_type,source_id into mat;
  insert into cp7_receipt_fix.movement_lineage(movement_id,correction_id,old_material_id,old_roll_id,new_material_id,new_roll_id,qty_signed,physical_at,source_type,source_id)
  values(mv.movement,fix_id,mv.old_material,mv.old_roll,mv.material,new_roll,mat.qty_signed,mat.physical_at,mat.source_type,mat.source_id);
  if mat.source_type='CUTTING_GROUP'then
   update erp.cutting_group_rolls set roll_id=new_roll where cutting_group_id=mat.source_id and roll_id=mv.old_roll;
  end if;
 end loop;
 -- Group the source-time receipt inverse and the corrected receipt row of the
 -- same physical roll/line under the original card row (root of all revisions).
 insert into cp7_receipt_fix.ledger_links(member_id,origin_id,correction_id)
 select rv.id,coalesce(l.origin_id,o.id),fix_id from erp.material_stock_movements rv
  join erp.material_stock_movements o on o.id=rv.reversal_of_id
  left join cp7_receipt_fix.ledger_links l on l.member_id=o.id
 where rv.source_type='MATERIAL_PURCHASE_REVERSAL'and o.movement_type='PURCHASE'
  and(o.source_type='MATERIAL_PURCHASE_ROLL'and o.source_id=any(coalesce(old_rolls,'{}'))
   or o.source_type='MATERIAL_PURCHASE_ITEM'and o.source_id=any(coalesce(old_items,'{}')))
  and not exists(select 1 from cp7_receipt_fix.ledger_links z where z.member_id=rv.id);
 insert into cp7_receipt_fix.ledger_links(member_id,origin_id,correction_id)
 select p.id,(select coalesce(l.origin_id,o.id)from erp.material_stock_movements o left join cp7_receipt_fix.ledger_links l on l.member_id=o.id
   where o.movement_type='PURCHASE'and o.source_type='MATERIAL_PURCHASE_ROLL'and o.source_id=p.source_id and o.id<>p.id
   order by o.system_created_at,o.id limit 1),fix_id
 from erp.material_stock_movements p join erp.material_rolls r6 on r6.id=p.source_id
  join erp.material_purchase_items i6 on i6.id=r6.purchase_item_id
 where p.movement_type='PURCHASE'and p.source_type='MATERIAL_PURCHASE_ROLL'and i6.purchase_id=replaced
  and r6.id=any(seen_rolls)and r6.id=any(coalesce(old_rolls,'{}'))
  and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=p.id)
  and not exists(select 1 from cp7_receipt_fix.ledger_links z where z.member_id=p.id);
 for line in select value from jsonb_array_elements(p_payload->'lines')loop
  if nullif(line->>'replaces_item_id','')is null or jsonb_array_length(line->'rolls')>0
   or(select material_id from erp.material_purchase_items where id=(line->>'replaces_item_id')::uuid)<>(line->>'material_id')::uuid then continue;end if;
  insert into cp7_receipt_fix.ledger_links(member_id,origin_id,correction_id)
  select p.id,(select coalesce(l.origin_id,o.id)from erp.material_stock_movements o left join cp7_receipt_fix.ledger_links l on l.member_id=o.id
    where o.movement_type='PURCHASE'and o.source_type='MATERIAL_PURCHASE_ITEM'and o.source_id=(line->>'replaces_item_id')::uuid limit 1),fix_id
  from erp.material_stock_movements p where p.movement_type='PURCHASE'and p.source_type='MATERIAL_PURCHASE_ITEM'
   and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=p.id)
   and p.source_id=(select k::uuid from jsonb_each_text(item_map)e(k,v)where e.v::integer=(select o3 from jsonb_array_elements(p_payload->'lines')with ordinality q3(l3,o3)where l3=line limit 1)limit 1);
 end loop;
 -- Chronological recost of every affected material from the receipt time. A
 -- material whose cutting use moved to the right material is rebuilt first and
 -- completely, so its derived history releases the moved rows before the right
 -- material replays them.
 for mat in select x.id from erp.materials x where x.id=any(mat_ids)
  order by(x.id in(select(z->>'old_material')::uuid from jsonb_array_elements(pending)z))desc,x.id loop
  if mat.id in(select(z->>'old_material')::uuid from jsonb_array_elements(pending)z)then
   perform erp._recalculate_material_cost_core(mat.id,h.physical_at,false);
  else
   perform erp.recalculate_material_cost(mat.id,h.physical_at);
  end if;
 end loop;
 delete from erp.invoice_recost_execution_context where transaction_id=txid_current();
 -- The original purchase journal inverse, restated to its original economic date.
 select id into rev_id from erp.journal_entries where source_type='MATERIAL_PURCHASE'and source_id=h.id and status='POSTED'order by posting_at desc,id desc limit 1;
 if rev_id is not null then perform erp.reverse_journal(rev_id,'Benerin penerimaan: '||why);end if;
 perform cp7_receipt_fix.restate_all(why);
 -- Corrected supplier invoices, posted by the Native writer at their own
 -- invoice/book date on the corrected receipt lines.
 for inv in select value from jsonb_array_elements(coalesce(p_payload->'invoices','[]'))
  order by(select array_position(inv_ids,(value->>'replaces_invoice_id')::uuid))loop
  select coalesce(jsonb_agg(jsonb_build_object('purchase_item_id',old_new->>l.purchase_item_id::text,'qty_invoiced',il2->>'qty_invoiced',
    'unit_price',il2->>'unit_price','discount_amount',coalesce(nullif(il2->>'discount_amount',''),'0'),'notes',coalesce(nullif(il2->>'notes',''),l.notes))order by l.id),'[]')
  into inv_lines from jsonb_array_elements(inv->'lines')il2 join erp.material_supplier_invoice_lines l on l.id=(il2->>'replaces_invoice_line_id')::uuid;
  select jsonb_build_object('invoice_number',regexp_replace(v.invoice_number,' · R[0-9]+$','')||' · R'||rev_no::text,'supplier_id',v.supplier_id,
    'invoice_date',v.invoice_date,'received_at',v.received_at,'due_date',v.due_date,'notes',coalesce(nullif(inv->>'notes',''),v.notes),
    'change_reason','Benerin penerimaan '||h.purchase_number||': '||why,'lines',inv_lines)into draft
  from erp.material_supplier_invoices v where v.id=(inv->>'replaces_invoice_id')::uuid;
  result:=erp.save_material_supplier_invoice_draft_v2(draft,md5(auth.uid()::text||':RECEIPT_FIX_INVOICE:'||p_request::text||':'||(inv->>'replaces_invoice_id'))::uuid,null);
  new_inv:=(result->>'supplier_invoice_id')::uuid;
  perform erp.post_material_supplier_invoice_v2(new_inv,md5(auth.uid()::text||':RECEIPT_FIX_INVOICE_POST:'||p_request::text||':'||(inv->>'replaces_invoice_id'))::uuid,
   (result->>'row_version')::bigint,'Benerin penerimaan: '||why);
  insert into cp7_receipt_fix.invoice_replays(previous_invoice_id,replacement_invoice_id,correction_id,previous_lines,corrected_lines)
  values((inv->>'replaces_invoice_id')::uuid,new_inv,fix_id,
   (select jsonb_agg(jsonb_build_object('invoice_line_id',l.id,'purchase_item_id',l.purchase_item_id,'qty_invoiced',l.qty_invoiced::text,'unit_price',l.unit_price::text,
     'discount_amount',l.discount_amount::text)order by l.id)from erp.material_supplier_invoice_lines l where l.invoice_id=(inv->>'replaces_invoice_id')::uuid),
   (select jsonb_agg(jsonb_build_object('invoice_line_id',l.id,'purchase_item_id',l.purchase_item_id,'qty_invoiced',l.qty_invoiced::text,'unit_price',l.unit_price::text,
     'discount_amount',l.discount_amount::text)order by l.id)from erp.material_supplier_invoice_lines l where l.invoice_id=new_inv));
 end loop;
 left_on_receipt:=round(erp.material_purchase_payable_total(replaced),2);
 if greatest(paid_total-left_on_receipt,0)<>excess then
  raise exception 'CP7_RECEIPT_FIX_CREDIT_ALLOCATION_MISMATCH credit % allocated %',greatest(paid_total-left_on_receipt,0),excess;end if;
 -- Replay every real supplier payment at its own date, cash account and
 -- amount: on the corrected receipt up to its payable, the rest as credit on
 -- the chosen receipts of the same supplier.
 queue:=credits;
 for payment in select*from jsonb_to_recordset(paid)as p(id uuid,payment_number text,payment_date timestamptz,amount numeric,cash_account_id uuid,
  payment_method text,reference_number text,notes text)loop
  part:=least(payment.amount,left_on_receipt);
  if part>0 then
   piece:=piece+1;
   insert into erp.supplier_payments(purchase_id,payment_number,payment_date,amount,cash_account_id,payment_method,reference_number,notes,status,created_by)
   values(replaced,left(payment.payment_number,36)||' · K'||piece::text||'-'||left(p_request::text,8),payment.payment_date,part,payment.cash_account_id,
    payment.payment_method,payment.reference_number,payment.notes,'DRAFT',erp.current_app_user_id())returning id into new_payment;
   perform erp.post_supplier_payment(new_payment);
   insert into cp7_receipt_fix.payment_replays(replacement_payment_id,previous_payment_id,correction_id,target_purchase_id,kind,amount)
   values(new_payment,payment.id,fix_id,replaced,'CORRECTED_RECEIPT',part);
   left_on_receipt:=left_on_receipt-part;
  end if;
  part:=payment.amount-part;
  while part>0 loop
   credit:=queue->0;
   if credit is null then raise exception 'CP7_RECEIPT_FIX_CREDIT_ALLOCATION_MISMATCH';end if;
   piece:=piece+1;
   insert into erp.supplier_payments(purchase_id,payment_number,payment_date,amount,cash_account_id,payment_method,reference_number,notes,status,created_by)
   values((credit->>'purchase_id')::uuid,left(payment.payment_number,36)||' · K'||piece::text||'-'||left(p_request::text,8),payment.payment_date,
    least(part,(credit->>'amount')::numeric),payment.cash_account_id,payment.payment_method,payment.reference_number,
    left('Retur bayangan dari pembetulan penerimaan '||h.purchase_number||': barang tidak pernah diterima; kelebihan bayar dipotong ke nota ini. '||why,1000),
    'DRAFT',erp.current_app_user_id())returning id into new_payment;
   perform erp.post_supplier_payment(new_payment);
   insert into cp7_receipt_fix.payment_replays(replacement_payment_id,previous_payment_id,correction_id,target_purchase_id,kind,amount)
   values(new_payment,payment.id,fix_id,(credit->>'purchase_id')::uuid,'CREDIT_TO_OTHER_RECEIPT',least(part,(credit->>'amount')::numeric));
   if part>=(credit->>'amount')::numeric then part:=part-(credit->>'amount')::numeric;queue:=queue-0;
   else queue:=jsonb_set(queue,'{0,amount}',to_jsonb(((credit->>'amount')::numeric-part)::text));part:=0;end if;
  end loop;
 end loop;
 if jsonb_array_length(queue)<>0 then raise exception 'CP7_RECEIPT_FIX_CREDIT_ALLOCATION_MISMATCH';end if;
 perform cp7_receipt_fix.admit(null);
 delete from erp.invoice_recost_execution_context where transaction_id=txid_current();
 if cp7_receipt_fix.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_RECEIPT_FIX_ACCESS_CHANGED';end if;
 select jsonb_build_object('purchase_number',(select purchase_number from erp.material_purchase_headers where id=replaced),'lines',coalesce(jsonb_agg(jsonb_build_object('item_id',i.id,'material_id',i.material_id,
  'qty',i.qty::text,'unit_price',i.unit_price::text,'price_state',i.price_state,'price_source',i.price_source,
  'rolls',(select coalesce(jsonb_agg(jsonb_build_object('roll_id',r5.id,'roll_number',r5.roll_number,'qty',r5.original_qty::text)order by r5.roll_number,r5.id),'[]')
   from erp.material_rolls r5 where r5.purchase_item_id=i.id))order by i.id),'[]'))into corrected_doc
 from erp.material_purchase_items i where i.purchase_id=replaced;
 corrected_doc:=corrected_doc||jsonb_build_object('invoices',(select coalesce(jsonb_agg(jsonb_build_object('invoice_id',v.id,'invoice_number',v.invoice_number,
  'invoice_date',v.invoice_date,'replaces_invoice_id',x.previous_invoice_id,'lines',x.corrected_lines)order by v.invoice_date,v.posted_at,v.id),'[]')
  from cp7_receipt_fix.invoice_replays x join erp.material_supplier_invoices v on v.id=x.replacement_invoice_id where x.correction_id=fix_id));
 insert into cp7_receipt_fix.revisions(id,root_purchase_id,previous_purchase_id,replacement_purchase_id,revision,actor,request_id,reason,effective_at,previous_document,corrected_document)
 values(fix_id,root,h.id,replaced,rev_no,auth.uid(),p_request,why,h.physical_at,previous_doc,corrected_doc);
 insert into cp7_receipt_fix.roll_lineage(correction_id,kind,old_roll_id,new_roll_id,old_material_id,new_material_id,old_purchase_item_id,new_purchase_item_id,old_qty,new_qty,roll_number)
 select fix_id,x.kind,x.old_roll_id,x.new_roll_id,x.old_material_id,x.new_material_id,x.old_purchase_item_id,x.new_purchase_item_id,x.old_qty,x.new_qty,x.roll_number
 from jsonb_to_recordset(lineage)as x(kind text,old_roll_id uuid,new_roll_id uuid,old_material_id uuid,new_material_id uuid,old_purchase_item_id uuid,
  new_purchase_item_id uuid,old_qty numeric,new_qty numeric,roll_number text);
 insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
 values('material_purchase_headers',h.id,'REVERSE',jsonb_build_object('receipt_correction_id',fix_id,'replacement_purchase_id',replaced),erp.current_app_user_id(),why);
 delete from cp7_receipt_fix.context where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 result:=jsonb_build_object('contract_version','cp7.receipt-correction-outcome.v1','kind','COMMITTED_OUTCOME','action','CORRECT',
  'request_id',p_request,'root_purchase_id',root,'previous_purchase_id',h.id,'purchase_id',replaced,
  'revision_id',fix_id,'revision',rev_no::text,'effective_at',h.physical_at,
  'row_version',(select row_version::text from erp.material_purchase_headers where id=replaced));
 update cp7_receipt_fix.requests set response=result where actor=auth.uid()and request_id=p_request;
 return result;
end $$;

do $own$
declare f text;
begin
 foreach f in array array['immutable()','access_now()','admit(text)','review_token(uuid)','roll_use(uuid,uuid)','blockers(uuid)','workspace(uuid)',
  'restate(uuid,text)','restate_all(text)','journal_net(uuid[])','reverse_invoice(uuid,text,uuid)','command(jsonb,uuid,text)']loop
  execute 'alter function cp7_receipt_fix.'||f||' owner to postgres';
 end loop;
end $own$;
-- Exact private composition: postgres owns this command's metadata and writes
-- the procurement admission row only for its own transaction.
grant usage on schema cp7_procurement to postgres;
grant execute on function cp7_procurement.decimal(jsonb,boolean)to postgres;
grant select,insert,delete on cp7_procurement.execution_context to postgres;
revoke all on all functions in schema cp7_receipt_fix from public,anon,authenticated,service_role,cp7_capture,cp7_procure_read,cp7_procure_write;
grant usage on schema cp7_receipt_fix to cp7_procure_write;
grant execute on function cp7_receipt_fix.workspace(uuid),cp7_receipt_fix.command(jsonb,uuid,text)to cp7_procure_write;
create function public.erp_cp7_get_receipt_correction_v1(p_purchase uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_receipt_fix.workspace(p_purchase)$$;
create function public.erp_cp7_correct_receipt_v1(p_payload jsonb,p_request uuid,p_expected text)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_receipt_fix.command(p_payload,p_request,p_expected)$$;
grant create on schema public to cp7_procure_write;
alter function public.erp_cp7_get_receipt_correction_v1(uuid)owner to cp7_procure_write;
alter function public.erp_cp7_correct_receipt_v1(jsonb,uuid,text)owner to cp7_procure_write;
revoke create on schema public from cp7_procure_write;
revoke all on function public.erp_cp7_get_receipt_correction_v1(uuid),public.erp_cp7_correct_receipt_v1(jsonb,uuid,text)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_get_receipt_correction_v1(uuid),public.erp_cp7_correct_receipt_v1(jsonb,uuid,text)to authenticated;

-- Material card v2: the same scope, access and money projection as v1, with
-- corrected receipt rows grouped under their original card row. Running
-- quantity is the complete chronological prefix of effective rows computed
-- before paging; raw immutable members stay inspectable.
create function cp7_receipt_fix.ledger(p_material uuid,p_roll uuid,p_location uuid,p_offset integer,p_limit integer)returns jsonb
language plpgsql stable security invoker set search_path=''as $$
declare a jsonb;rows jsonb;total bigint;
begin
 a:=cp7_material.access_now();
 if p_material is null or p_location is null or p_offset is null or p_offset not between 0 and 1000000
  or p_limit is null or p_limit not between 1 and 100 then raise exception 'CP7_MATERIAL_LEDGER_SCOPE';end if;
 if not exists(select 1 from erp.materials m where m.id=p_material and((m.material_type='FABRIC'and exists(select 1 from erp.material_rolls r where r.id=p_roll and r.material_id=m.id))
   or(m.material_type<>'FABRIC'and p_roll is null)))
  or not exists(select 1 from erp.locations where id=p_location)then raise exception 'CP7_MATERIAL_LEDGER_SCOPE';end if;
 with base as(
  select sm.*,coalesce(l.origin_id,sm.id)origin from erp.material_stock_movements sm left join cp7_receipt_fix.ledger_links l on l.member_id=sm.id
  where sm.material_id=p_material and sm.roll_id is not distinct from p_roll and sm.location_id=p_location and sm.physical_at<=statement_timestamp()
 ),grouped as(
  select b.origin,sum(b.qty_signed)effective_qty,count(*)-1 correction_count,max(b.system_created_at)last_recorded_at,
   jsonb_agg(jsonb_build_object('movement_id',b.id,'qty_signed',b.qty_signed::text,'movement_type',b.movement_type,'recorded_at',b.system_created_at,
    'physical_at',b.physical_at,'source_type',b.source_type,'reversal_of_id',b.reversal_of_id,'note',b.note)order by b.system_created_at,b.id)members
  from base b group by b.origin
 ),effective as(
  select o.*,g.effective_qty,g.correction_count,g.last_recorded_at,g.members,
   (select x.unit_cost_snapshot from base x where x.origin=o.id and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=x.id)and x.reversal_of_id is null
     order by x.system_created_at desc,x.id desc limit 1)effective_unit_cost,
   sum(g.effective_qty)over(order by o.physical_at,o.system_created_at,o.id rows unbounded preceding)running_qty
  from grouped g join erp.material_stock_movements o on o.id=g.origin
 ),paged as(select*from effective order by physical_at desc,system_created_at desc,id desc limit p_limit offset p_offset)
 select(select count(*)from effective),coalesce(jsonb_agg(jsonb_build_object('movement_id',x.id,'physical_at',x.physical_at,'recorded_at',x.system_created_at,
  'movement_type',x.movement_type,'qty_signed',x.effective_qty::text,'original_qty_signed',x.qty_signed::text,'running_qty',x.running_qty::text,
  'correction_count',x.correction_count::text,'last_correction_recorded_at',case when x.correction_count>0 then x.last_recorded_at end,
  'corrections',case when x.correction_count>0 then x.members else '[]'::jsonb end,
  'source_type',x.source_type,'source_id',x.source_id,'reversal_of_id',x.reversal_of_id,'note',x.note)
  ||case when(a->>'can_value')::boolean then jsonb_build_object('valuation',jsonb_build_object('state',case when coalesce(x.effective_unit_cost,x.unit_cost_snapshot)is null then 'UNKNOWN'else 'KNOWN'end,
   'unit_cost',coalesce(x.effective_unit_cost,x.unit_cost_snapshot)::text,'movement_value',round(x.effective_qty*coalesce(x.effective_unit_cost,x.unit_cost_snapshot),6)::text,'basis','CURRENT_RESTATED_MOVEMENT_COST'))else '{}'::jsonb end
  order by x.physical_at desc,x.system_created_at desc,x.id desc),'[]'::jsonb)into total,rows from paged x;
 return jsonb_build_object('contract_version','cp7.material-ledger.v2','material_id',p_material,'roll_id',p_roll,'location_id',p_location,
  'read_at',statement_timestamp(),'financial_captured',a->'can_value','history_basis','CORRECTED_EFFECTIVE_ROWS_CURRENT_RESTATED',
  'page',jsonb_build_object('rows',rows,'total',total::text,'offset',p_offset,'limit',p_limit,'next_offset',case when p_offset+jsonb_array_length(rows)<total then p_offset+jsonb_array_length(rows)else null end));
end $$;
grant usage on schema cp7_receipt_fix to cp7_material_read;
grant select on cp7_receipt_fix.ledger_links to cp7_material_read;
grant create on schema cp7_receipt_fix,public to cp7_material_read;
alter function cp7_receipt_fix.ledger(uuid,uuid,uuid,integer,integer)owner to cp7_material_read;
create function public.erp_cp7_get_material_ledger_v2(p_material uuid,p_roll uuid,p_location uuid,p_offset integer,p_limit integer)returns jsonb
language sql stable security definer set search_path=''as $$select cp7_receipt_fix.ledger(p_material,p_roll,p_location,p_offset,p_limit)$$;
alter function public.erp_cp7_get_material_ledger_v2(uuid,uuid,uuid,integer,integer)owner to cp7_material_read;
revoke create on schema cp7_receipt_fix,public from cp7_material_read;
revoke all on function cp7_receipt_fix.ledger(uuid,uuid,uuid,integer,integer)from public,anon,authenticated,service_role,cp7_capture;
revoke all on function public.erp_cp7_get_material_ledger_v2(uuid,uuid,uuid,integer,integer)from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_material_ledger_v2(uuid,uuid,uuid,integer,integer)to authenticated;
