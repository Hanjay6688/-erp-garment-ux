-- Deliberately local typed fixtures/doubles, NOT financial Native acceptance.
create schema erp;create schema cp7_sku_conversion;
create table erp.test_actor(id uuid primary key,role_name text,permissions text[],revoke_after_begin boolean default false,revoke_after_lot boolean default false);
insert into erp.test_actor values('10000000-0000-4000-8000-000000000090','OWNER',array['warehouse.accessory.view','finance.hpp.manage'],false,false);
create function erp.current_app_user_id()returns uuid language sql stable as $$select id from erp.test_actor$$;
create function erp.require_permission(p text)returns void language plpgsql as $$begin
 if not coalesce((select p=any(permissions)from erp.test_actor),false)then raise exception '42501 ACCESS_DENIED';end if;end$$;
create function erp.require_owner_admin()returns void language plpgsql as $$begin
 if(select role_name from erp.test_actor)not in('OWNER','ADMIN')then raise exception 'OWNER_ADMIN_REQUIRED';end if;end$$;
create function erp.require_internal()returns void language plpgsql as $$begin
 if erp.current_app_user_id()is null then raise exception 'AUTH_REQUIRED';end if;end$$;
create function erp._cp3_assert_closed_json_object(p jsonb,required text[],allowed text[],label text)returns void language plpgsql as $$begin
 if jsonb_typeof(p)<>'object' or exists(select 1 from jsonb_object_keys(p)k where not k=any(allowed))
  or exists(select 1 from unnest(required)k where p->k is null or p->k='null'::jsonb)then raise exception 'BAD_PAYLOAD';end if;end$$;
create function erp.bc_uuid_v1(p jsonb,k text,required boolean)returns uuid language sql as $$select(p->>k)::uuid$$;
create function erp.bc_text_v1(p jsonb,k text,required boolean,max_length int)returns text language sql as $$select p->>k$$;
create function erp.bc_parse_qty_v1(m uuid,p jsonb,k text)returns numeric language sql as $$select(p#>>'{}')::numeric$$;
create function erp.bb_parse_amount_v1(p text,k text)returns numeric language plpgsql as $$begin
 if p!~'^[0-9]+\.[0-9]{2}$'then raise exception 'BB_AMOUNT_INVALID';end if;return p::numeric;end$$;
create function erp.bc_location_v1(p uuid,k text[],label text)returns uuid language sql as $$select p$$;
create function erp.bc_parse_at_v1(p text,k text)returns timestamptz language sql as $$select p::timestamptz$$;
create function erp._cp3_business_date(p timestamptz)returns date language sql stable as $$select(p at time zone 'Asia/Jakarta')::date$$;
create table erp.accounting_period_control(singleton_id int primary key,closed_through date);
insert into erp.accounting_period_control values(1,null);
create function erp.resolve_accounting_transaction_date(p date)returns date language plpgsql as $$begin
 if exists(select 1 from erp.accounting_period_control where closed_through>=p)then raise exception 'PERIOD_CLOSED';end if;return p;end$$;
create function erp.bc_require_policy_v1(k text,label text)returns jsonb language sql as $$select jsonb_build_object('unit_value_cap','MOVING_AVERAGE','credit_account_id','10000000-0000-4000-8000-000000000099')$$;
create function erp.bc_policy_version_v1(k text)returns bigint language sql as $$select 1::bigint$$;
create function erp.bc_enter_context_v1()returns void language sql as $$select$$;
create function erp.bc_leave_context_v1()returns void language sql as $$select$$;
create table erp.test_requests(namespace text,id uuid,hash text,response jsonb,primary key(namespace,id));
create function erp._request_hash(p jsonb)returns text language sql immutable as $$select md5(p::text)$$;
create function erp._idempotency_begin(n text,r uuid,h text)returns jsonb language plpgsql as $$declare x erp.test_requests%rowtype;begin
 insert into erp.test_requests values(n,r,h,null)on conflict do nothing;select *into strict x from erp.test_requests where namespace=n and id=r;
 if x.hash<>h then raise exception 'REQUEST_REUSED';end if;
 -- Single-session authority boundary injection, explicitly NOT a two-session race.
 if(select revoke_after_begin from erp.test_actor)then update erp.test_actor set role_name='STAFF';end if;
 return x.response;end$$;
create function erp._idempotency_complete(n text,r uuid,p jsonb)returns jsonb language plpgsql as $$begin
 update erp.test_requests set response=p where namespace=n and id=r;return p;end$$;
create table cp7_sku_conversion.groups_v1(request_id uuid primary key);
create table cp7_sku_conversion.members_v1(conversion_id uuid primary key,group_id uuid,line_no integer);
create table erp.product_conversions(id uuid primary key,status text,from_product_id uuid,to_product_id uuid);
create table erp.fg_lots(id uuid primary key,po_id uuid,lot_origin text,source_lot_id uuid,product_id uuid);
create table erp.product_conversion_allocations(id uuid primary key,conversion_id uuid,source_lot_id uuid,destination_lot_id uuid,qty_pcs integer,conversion_cost_allocated numeric default 0);
create table erp.hpp_versions(id uuid primary key default gen_random_uuid(),lot_id uuid,version_no int,cost_state text,qty_basis_pcs int not null,total_cost numeric(24,6)not null default 0,
 hpp_per_pcs numeric(18,6)generated always as(total_cost/nullif(qty_basis_pcs,0)::numeric)stored,
 is_current boolean,supersedes_id uuid,calculation_reason text,created_by uuid);
create view erp.v_current_hpp as select distinct on(lot_id)lot_id,id hpp_version_id,version_no,cost_state,qty_basis_pcs,total_cost,hpp_per_pcs from erp.hpp_versions where is_current order by lot_id,version_no desc;
create table erp.hpp_version_components(hpp_version_id uuid,component_type text,description text,qty_basis numeric,unit_cost numeric,total_cost numeric,source_type text,source_id uuid);
create table erp.be_conversion_sources_v1(conversion_id uuid primary key,source_lot_id uuid);
create table erp.be_conversion_returns_v1(conversion_id uuid,outstanding_id uuid);
create table erp.be_conversion_cost_sources_v1(document_id uuid primary key,conversion_id uuid,kind text);
create table erp.be_conversion_cost_events_v1(id uuid primary key,document_id uuid,adjustment_id uuid,previous_amount numeric,target_amount numeric,journal_id uuid,economic_date date,created_by uuid);
create table erp.be_execution_context_v1(backend_pid int,transaction_id bigint,request_id uuid);
create function erp.be_in_context_v1()returns boolean language sql stable as $$select exists(select 1 from erp.be_execution_context_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current())$$;
create table erp.materials(id uuid primary key,moving_average_cost numeric(18,6),cached_stock_qty numeric(18,6),accessory_category_id uuid);
create table erp.material_stock_movements(id uuid primary key default gen_random_uuid(),material_id uuid,physical_at timestamptz,system_created_at timestamptz default statement_timestamp(),
 qty_signed numeric(18,6),unit_cost_snapshot numeric(18,6),input_unit_cost numeric(18,6),is_cost_recalculated boolean,reversal_of_id uuid,roll_id uuid,source_type text,source_id uuid);
create table erp.material_cost_history(material_id uuid,movement_id uuid primary key,physical_at timestamptz,stock_before numeric(18,6),stock_after numeric(18,6),average_before numeric(18,6),average_after numeric(18,6),movement_qty numeric(18,6),movement_unit_cost numeric(18,6));
create table erp.material_cost_checkpoints(material_id uuid primary key,checkpoint_date date,stock_qty numeric(18,6),moving_average_cost numeric(18,6),last_movement_id uuid);
create table erp.material_cost_revaluation_state(movement_id uuid);
create table erp.material_adjustment_revaluation_facts(id uuid);
create table erp.material_supplier_invoice_lines(id uuid);
create table erp.material_supplier_invoices(id uuid);
create table erp.material_purchase_items(id uuid primary key,purchase_id uuid,material_id uuid);
create table erp.cost_recalc_queue(id uuid default gen_random_uuid(),completed_at timestamptz);
create table erp.fg_accessory_cost_snapshots(id uuid default gen_random_uuid(),category_id uuid,hpp_method text);
create table erp.bc_return_lots_v1(id uuid primary key,document_id uuid,parent_event_id uuid,outstanding_id uuid,material_id uuid,value_mode text,received_at timestamptz);
create function erp.bc_lock_lot_v1(p uuid)returns erp.bc_return_lots_v1 language plpgsql as $$declare l erp.bc_return_lots_v1%rowtype;begin
 perform pg_advisory_xact_lock(hashtextextended('BCLOT|'||p::text,0));select *into strict l from erp.bc_return_lots_v1 where id=p for update;
 if(select revoke_after_lot from erp.test_actor)then update erp.test_actor set role_name='STAFF';end if;return l;end$$;
create table erp.bc_documents_v1(id uuid primary key,document_number text,action text,physical_at timestamptz,responsible text,reference text,reason text,payload jsonb,policy_versions jsonb,created_by uuid,status text default 'POSTED',row_version bigint default 1);
create table erp.bc_lot_events_v1(id uuid primary key default gen_random_uuid(),document_id uuid,lot_id uuid,event_kind text,condition text,qty numeric,event_at timestamptz,target_location_id uuid,unit_value numeric,amount numeric);
create function erp.bc_lot_state_v1(p uuid)returns jsonb language sql stable as $$select jsonb_build_object('usable',1-coalesce((select sum(qty)from erp.bc_lot_events_v1 where lot_id=p),0),'damaged',0)$$;
create table erp.bc_adjustment_purposes_v1(adjustment_id uuid primary key,document_id uuid,purpose text,account_id uuid);
create table erp.material_adjustments(id uuid primary key,amount numeric,status text);
create table erp.material_adjustment_items(id uuid primary key default gen_random_uuid(),adjustment_id uuid,material_id uuid);
create table erp.audit_logs(id bigserial primary key,entity_type text,entity_id uuid,action text,new_data jsonb,changed_by uuid,change_reason text);
create table erp.test_journal(id uuid primary key default gen_random_uuid(),source_type text,source_id uuid,date date,lines jsonb);
create function erp.post_journal(k text,i uuid,d date,reason text,lines jsonb)returns uuid language plpgsql as $$declare j uuid;begin
 insert into erp.test_journal(source_type,source_id,date,lines)values(k,i,d,lines)returning id into j;
 insert into erp.audit_logs(entity_type,entity_id,action)values('journal',j,'POST');return j;end$$;
create function erp._cp6_material_adjustment_revaluation_state(p uuid)returns jsonb language sql stable as $$select jsonb_build_object('current_value',amount,'incomplete_cost',0)from erp.material_adjustments where id=p$$;
create function erp.bc_post_adjustment_v1(doc uuid,loc uuid,at timestamptz,code text,items jsonb,reason text,purpose text,account uuid,policy text)returns uuid language plpgsql as $$
 declare a uuid:=gen_random_uuid();m uuid:=(items->0->>'material_id')::uuid;q numeric:=(items->0->>'qty_signed')::numeric;u numeric:=(items->0->>'input_unit_cost')::numeric;mid uuid;item_id uuid;stock numeric;begin
 insert into erp.material_adjustments values(a,round(q*u,2),'POSTED');insert into erp.material_adjustment_items(adjustment_id,material_id)values(a,m)returning id into item_id;
 insert into erp.bc_adjustment_purposes_v1 values(a,doc,purpose,account);
 select cached_stock_qty into stock from erp.materials where id=m;
 insert into erp.material_stock_movements(material_id,physical_at,qty_signed,unit_cost_snapshot,input_unit_cost,is_cost_recalculated,source_type,source_id)
 values(m,at,q,u,u,true,'MATERIAL_ADJUSTMENT_ITEM',item_id)returning id into mid;
 insert into erp.material_cost_history values(m,mid,at,stock,stock+q,u,u,q,u);update erp.materials set cached_stock_qty=stock+q where id=m;
 -- Four audit allocations model the actual material path; Native BE reconciliation is executed below unchanged.
 insert into erp.audit_logs(entity_type,entity_id,action)select 'material_adjustment',a,n::text from generate_series(1,4)n;
 return a;end$$;
create function erp.be_nonpo_sync_all_v1(d date,s text,i uuid,r text)returns void language plpgsql as $$begin perform erp.be_propagate_nonpo_v1();end$$;
create function erp.sync_po_hpp_to_gl(p uuid,d date)returns void language sql as $$select$$;
create function erp.assert_po_hpp_target_book_v2620e(p uuid)returns void language sql as $$select$$;
select set_config('app.change_reason','Declared local initial reason',false);
