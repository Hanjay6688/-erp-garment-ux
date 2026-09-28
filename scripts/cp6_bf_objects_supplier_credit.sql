-- Return credit starts on its original purchase. Moving it changes document
-- allocation only: AP in total, cash, physical stock and product costs stay put.
create table erp.bf_supplier_credit_moves_v1(
 id uuid primary key default gen_random_uuid(), return_id uuid not null references erp.material_supplier_returns(id),
 source_purchase_id uuid not null references erp.material_purchase_headers(id),
 target_purchase_id uuid not null references erp.material_purchase_headers(id),
 amount numeric(20,2) not null check(amount<>0), effective_date date not null,
 reversal_of uuid unique references erp.bf_supplier_credit_moves_v1(id),
 reason text not null, actor uuid, request_id uuid not null,
 journal_id uuid references erp.journal_entries(id), created_at timestamptz not null default clock_timestamp(),
 check(source_purchase_id<>target_purchase_id), check((amount>0)=(reversal_of is null))
);
create index bf_supplier_credit_source on erp.bf_supplier_credit_moves_v1(return_id,source_purchase_id);
create index bf_supplier_credit_target on erp.bf_supplier_credit_moves_v1(target_purchase_id,effective_date);

CREATE OR REPLACE FUNCTION erp.bf_supplier_credit_delta_v1(p_purchase uuid,p_through date DEFAULT NULL)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select coalesce(sum(case when source_purchase_id=p_purchase then amount else -amount end),0)
 from erp.bf_supplier_credit_moves_v1 where p_purchase in(source_purchase_id,target_purchase_id)
   and(p_through is null or effective_date<=p_through)
$function$;

CREATE OR REPLACE FUNCTION erp.bf_supplier_credit_source_v1(p_return uuid,p_purchase uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select coalesce((f.before_state->p_purchase::text->>'ap')::numeric-(f.after_state->p_purchase::text->>'ap')::numeric,0)
 from erp.supplier_cent_posting_facts f join erp.material_supplier_returns r on r.id=f.source_id and r.status='POSTED'
 where f.source_type='MATERIAL_SUPPLIER_RETURN' and f.phase='POST' and f.source_id=p_return
$function$;

CREATE OR REPLACE FUNCTION erp.bf_supplier_credit_revision_v1(p_return uuid)
 RETURNS text LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select md5(coalesce((select status||':'||row_version from erp.material_supplier_returns where id=p_return),'')||':'||
   coalesce((select string_agg(id::text,',' order by created_at,id) from erp.bf_supplier_credit_moves_v1 where return_id=p_return),''))
$function$;

CREATE OR REPLACE FUNCTION erp.bf_supplier_credit_guard_v1()
 RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
begin
 if TG_TABLE_NAME='bf_supplier_credit_moves_v1' then raise exception 'BF_CREDIT_APPEND_ONLY';end if;
 if TG_TABLE_NAME='material_purchase_headers' then
   if old.status='POSTED' and new.status<>old.status and exists(select 1 from erp.bf_supplier_credit_moves_v1 e
     where old.id in(e.source_purchase_id,e.target_purchase_id) group by e.return_id,e.source_purchase_id,e.target_purchase_id having sum(e.amount)<>0) then
     raise exception 'BF_CREDIT_PURCHASE_IN_USE';end if;
   return new;
 end if;
 if old.status='POSTED' and new.status<>old.status and exists(
   select 1 from erp.bf_supplier_credit_moves_v1 e where e.return_id=old.id
   group by e.source_purchase_id,e.target_purchase_id having sum(e.amount)<>0) then
   raise exception 'BF_CREDIT_RETURN_IN_USE: kembalikan alokasi kredit sebelum membalik retur';end if;
 return new;
end;$function$;

CREATE OR REPLACE FUNCTION public.erp_get_supplier_credit_v1(p_filters jsonb DEFAULT '{}'::jsonb)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare supplier uuid; result jsonb; page_no integer;
begin
 perform erp.require_permission('finance.ap.view');
 perform erp._cp3_assert_closed_json_object(p_filters,array[]::text[],array['supplier_id','page'],'supplier credit filters');
 supplier:=erp.bd_uuid_v1(p_filters,'supplier_id',false);page_no:=greatest(1,coalesce((p_filters->>'page')::integer,1));
 with credits as materialized(
   select r.id return_id,r.return_number,r.supplier_id,r.physical_at,i.purchase_id source_purchase_id,h.purchase_number,
     erp.bf_supplier_credit_source_v1(r.id,i.purchase_id) credit,
     coalesce((select sum(e.amount) from erp.bf_supplier_credit_moves_v1 e where e.return_id=r.id and e.source_purchase_id=i.purchase_id),0) moved
   from erp.material_supplier_returns r join(select distinct return_id,purchase_id from erp.material_supplier_return_items ri
     join erp.material_purchase_items pi on pi.id=ri.purchase_item_id)i on i.return_id=r.id
   join erp.material_purchase_headers h on h.id=i.purchase_id
   where r.status='POSTED' and(supplier is null or r.supplier_id=supplier)
 ), positive as materialized(select * from credits where credit>0)
 select jsonb_build_object('supplier_id',supplier,'page',page_no,'total',(select count(*) from positive),
   'can_manage',erp.current_app_role() in('OWNER','ADMIN') and erp.has_permission('finance.ap.pay'),
   'suppliers',coalesce((select jsonb_agg(jsonb_build_object('id',s.id,'code',s.supplier_code,'name',s.supplier_name) order by s.supplier_name,s.id)
     from erp.suppliers s where exists(select 1 from erp.material_purchase_headers h where h.supplier_id=s.id and h.status='POSTED')),'[]'),
   'credits',coalesce((select jsonb_agg(jsonb_build_object('return_id',x.return_id,'return_number',x.return_number,'supplier_id',x.supplier_id,
     'source_purchase_id',x.source_purchase_id,'purchase_number',x.purchase_number,'physical_at',x.physical_at,
     'credit',x.credit::numeric(20,2)::text,'original_purchase_credit',(x.credit-x.moved)::numeric(20,2)::text,
     'version',erp.bf_supplier_credit_revision_v1(x.return_id),
     'allocations',coalesce((select jsonb_agg(jsonb_build_object('purchase_id',a.target_purchase_id,'amount',a.amount::numeric(20,2)::text))
       from(select e.target_purchase_id,sum(e.amount) amount from erp.bf_supplier_credit_moves_v1 e
         where e.return_id=x.return_id and e.source_purchase_id=x.source_purchase_id group by e.target_purchase_id having sum(e.amount)>0)a),'[]'),
     'events',coalesce((select jsonb_agg(jsonb_build_object('id',e.id,'purchase_id',e.target_purchase_id,'amount',e.amount::numeric(20,2)::text,
       'date',e.effective_date,'reason',e.reason,'reversal_of',e.reversal_of,'journal_id',e.journal_id) order by e.created_at,e.id)
       from erp.bf_supplier_credit_moves_v1 e where e.return_id=x.return_id and e.source_purchase_id=x.source_purchase_id),'[]'))
     order by x.physical_at desc,x.return_id,x.source_purchase_id) from(select * from positive order by physical_at desc,return_id,source_purchase_id limit 50 offset(page_no-1)*50)x),'[]'),
   'purchases',case when supplier is not null then coalesce((select jsonb_agg(jsonb_build_object('id',h.id,'number',h.purchase_number,
     'date',erp._cp3_business_date(h.physical_at),'final_ap',round(erp.material_purchase_final_ap_total(h.id),2)::text,
     'paid',p.paid::numeric(20,2)::text,'remaining',(round(erp.material_purchase_final_ap_total(h.id),2)-p.paid)::numeric(20,2)::text,
     'credit_delta',erp.bf_supplier_credit_delta_v1(h.id)::numeric(20,2)::text,'payment_status',h.payment_status) order by h.physical_at,h.id)
     from erp.material_purchase_headers h cross join lateral(select coalesce(sum(amount),0) paid from erp.supplier_payments where purchase_id=h.id and status='POSTED')p
     where h.supplier_id=supplier and h.status='POSTED'),'[]') else '[]'::jsonb end) into result;
 return result;
end;$function$;
create trigger bf_supplier_credit_append_only before update or delete on erp.bf_supplier_credit_moves_v1
 for each row execute function erp.bf_supplier_credit_guard_v1();
create trigger bf_supplier_return_credit_guard before update of status on erp.material_supplier_returns
 for each row execute function erp.bf_supplier_credit_guard_v1();
create trigger bf_supplier_purchase_credit_guard before update of status on erp.material_purchase_headers
 for each row execute function erp.bf_supplier_credit_guard_v1();

CREATE OR REPLACE FUNCTION erp.bf_supplier_credit_allocate_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare h erp.material_supplier_returns%rowtype; src uuid; reason text; today date:=erp.bb_business_today_v1();
 targets uuid[]; affected uuid[]; item jsonb; target uuid; amount numeric; total numeric:=0; credit numeric;
 row_move erp.bf_supplier_credit_moves_v1%rowtype; event_id uuid; journal uuid; amount_paid numeric; payable numeric;
begin
 perform erp._cp3_assert_closed_json_object(p_payload,array['return_id','source_purchase_id','expected_version','allocations','reason'],
   array['return_id','source_purchase_id','expected_version','allocations','reason'],'supplier credit allocation');
 src:=erp.bd_uuid_v1(p_payload,'source_purchase_id',true);reason:=erp.bc_text_v1(p_payload,'reason',true,1000);
 select * into h from erp.material_supplier_returns where id=erp.bd_uuid_v1(p_payload,'return_id',true) for update;
 if h.id is null or h.status<>'POSTED' then raise exception 'BF_CREDIT_RETURN_NOT_POSTED';end if;
 if erp._cp3_business_date(h.physical_at)>today then raise exception 'BF_CREDIT_NOT_YET_AVAILABLE';end if;
 if p_payload->>'expected_version' is distinct from erp.bf_supplier_credit_revision_v1(h.id) then raise exception 'STALE_VERSION';end if;
 if jsonb_typeof(p_payload->'allocations') is distinct from 'array' or jsonb_array_length(p_payload->'allocations')>100 then
   raise exception 'BF_CREDIT_ALLOCATIONS_INVALID';end if;
 targets:=array[src];
 for item in select value from jsonb_array_elements(p_payload->'allocations') loop
   perform erp._cp3_assert_closed_json_object(item,array['purchase_id','amount'],array['purchase_id','amount'],'credit target');
   target:=erp.bd_uuid_v1(item,'purchase_id',true);amount:=erp.bd_amount_v1(item->'amount','amount',false);
   if amount<=0 or amount<>round(amount,2) or target=any(targets) then raise exception 'BF_CREDIT_TARGET_INVALID';end if;
   total:=total+amount;targets:=targets||target;
 end loop;
 select array_agg(distinct x order by x) into affected from(
   select unnest(targets) x union select target_purchase_id from erp.bf_supplier_credit_moves_v1
     where return_id=h.id and source_purchase_id=src) ids;
 perform 1 from erp.material_purchase_headers where id=any(affected) order by id for update;
 if (select count(*) from erp.material_purchase_headers where id=any(affected) and supplier_id=h.supplier_id
     and status='POSTED' and erp._cp3_business_date(physical_at)<=today)<>cardinality(affected) then
   raise exception 'BF_CREDIT_SAME_SUPPLIER_REQUIRED';end if;
 credit:=erp.bf_supplier_credit_source_v1(h.id,src);
 if credit is null or credit<=0 or total>credit then raise exception 'BF_CREDIT_EXCEEDS_RETURN';end if;
 -- Append inverses first; the following desired allocation is one transaction.
 for row_move in select e.* from erp.bf_supplier_credit_moves_v1 e where e.return_id=h.id and e.source_purchase_id=src and e.amount>0
   and not exists(select 1 from erp.bf_supplier_credit_moves_v1 undo where undo.reversal_of=e.id) order by e.id loop
   event_id:=gen_random_uuid();
   journal:=erp.post_journal('BF_SUPPLIER_CREDIT_MOVE',event_id,today,reason,
     jsonb_build_array(jsonb_build_object('mapping_key','AP_SUPPLIER','debit',row_move.amount,'credit',0),
       jsonb_build_object('mapping_key','AP_SUPPLIER','debit',0,'credit',row_move.amount)));
   insert into erp.bf_supplier_credit_moves_v1(id,return_id,source_purchase_id,target_purchase_id,amount,effective_date,reversal_of,reason,actor,request_id,journal_id)
     values(event_id,h.id,src,row_move.target_purchase_id,-row_move.amount,today,row_move.id,reason,erp.current_app_user_id(),p_request,journal);
 end loop;
 for item in select value from jsonb_array_elements(p_payload->'allocations') loop
   target:=(item->>'purchase_id')::uuid;amount:=(item->>'amount')::numeric;event_id:=gen_random_uuid();
   journal:=erp.post_journal('BF_SUPPLIER_CREDIT_MOVE',event_id,today,reason,
     jsonb_build_array(jsonb_build_object('mapping_key','AP_SUPPLIER','debit',amount,'credit',0),
       jsonb_build_object('mapping_key','AP_SUPPLIER','debit',0,'credit',amount)));
   insert into erp.bf_supplier_credit_moves_v1(id,return_id,source_purchase_id,target_purchase_id,amount,effective_date,reason,actor,request_id,journal_id)
     values(event_id,h.id,src,target,amount,today,reason,erp.current_app_user_id(),p_request,journal);
 end loop;
 foreach target in array affected loop
   select round(erp.material_purchase_final_ap_total(target),2),coalesce((select sum(p.amount) from erp.supplier_payments p
     where p.purchase_id=target and p.status='POSTED'),0) into payable,amount_paid;
   if payable<amount_paid then raise exception 'BF_CREDIT_TARGET_ALREADY_PAID: alokasi melewati sisa utang atau kredit sudah dipakai pembayaran';end if;
   update erp.material_purchase_headers set payment_status=case when amount_paid=payable then 'PAID' when amount_paid>0 then 'PARTIAL' else 'UNPAID' end where id=target;
 end loop;
 return jsonb_build_object('return_id',h.id,'source_purchase_id',src,'version',erp.bf_supplier_credit_revision_v1(h.id),
   'credit',credit::numeric(20,2)::text,'original_purchase_credit',(credit-total)::numeric(20,2)::text,'allocated_elsewhere',total::numeric(20,2)::text,'effective_date',today);
end;$function$;

CREATE OR REPLACE FUNCTION public.erp_save_supplier_credit_v1(p_payload jsonb,p_client_request_id uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare prior erp.bf_requests_v1%rowtype;result jsonb;actor uuid;
begin
 perform erp.require_owner_admin();perform erp.require_permission('finance.ap.pay');actor:=erp.current_app_user_id();
 if p_client_request_id is null then raise exception 'CLIENT_REQUEST_ID_REQUIRED';end if;
 perform pg_advisory_xact_lock(hashtextextended('BF:REQUEST:'||p_client_request_id,0));
 select * into prior from erp.bf_requests_v1 where request_id=p_client_request_id;
 if found then
   if prior.action<>'SUPPLIER_CREDIT_ALLOCATE' or prior.actor is distinct from actor or prior.payload is distinct from p_payload then
     raise exception 'CLIENT_REQUEST_ID_CONFLICT';end if;
   return prior.response||jsonb_build_object('replayed',true);
 end if;
 result:=erp.bf_supplier_credit_allocate_v1(p_payload,p_client_request_id)||jsonb_build_object('request_id',p_client_request_id,'replayed',false);
 insert into erp.bf_requests_v1 values(p_client_request_id,actor,'SUPPLIER_CREDIT_ALLOCATE',p_payload,result);
 return result;
end;$function$;
