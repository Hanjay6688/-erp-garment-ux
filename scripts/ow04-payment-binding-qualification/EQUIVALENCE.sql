create schema binding_equivalence;
create table binding_equivalence.live(like cp7_credit.source_operation_work_v1 including defaults);
create table binding_equivalence.saved(like cp7_credit.source_operation_materializations_v1 including defaults);
do $$declare t text;c record;begin foreach t in array array['live','saved']loop
 for c in select attname from pg_attribute where attrelid=('binding_equivalence.'||t)::regclass and attnum>0 and not attisdropped loop
 execute format('alter table binding_equivalence.%I alter column %I drop not null',t,c.attname);
 end loop;end loop;end$$;
CREATE OR REPLACE FUNCTION binding_equivalence.old_payload(p_operation uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
 SET "TimeZone" TO 'UTC'
AS $function$
declare live jsonb;saved jsonb;answer jsonb;other jsonb;
 fields text[]:=array['operation_id','operation_ordinal','predecessor_operation_id','backend_pid','transaction_id',
  'actor','request_id','action','sale_id','source_id','expected_version','payload','payload_sha256','authority_snapshot',
  'before_source','before_ordinal_input','before_ordinal_result','before_financial_profile','account_facts','period_snapshot',
  'actual_source','actual_source_proof','actual_ordinal_input','actual_ordinal_result','plan_manifest'];
begin
 select to_jsonb(w)into live from binding_equivalence.live w where operation_id=p_operation;
 select to_jsonb(m)into saved from binding_equivalence.saved m where operation_id=p_operation;
 if live is null and saved is null then raise exception 'CP7_CREDIT_SOURCE_OPERATION_BINDING_ABSENT';end if;
 select jsonb_object_agg(key,value)into answer from jsonb_each(coalesce(saved,live))where key=any(fields);
 if(select count(*)from jsonb_object_keys(answer))<>cardinality(fields)
  or exists(select 1 from jsonb_each(answer)where key<>'predecessor_operation_id'and value='null'::jsonb)then
  raise exception 'CP7_CREDIT_SOURCE_OPERATION_BINDING_INCOMPLETE';end if;
 if live is not null and saved is not null then
  select jsonb_object_agg(key,value)into other from jsonb_each(live)where key=any(fields);
  if other is distinct from answer then raise exception 'CP7_CREDIT_SOURCE_OPERATION_SAVED_BINDING_CHANGED';end if;
 end if;
 return jsonb_build_object('contract_version','ow04.source-operation-input-binding.v1','operation',answer);
end $function$
;
CREATE OR REPLACE FUNCTION binding_equivalence.new_payload(p_operation uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
 SET "TimeZone" TO 'UTC'
AS $function$
declare live jsonb;saved jsonb;answer jsonb;other jsonb;
 fields text[]:=array['operation_id','operation_ordinal','predecessor_operation_id','backend_pid','transaction_id',
  'actor','request_id','action','sale_id','source_id','expected_version','payload','payload_sha256','authority_snapshot',
  'before_source','before_ordinal_input','before_ordinal_result','before_financial_profile','account_facts','period_snapshot',
  'actual_source','actual_source_proof','actual_ordinal_input','actual_ordinal_result','plan_manifest'];
begin
 select jsonb_build_object('operation_id',w.operation_id,'operation_ordinal',w.operation_ordinal,'predecessor_operation_id',w.predecessor_operation_id,'backend_pid',w.backend_pid,'transaction_id',w.transaction_id,'actor',w.actor,'request_id',w.request_id,'action',w.action,'sale_id',w.sale_id,'source_id',w.source_id,'expected_version',w.expected_version,'payload',w.payload,'payload_sha256',w.payload_sha256,'authority_snapshot',w.authority_snapshot,'before_source',w.before_source,'before_ordinal_input',w.before_ordinal_input,'before_ordinal_result',w.before_ordinal_result,'before_financial_profile',w.before_financial_profile,'account_facts',w.account_facts,'period_snapshot',w.period_snapshot,'actual_source',w.actual_source,'actual_source_proof',w.actual_source_proof,'actual_ordinal_input',w.actual_ordinal_input,'actual_ordinal_result',w.actual_ordinal_result,'plan_manifest',w.plan_manifest)into live from binding_equivalence.live w where operation_id=p_operation;
 select jsonb_build_object('operation_id',m.operation_id,'operation_ordinal',m.operation_ordinal,'predecessor_operation_id',m.predecessor_operation_id,'backend_pid',m.backend_pid,'transaction_id',m.transaction_id,'actor',m.actor,'request_id',m.request_id,'action',m.action,'sale_id',m.sale_id,'source_id',m.source_id,'expected_version',m.expected_version,'payload',m.payload,'payload_sha256',m.payload_sha256,'authority_snapshot',m.authority_snapshot,'before_source',m.before_source,'before_ordinal_input',m.before_ordinal_input,'before_ordinal_result',m.before_ordinal_result,'before_financial_profile',m.before_financial_profile,'account_facts',m.account_facts,'period_snapshot',m.period_snapshot,'actual_source',m.actual_source,'actual_source_proof',m.actual_source_proof,'actual_ordinal_input',m.actual_ordinal_input,'actual_ordinal_result',m.actual_ordinal_result,'plan_manifest',m.plan_manifest)into saved from binding_equivalence.saved m where operation_id=p_operation;
 if live is null and saved is null then raise exception 'CP7_CREDIT_SOURCE_OPERATION_BINDING_ABSENT';end if;
 answer:=coalesce(saved,live);
 if(select count(*)from jsonb_object_keys(answer))<>cardinality(fields)
  or exists(select 1 from jsonb_each(answer)where key<>'predecessor_operation_id'and value='null'::jsonb)then
  raise exception 'CP7_CREDIT_SOURCE_OPERATION_BINDING_INCOMPLETE';end if;
 if live is not null and saved is not null then
  other:=live;
  if other is distinct from answer then raise exception 'CP7_CREDIT_SOURCE_OPERATION_SAVED_BINDING_CHANGED';end if;
 end if;
 return jsonb_build_object('contract_version','ow04.source-operation-input-binding.v1','operation',answer);
end $function$
;

create table binding_equivalence.checks(name text primary key);
create function binding_equivalence.answer(p_new boolean)returns jsonb language plpgsql as $$
begin
 if p_new then return jsonb_build_object('value',binding_equivalence.new_payload('c8c00000-0000-4000-8000-000000000001'));
 else return jsonb_build_object('value',binding_equivalence.old_payload('c8c00000-0000-4000-8000-000000000001'));end if;
exception when others then return jsonb_build_object('sqlstate',sqlstate,'message',sqlerrm);end$$;
create function binding_equivalence.check(p_name text,p_error text default null)returns void language plpgsql as $$
declare a jsonb:=binding_equivalence.answer(false);b jsonb:=binding_equivalence.answer(true);
begin
 if a is distinct from b then raise exception 'BINDING_PROJECTION_OUTPUT_OR_ERROR_DIFFERENT: %',p_name;end if;
 if p_error is null then
  if a#>>'{value,contract_version}'is distinct from'ow04.source-operation-input-binding.v1'then raise exception 'EXPECTED_VALID_BINDING: % %',p_name,a;end if;
 else if a->>'message'is distinct from p_error or a->>'sqlstate'is distinct from'P0001'then raise exception 'EXPECTED_ORIGINAL_REFUSAL: % %',p_name,a;end if;end if;
 insert into binding_equivalence.checks values(p_name);
end$$;
create function binding_equivalence.reset(p_live boolean,p_saved boolean)returns void language plpgsql as $reset$begin
truncate binding_equivalence.live,binding_equivalence.saved;
if p_live then insert into binding_equivalence.live select *from jsonb_populate_record(null::binding_equivalence.live,$sample${"operation_id":"c8c00000-0000-4000-8000-000000000001","operation_ordinal":1,"predecessor_operation_id":null,"backend_pid":123,"transaction_id":45,"actor":"c8c00000-0000-4000-8000-000000000002","request_id":"c8c00000-0000-4000-8000-000000000003","action":"PAYMENT_CORRECT","sale_id":"c8c00000-0000-4000-8000-000000000004","source_id":"c8c00000-0000-4000-8000-000000000005","expected_version":"7","payload":{"field":"payload","nested":{"amount":"999999999999999999.99","nullable":null},"rows":[1,"a",true]},"payload_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","authority_snapshot":{"field":"authority_snapshot","nested":{"amount":"999999999999999999.99","nullable":null},"rows":[1,"a",true]},"before_source":{"field":"before_source","nested":{"amount":"999999999999999999.99","nullable":null},"rows":[1,"a",true]},"before_ordinal_input":{"field":"before_ordinal_input","nested":{"amount":"999999999999999999.99","nullable":null},"rows":[1,"a",true]},"before_ordinal_result":{"field":"before_ordinal_result","nested":{"amount":"999999999999999999.99","nullable":null},"rows":[1,"a",true]},"before_financial_profile":{"field":"before_financial_profile","nested":{"amount":"999999999999999999.99","nullable":null},"rows":[1,"a",true]},"account_facts":{"field":"account_facts","nested":{"amount":"999999999999999999.99","nullable":null},"rows":[1,"a",true]},"period_snapshot":{"field":"period_snapshot","nested":{"amount":"999999999999999999.99","nullable":null},"rows":[1,"a",true]},"actual_source":{"field":"actual_source","nested":{"amount":"999999999999999999.99","nullable":null},"rows":[1,"a",true]},"actual_source_proof":{"field":"actual_source_proof","nested":{"amount":"999999999999999999.99","nullable":null},"rows":[1,"a",true]},"actual_ordinal_input":{"field":"actual_ordinal_input","nested":{"amount":"999999999999999999.99","nullable":null},"rows":[1,"a",true]},"actual_ordinal_result":{"field":"actual_ordinal_result","nested":{"amount":"999999999999999999.99","nullable":null},"rows":[1,"a",true]},"plan_manifest":{"field":"plan_manifest","nested":{"amount":"999999999999999999.99","nullable":null},"rows":[1,"a",true]}}$sample$::jsonb);end if;
if p_saved then insert into binding_equivalence.saved select *from jsonb_populate_record(null::binding_equivalence.saved,$sample${"operation_id":"c8c00000-0000-4000-8000-000000000001","operation_ordinal":1,"predecessor_operation_id":null,"backend_pid":123,"transaction_id":45,"actor":"c8c00000-0000-4000-8000-000000000002","request_id":"c8c00000-0000-4000-8000-000000000003","action":"PAYMENT_CORRECT","sale_id":"c8c00000-0000-4000-8000-000000000004","source_id":"c8c00000-0000-4000-8000-000000000005","expected_version":"7","payload":{"field":"payload","nested":{"amount":"999999999999999999.99","nullable":null},"rows":[1,"a",true]},"payload_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","authority_snapshot":{"field":"authority_snapshot","nested":{"amount":"999999999999999999.99","nullable":null},"rows":[1,"a",true]},"before_source":{"field":"before_source","nested":{"amount":"999999999999999999.99","nullable":null},"rows":[1,"a",true]},"before_ordinal_input":{"field":"before_ordinal_input","nested":{"amount":"999999999999999999.99","nullable":null},"rows":[1,"a",true]},"before_ordinal_result":{"field":"before_ordinal_result","nested":{"amount":"999999999999999999.99","nullable":null},"rows":[1,"a",true]},"before_financial_profile":{"field":"before_financial_profile","nested":{"amount":"999999999999999999.99","nullable":null},"rows":[1,"a",true]},"account_facts":{"field":"account_facts","nested":{"amount":"999999999999999999.99","nullable":null},"rows":[1,"a",true]},"period_snapshot":{"field":"period_snapshot","nested":{"amount":"999999999999999999.99","nullable":null},"rows":[1,"a",true]},"actual_source":{"field":"actual_source","nested":{"amount":"999999999999999999.99","nullable":null},"rows":[1,"a",true]},"actual_source_proof":{"field":"actual_source_proof","nested":{"amount":"999999999999999999.99","nullable":null},"rows":[1,"a",true]},"actual_ordinal_input":{"field":"actual_ordinal_input","nested":{"amount":"999999999999999999.99","nullable":null},"rows":[1,"a",true]},"actual_ordinal_result":{"field":"actual_ordinal_result","nested":{"amount":"999999999999999999.99","nullable":null},"rows":[1,"a",true]},"plan_manifest":{"field":"plan_manifest","nested":{"amount":"999999999999999999.99","nullable":null},"rows":[1,"a",true]}}$sample$::jsonb);end if;
end$reset$;
select binding_equivalence.reset(false,false);select binding_equivalence.check('absent','CP7_CREDIT_SOURCE_OPERATION_BINDING_ABSENT');
select binding_equivalence.reset(true,false);select binding_equivalence.check('live_only');
select binding_equivalence.reset(false,true);select binding_equivalence.check('saved_only');
select binding_equivalence.reset(true,true);select binding_equivalence.check('both_equal');
update binding_equivalence.live set phase='NATIVE_COMPLETE',active_plan_id='c8c00000-0000-4000-8000-000000000088';
update binding_equivalence.saved set financial_marker_id='c8c00000-0000-4000-8000-000000000099',actual_objects='[{"ignored_output":"different"}]';
select binding_equivalence.check('ignored_mutable_and_output_columns');
update binding_equivalence.live set payload=jsonb_set(payload,'{nested,nullable}','"changed"');
select binding_equivalence.check('live_saved_mismatch','CP7_CREDIT_SOURCE_OPERATION_SAVED_BINDING_CHANGED');
select binding_equivalence.reset(true,true);update binding_equivalence.saved set before_source=null;
select binding_equivalence.check('saved_null_does_not_adopt_live','CP7_CREDIT_SOURCE_OPERATION_BINDING_INCOMPLETE');
select binding_equivalence.reset(true,true);update binding_equivalence.live set before_source=null;
select binding_equivalence.check('live_null_cannot_adopt_saved','CP7_CREDIT_SOURCE_OPERATION_SAVED_BINDING_CHANGED');
select binding_equivalence.reset(true,true);update binding_equivalence.live set predecessor_operation_id='c8c00000-0000-4000-8000-000000000077';update binding_equivalence.saved set predecessor_operation_id='c8c00000-0000-4000-8000-000000000077';
select binding_equivalence.check('noninitial_predecessor_retained');
select binding_equivalence.reset(true,false);update binding_equivalence.live set operation_id=null;select binding_equivalence.check('null_operation_id','CP7_CREDIT_SOURCE_OPERATION_BINDING_ABSENT');
select binding_equivalence.reset(true,false);update binding_equivalence.live set operation_ordinal=null;select binding_equivalence.check('null_operation_ordinal','CP7_CREDIT_SOURCE_OPERATION_BINDING_INCOMPLETE');
select binding_equivalence.reset(true,false);update binding_equivalence.live set backend_pid=null;select binding_equivalence.check('null_backend_pid','CP7_CREDIT_SOURCE_OPERATION_BINDING_INCOMPLETE');
select binding_equivalence.reset(true,false);update binding_equivalence.live set transaction_id=null;select binding_equivalence.check('null_transaction_id','CP7_CREDIT_SOURCE_OPERATION_BINDING_INCOMPLETE');
select binding_equivalence.reset(true,false);update binding_equivalence.live set actor=null;select binding_equivalence.check('null_actor','CP7_CREDIT_SOURCE_OPERATION_BINDING_INCOMPLETE');
select binding_equivalence.reset(true,false);update binding_equivalence.live set request_id=null;select binding_equivalence.check('null_request_id','CP7_CREDIT_SOURCE_OPERATION_BINDING_INCOMPLETE');
select binding_equivalence.reset(true,false);update binding_equivalence.live set action=null;select binding_equivalence.check('null_action','CP7_CREDIT_SOURCE_OPERATION_BINDING_INCOMPLETE');
select binding_equivalence.reset(true,false);update binding_equivalence.live set sale_id=null;select binding_equivalence.check('null_sale_id','CP7_CREDIT_SOURCE_OPERATION_BINDING_INCOMPLETE');
select binding_equivalence.reset(true,false);update binding_equivalence.live set source_id=null;select binding_equivalence.check('null_source_id','CP7_CREDIT_SOURCE_OPERATION_BINDING_INCOMPLETE');
select binding_equivalence.reset(true,false);update binding_equivalence.live set expected_version=null;select binding_equivalence.check('null_expected_version','CP7_CREDIT_SOURCE_OPERATION_BINDING_INCOMPLETE');
select binding_equivalence.reset(true,false);update binding_equivalence.live set payload=null;select binding_equivalence.check('null_payload','CP7_CREDIT_SOURCE_OPERATION_BINDING_INCOMPLETE');
select binding_equivalence.reset(true,false);update binding_equivalence.live set payload_sha256=null;select binding_equivalence.check('null_payload_sha256','CP7_CREDIT_SOURCE_OPERATION_BINDING_INCOMPLETE');
select binding_equivalence.reset(true,false);update binding_equivalence.live set authority_snapshot=null;select binding_equivalence.check('null_authority_snapshot','CP7_CREDIT_SOURCE_OPERATION_BINDING_INCOMPLETE');
select binding_equivalence.reset(true,false);update binding_equivalence.live set before_source=null;select binding_equivalence.check('null_before_source','CP7_CREDIT_SOURCE_OPERATION_BINDING_INCOMPLETE');
select binding_equivalence.reset(true,false);update binding_equivalence.live set before_ordinal_input=null;select binding_equivalence.check('null_before_ordinal_input','CP7_CREDIT_SOURCE_OPERATION_BINDING_INCOMPLETE');
select binding_equivalence.reset(true,false);update binding_equivalence.live set before_ordinal_result=null;select binding_equivalence.check('null_before_ordinal_result','CP7_CREDIT_SOURCE_OPERATION_BINDING_INCOMPLETE');
select binding_equivalence.reset(true,false);update binding_equivalence.live set before_financial_profile=null;select binding_equivalence.check('null_before_financial_profile','CP7_CREDIT_SOURCE_OPERATION_BINDING_INCOMPLETE');
select binding_equivalence.reset(true,false);update binding_equivalence.live set account_facts=null;select binding_equivalence.check('null_account_facts','CP7_CREDIT_SOURCE_OPERATION_BINDING_INCOMPLETE');
select binding_equivalence.reset(true,false);update binding_equivalence.live set period_snapshot=null;select binding_equivalence.check('null_period_snapshot','CP7_CREDIT_SOURCE_OPERATION_BINDING_INCOMPLETE');
select binding_equivalence.reset(true,false);update binding_equivalence.live set actual_source=null;select binding_equivalence.check('null_actual_source','CP7_CREDIT_SOURCE_OPERATION_BINDING_INCOMPLETE');
select binding_equivalence.reset(true,false);update binding_equivalence.live set actual_source_proof=null;select binding_equivalence.check('null_actual_source_proof','CP7_CREDIT_SOURCE_OPERATION_BINDING_INCOMPLETE');
select binding_equivalence.reset(true,false);update binding_equivalence.live set actual_ordinal_input=null;select binding_equivalence.check('null_actual_ordinal_input','CP7_CREDIT_SOURCE_OPERATION_BINDING_INCOMPLETE');
select binding_equivalence.reset(true,false);update binding_equivalence.live set actual_ordinal_result=null;select binding_equivalence.check('null_actual_ordinal_result','CP7_CREDIT_SOURCE_OPERATION_BINDING_INCOMPLETE');
select binding_equivalence.reset(true,false);update binding_equivalence.live set plan_manifest=null;select binding_equivalence.check('null_plan_manifest','CP7_CREDIT_SOURCE_OPERATION_BINDING_INCOMPLETE');
select count(*)::int as checks_passed,true as exact_original_output_and_refusal_equivalence,false as Native_financial_execution from binding_equivalence.checks;
