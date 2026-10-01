-- CP7 current-authority admission only. The accepted release files retain
-- their bytes; Native balances, credit moves, journals, stock, HPP, actors,
-- UUID replay payloads, owners and ACLs retain their original rules.
-- Recheck after request/source/target waits and after all Native writes so a
-- later accounting lock cannot commit under a permission revoked meanwhile.
do $credit_guard$ begin
 if encode(extensions.digest(pg_get_functiondef('public.erp_save_supplier_credit_v1(jsonb,uuid)'::regprocedure),'sha256'),'hex')<>'26d6a5024fe1caf7b50a5f9b516d454baeaf94353ee84f90f454d7bcd6a4624c' then raise exception 'CP7_SUPPLIER_CREDIT_PREDECESSOR_CHANGED';end if;
 if encode(extensions.digest(pg_get_functiondef('erp.bf_supplier_credit_allocate_v1(jsonb,uuid)'::regprocedure),'sha256'),'hex')<>'9f3e2c02b022f2288d4ffcf8c21a1da07783e82cf11c6da5484189282daa8db0' then raise exception 'CP7_SUPPLIER_CREDIT_PREDECESSOR_CHANGED';end if;
end $credit_guard$;

CREATE OR REPLACE FUNCTION public.erp_save_supplier_credit_v1(p_payload jsonb, p_client_request_id uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare prior erp.bf_requests_v1%rowtype;result jsonb;actor uuid;
begin
 if current_setting('transaction_isolation')<>'read committed' then raise exception using errcode='25000',message='CP7_SUPPLIER_CREDIT_READ_COMMITTED_REQUIRED';end if;
 perform erp.require_owner_admin();perform erp.require_permission('finance.ap.pay');actor:=erp.current_app_user_id();
 if p_client_request_id is null then raise exception 'CLIENT_REQUEST_ID_REQUIRED';end if;
 perform pg_advisory_xact_lock(hashtextextended('BF:REQUEST:'||p_client_request_id,0));
 perform erp.require_owner_admin();perform erp.require_permission('finance.ap.pay');
 select * into prior from erp.bf_requests_v1 where request_id=p_client_request_id;
 if found then
   if prior.action<>'SUPPLIER_CREDIT_ALLOCATE' or prior.actor is distinct from actor or prior.payload is distinct from p_payload then
     raise exception 'CLIENT_REQUEST_ID_CONFLICT';end if;
   return prior.response||jsonb_build_object('replayed',true);
 end if;
 result:=erp.bf_supplier_credit_allocate_v1(p_payload,p_client_request_id)||jsonb_build_object('request_id',p_client_request_id,'replayed',false);
 insert into erp.bf_requests_v1 values(p_client_request_id,actor,'SUPPLIER_CREDIT_ALLOCATE',p_payload,result);
 perform erp.require_owner_admin();perform erp.require_permission('finance.ap.pay');
 return result;
end;$function$
;

CREATE OR REPLACE FUNCTION erp.bf_supplier_credit_allocate_v1(p_payload jsonb, p_request uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare h erp.material_supplier_returns%rowtype; src uuid; reason text; today date:=erp.bb_business_today_v1();
 targets uuid[]; affected uuid[]; item jsonb; target uuid; amount numeric; total numeric:=0; credit numeric;
 row_move erp.bf_supplier_credit_moves_v1%rowtype; event_id uuid; journal uuid; amount_paid numeric; payable numeric;
begin
 perform erp._cp3_assert_closed_json_object(p_payload,array['return_id','source_purchase_id','expected_version','allocations','reason'],
   array['return_id','source_purchase_id','expected_version','allocations','reason'],'supplier credit allocation');
 src:=erp.bd_uuid_v1(p_payload,'source_purchase_id',true);reason:=erp.bc_text_v1(p_payload,'reason',true,1000);
 select * into h from erp.material_supplier_returns where id=erp.bd_uuid_v1(p_payload,'return_id',true) for update;
 perform erp.require_owner_admin();perform erp.require_permission('finance.ap.pay');
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
   select unnest(targets) x union select e.target_purchase_id from erp.bf_supplier_credit_moves_v1 e
     where e.return_id=h.id and e.source_purchase_id=src
     group by e.target_purchase_id having sum(e.amount)<>0) ids;
 perform 1 from erp.material_purchase_headers where id=any(affected) order by id for update;
 perform erp.require_owner_admin();perform erp.require_permission('finance.ap.pay');
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
end;$function$
;
