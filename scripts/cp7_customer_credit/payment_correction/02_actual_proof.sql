do $not_an_installer$begin raise exception 'OW04_PAYMENT_SOURCE_REQUIRES_COMPLETE_OWNING_COMPOSITION';end $not_an_installer$;

create function cp7_credit.payment_terminal_header_v1(p_native jsonb,p_final jsonb,p_payment uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare j erp.journal_entries;before_version bigint;after_version bigint;
begin
 select *into strict j from erp.journal_entries where source_type='SALES_PAYMENT'and source_id=p_payment and reversal_of_id is null;
 before_version:=(p_native#>>'{sale,row_version}')::bigint;after_version:=(p_final#>>'{sale,row_version}')::bigint;
 if j.status not in('POSTED','REVERSED')or(p_native->'sale')-array['status','row_version','updated_at']is distinct from
   (p_final->'sale')-array['status','row_version','updated_at']
  or before_version is null or after_version is distinct from before_version+1
  or(p_final#>>'{sale,updated_at}')::timestamptz is distinct from j.posting_at
  or p_native-array['sale','hpp_support']is distinct from p_final-array['sale','hpp_support']then
  raise exception 'CP7_CREDIT_PAYMENT_NATIVE_TERMINAL_HEADER_CHANGED';end if;
 return jsonb_build_object('contract_version','ow04.payment-native-terminal-header.v1','payment_id',p_payment,
  'journal_id',j.id,'before_row_version',before_version,'final_row_version',after_version,'native_header_updates',1);
end $$;

-- Every field outside the explicitly listed real time journals stays exact.
-- This proves the actual Native neutral/effective pair before replacement.
create function cp7_credit.payment_time_pair_v1(p_inverse jsonb,p_ready jsonb,p_original uuid,p_neutral uuid,p_effective uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare original_j erp.journal_entries;inverse_j erp.journal_entries;neutral_j erp.journal_entries;effective_j erp.journal_entries;
 inverse_payload jsonb;neutral_payload jsonb;effective_payload jsonb;expected_journals jsonb;ar uuid;expected_events jsonb;
begin
 select *into strict original_j from erp.journal_entries where source_type='SALES_PAYMENT'and source_id=p_original and reversal_of_id is null;
 select *into strict inverse_j from erp.journal_entries where source_type='JOURNAL_REVERSAL'and source_id=original_j.id and reversal_of_id=original_j.id;
 if p_inverse-array['journals','base_events']is distinct from p_ready-array['journals','base_events']then
  raise exception 'CP7_CREDIT_PAYMENT_TIME_PAIR_UNRELATED_FACT_CHANGED';end if;
 expected_journals:=p_inverse->'journals';
 if original_j.economic_date=inverse_j.economic_date then
  if p_neutral is not null or p_effective is not null then raise exception 'CP7_CREDIT_PAYMENT_TIME_PAIR_UNEXPECTED';end if;
 else
  select *into strict neutral_j from erp.journal_entries where id=p_neutral;
  select *into strict effective_j from erp.journal_entries where id=p_effective;
  if(neutral_j.source_type,neutral_j.source_id,neutral_j.reversal_of_id,neutral_j.status,neutral_j.economic_date,neutral_j.transaction_date)
    is distinct from('PAYMENT_CORRECTION_TIME_NEUTRAL',p_original,null::uuid,'POSTED',inverse_j.economic_date,inverse_j.transaction_date)
   or(effective_j.source_type,effective_j.source_id,effective_j.reversal_of_id,effective_j.status,effective_j.economic_date,effective_j.transaction_date)
    is distinct from('PAYMENT_CORRECTION_EFFECTIVE',p_original,null::uuid,'POSTED',original_j.economic_date,original_j.transaction_date)
   or neutral_j.posting_at<inverse_j.posting_at or effective_j.posting_at<neutral_j.posting_at then
   raise exception 'CP7_CREDIT_PAYMENT_ACTUAL_TIME_PAIR_CHANGED';end if;
  inverse_payload:=cp7_credit.materialized_journal_payload(inverse_j.id);
  neutral_payload:=cp7_credit.materialized_journal_payload(neutral_j.id);
  effective_payload:=cp7_credit.materialized_journal_payload(effective_j.id);
  if cp7_credit.source_inverse_vector_v1(neutral_payload->'lines')is distinct from
     cp7_credit.source_inverse_vector_v1(inverse_payload->'lines',true)
   or cp7_credit.source_inverse_vector_v1(effective_payload->'lines')is distinct from
     cp7_credit.source_inverse_vector_v1(inverse_payload->'lines')then
   raise exception 'CP7_CREDIT_PAYMENT_TIME_PAIR_EXACT_VECTOR_CHANGED';end if;
  expected_journals:=expected_journals||jsonb_build_array(
   jsonb_build_object('id',neutral_j.id,'status',neutral_j.status,'immutable_payload',neutral_payload),
   jsonb_build_object('id',effective_j.id,'status',effective_j.status,'immutable_payload',effective_payload));
 end if;
 if cp7_credit.source_rows_v1(expected_journals)is distinct from cp7_credit.source_rows_v1(p_ready->'journals')then
  raise exception 'CP7_CREDIT_PAYMENT_TIME_PAIR_JOURNAL_SET_CHANGED';end if;
 expected_events:=cp7_credit.source_snapshot_base_events_v1(p_ready);
 return jsonb_build_object('contract_version','ow04.actual-payment-time-pair.v1','original_journal_id',original_j.id,
  'inverse_journal_id',inverse_j.id,'time_neutral_id',p_neutral,'effective_inverse_id',p_effective,
  'actual_ready_source_sha256',cp7_credit.pg_jsonb_sha256(p_ready),'actual_base_events_sha256',cp7_credit.pg_jsonb_sha256(expected_events));
end $$;

create function cp7_credit.payment_source_actual_proof_v1(p_operation uuid,p_before jsonb,p_actual jsonb)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare op jsonb;legs cp7_credit.payment_source_legs_v1;inverse_proof jsonb;time_proof jsonb;header_proof jsonb;
 original erp.sales_payments;replacement erp.sales_payments;fact erp.sales_payment_posting_facts;j erp.journal_entries;
 expected jsonb;row jsonb;ar uuid;replacement_event jsonb;
begin
 select coalesce((select to_jsonb(m)from cp7_credit.source_operation_materializations_v1 m where operation_id=p_operation),
  (select to_jsonb(w)from cp7_credit.source_operation_work_v1 w where operation_id=p_operation))into op;
 select *into strict legs from cp7_credit.payment_source_legs_v1 where operation_id=p_operation;
 if op is null or op->>'action'<>'PAYMENT_CORRECT'or op->'before_source'is distinct from p_before then
  raise exception 'CP7_CREDIT_PAYMENT_ACTUAL_OWNING_BINDING_REQUIRED';end if;
 inverse_proof:=cp7_credit.source_inverse_proof_v1(p_before,legs.inverse_native,'PAYMENT_REVERSE',(op->>'source_id')::uuid);
 header_proof:=cp7_credit.source_native_terminal_header_v1(legs.inverse_native,legs.inverse_final,(inverse_proof->>'inverse_journal_id')::uuid);
 time_proof:=cp7_credit.payment_time_pair_v1(legs.inverse_final,legs.replacement_before,(op->>'source_id')::uuid,
  legs.time_neutral_id,legs.effective_inverse_id);
 select (jsonb_populate_record(null::erp.sales_payments,x)).*into strict original from jsonb_array_elements(p_before->'payments')x
  where x->>'id'=op->>'source_id';
 select (jsonb_populate_record(null::erp.sales_payments,x)).*into strict replacement from jsonb_array_elements(p_actual->'payments')x
  where x->>'id'=legs.replacement_id::text;
 select (jsonb_populate_record(null::erp.sales_payment_posting_facts,x)).*into strict fact from jsonb_array_elements(p_actual->'payment_posting_facts')x
  where x->>'payment_id'=replacement.id::text;
 select (jsonb_populate_record(null::erp.journal_entries,(x->'immutable_payload'->'journal')||jsonb_build_object('status',x->>'status'))).*into strict j
  from jsonb_array_elements(p_actual->'journals')x where x->>'id'=fact.original_journal_entry_id::text;
 if replacement.status<>'POSTED'or to_jsonb(replacement)-'status'is distinct from legs.replacement_draft-'status'
  or replacement.sale_id is distinct from(op->>'sale_id')::uuid or replacement.replaces_payment_id is not null
  or replacement.amount is distinct from(op#>>'{payload,replacement,amount}')::numeric
  or replacement.payment_date is distinct from(op#>>'{payload,replacement,payment_date}')::timestamptz
  or replacement.cash_account_id is distinct from(op#>>'{payload,replacement,cash_account_id}')::uuid
  or replacement.payment_method is distinct from op#>>'{payload,replacement,payment_method}'
  or replacement.reference_number is distinct from op#>>'{payload,replacement,reference_number}'
  or replacement.notes is distinct from op#>>'{payload,replacement,notes}'
  or replacement.payment_number is distinct from left(original.payment_number,20)||' · K-'||replace(op->>'request_id','-','')
  or(fact.sale_id,fact.customer_id,fact.amount,fact.payment_date,fact.cash_account_id,fact.replaces_payment_id,fact.predecessor_reversal_journal_id)
   is distinct from(replacement.sale_id,(op#>>'{before_source,sale,customer_id}')::uuid,replacement.amount,replacement.payment_date,
    replacement.cash_account_id,null::uuid,null::uuid)
  or fact.payment_snapshot is distinct from to_jsonb(replacement)-'status'
  or fact.lineage_sha256 is distinct from cp7_credit.pg_jsonb_sha256(jsonb_build_array(fact.payment_id,fact.sale_id,fact.customer_id,
   fact.payment_number,fact.payment_date,fact.amount,fact.cash_account_id,fact.original_journal_entry_id,fact.journal_economic_date,
   fact.journal_transaction_date,fact.journal_posting_at,fact.replaces_payment_id,fact.predecessor_reversal_journal_id,fact.payment_snapshot))
  or(j.source_type,j.source_id,j.reversal_of_id,j.status,j.economic_date,j.transaction_date,j.posting_at)is distinct from
   ('SALES_PAYMENT',replacement.id,null::uuid,'POSTED',fact.journal_economic_date,fact.journal_transaction_date,fact.journal_posting_at)
  or j.economic_date is distinct from(replacement.payment_date at time zone'Asia/Jakarta')::date
  or j.transaction_date is distinct from j.economic_date
  or(select to_jsonb(p)-'status'from erp.sales_payments p where p.id=replacement.id)is distinct from to_jsonb(replacement)-'status'
  or(select to_jsonb(f)from erp.sales_payment_posting_facts f where f.payment_id=replacement.id)is distinct from to_jsonb(fact)then
  raise exception 'CP7_CREDIT_PAYMENT_ACTUAL_REPLACEMENT_FACT_CHANGED';end if;
 -- Actual Native captures include the one new payment/fact/journal and no
 -- arbitrary adoption of stock, HPP, headers, other payments or journal rows.
 if p_actual-array['payments','payment_posting_facts','journals','base_events']is distinct from
   legs.replacement_before-array['payments','payment_posting_facts','journals','base_events']then
  raise exception 'CP7_CREDIT_PAYMENT_REPLACEMENT_UNRELATED_FACT_CHANGED';end if;
 expected:=(legs.replacement_before->'payments')||jsonb_build_array(to_jsonb(replacement));
 if cp7_credit.source_rows_v1(p_actual->'payments')is distinct from cp7_credit.source_rows_v1(expected)then
  raise exception 'CP7_CREDIT_PAYMENT_ACTUAL_PAYMENT_SET_CHANGED';end if;
 expected:=(legs.replacement_before->'payment_posting_facts')||jsonb_build_array(to_jsonb(fact));
 if cp7_credit.source_rows_v1(p_actual->'payment_posting_facts')is distinct from cp7_credit.source_rows_v1(expected)then
  raise exception 'CP7_CREDIT_PAYMENT_ACTUAL_POSTING_FACT_SET_CHANGED';end if;
 expected:=(legs.replacement_before->'journals')||jsonb_build_array(jsonb_build_object('id',j.id,'status',j.status,
  'immutable_payload',cp7_credit.materialized_journal_payload(j.id)));
 if cp7_credit.source_rows_v1(p_actual->'journals')is distinct from cp7_credit.source_rows_v1(expected)then
  raise exception 'CP7_CREDIT_PAYMENT_ACTUAL_JOURNAL_SET_CHANGED';end if;
 perform cp7_credit.source_snapshot_base_events_v1(p_actual);
 select distinct c.ar_account_id into strict ar from cp7_credit.cohorts c where c.source_sale_id=replacement.sale_id;
 if cp7_credit.source_inverse_vector_v1(cp7_credit.materialized_journal_payload(j.id)->'lines')is distinct from
  cp7_credit.source_inverse_vector_v1(jsonb_build_array(
   jsonb_build_object('account_id',ar,'customer_id',fact.customer_id,'debit',0,'credit',replacement.amount),
   jsonb_build_object('account_id',(select coa_account_id from erp.cash_accounts where id=replacement.cash_account_id),
    'customer_id',fact.customer_id,'debit',replacement.amount,'credit',0)))then
  raise exception 'CP7_CREDIT_PAYMENT_REPLACEMENT_EXACT_JOURNAL_VECTOR_CHANGED';end if;
 return jsonb_build_object('contract_version','ow04.actual-compound-payment-source-proof.v1','operation_id',p_operation,
  'source_id',original.id,'replacement_id',replacement.id,'replacement_journal_id',j.id,
  'inverse_journal_id',inverse_proof->'inverse_journal_id','actual_pair',inverse_proof->'actual_pair',
  'inverse_proof',inverse_proof,'inverse_terminal_header',header_proof,'time_pair_proof',time_proof,
  'actual_leg_facts_sha256',cp7_credit.pg_jsonb_sha256(to_jsonb(legs)),
  'before_source_sha256',cp7_credit.pg_jsonb_sha256(p_before),'actual_source_sha256',cp7_credit.pg_jsonb_sha256(p_actual),
  'original_amount_preserved',original.amount,'replacement_amount',replacement.amount,
  'actual_replacement_posting_fact_sha256',cp7_credit.pg_jsonb_sha256(to_jsonb(fact)));
end $$;

create function cp7_credit.source_owned_actual_proof_v1(p_operation uuid,p_before jsonb,p_actual jsonb,p_action text,p_source uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
begin
 if p_action='PAYMENT_CORRECT'then return cp7_credit.payment_source_actual_proof_v1(p_operation,p_before,p_actual);end if;
 return cp7_credit.source_inverse_proof_v1(p_before,p_actual,p_action,p_source);
end $$;
