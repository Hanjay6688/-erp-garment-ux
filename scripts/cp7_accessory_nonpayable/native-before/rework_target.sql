CREATE OR REPLACE FUNCTION erp.be_reverse_rework_target_v1(p_rework uuid, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare v uuid;v_own boolean;
begin
 if not exists(select 1 from erp.be_rework_targets_v1 where rework_id=p_rework) then return;end if;
 v_own:=not erp.be_in_context_v1();
 if v_own then insert into erp.be_execution_context_v1(backend_pid,transaction_id,request_id) values(pg_backend_pid(),txid_current(),gen_random_uuid());end if;
 for v in select s.conversion_id from erp.be_conversion_sources_v1 s join erp.product_conversions c on c.id=s.conversion_id
    where s.rework_id=p_rework and c.status='POSTED' order by c.physical_at desc,c.id desc loop
   perform erp.be_reverse_conversion_v1(v,p_reason);
 end loop;
 if v_own then delete from erp.be_execution_context_v1 where backend_pid=pg_backend_pid() and transaction_id=txid_current();end if;
end;$function$
