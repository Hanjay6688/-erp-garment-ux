-- Must be last in a complete verified consumer installation transaction.
do $not_an_installer$begin
 raise exception 'OW04_CONSUMER_REQUIRES_COMPLETE_OWNING_COMPOSITION';
end $not_an_installer$;

grant execute on function cp7_credit.validate_consumer_payload_v1(jsonb,boolean),cp7_credit.consumer_payload_kind_v1(jsonb),
 cp7_credit.consumer_command_access_v1(text,text),cp7_credit.assert_consumer_scopes_clear_v1(),
 cp7_credit.consumer_completed_operation_v1(uuid,uuid,jsonb),cp7_credit.assert_consumer_closed_v1(uuid),
 cp7_credit.consumer_execute_v1(uuid)to cp7_credit_write;

create function public.erp_cp7_get_customer_credit_review_v1(p_payload jsonb)returns jsonb
language sql volatile security definer set search_path=''set TimeZone='UTC'as $$
 select cp7_credit.consumer_quote_v1(p_payload)
$$;
alter function public.erp_cp7_get_customer_credit_review_v1(jsonb)owner to postgres;
revoke all on function public.erp_cp7_get_customer_credit_review_v1(jsonb)
 from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write,cp7_credit_write;
grant execute on function public.erp_cp7_get_customer_credit_review_v1(jsonb)to authenticated;

create function public.erp_cp7_customer_credit_command_v1(p_payload jsonb,p_request uuid,p_expected_versions jsonb)returns jsonb
language sql volatile security definer set search_path=''set TimeZone='UTC'as $$
 select cp7_credit.consumer_command_v1(p_payload,p_request,p_expected_versions)
$$;
alter function public.erp_cp7_customer_credit_command_v1(jsonb,uuid,jsonb)owner to cp7_credit_write;
revoke all on function public.erp_cp7_customer_credit_command_v1(jsonb,uuid,jsonb)
 from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write;
grant execute on function public.erp_cp7_customer_credit_command_v1(jsonb,uuid,jsonb)to authenticated;

-- No table rights, generic line posting, Native source facade, scheduling,
-- service JWT capability or unrelated private schema access is introduced.
