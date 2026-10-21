-- Pending complete owning consumer composition. This pure source-credit bound
-- is not a Native date resolver, cash/target approval or posting authority.
do $not_an_installer$begin
 raise exception 'OW04_CONSUMER_REQUIRES_COMPLETE_OWNING_COMPOSITION';
end $not_an_installer$;

-- The complete coordinator supplies actual materialized I/C vectors and the
-- exact Native lawful/source floor. It must separately prove target-family,
-- cash, current authority and lock-set constraints. No browser supplies vectors,
-- a free book day, or a clock to this private function.
create function cp7_credit.consumer_positive_credit_book_bound_v1(
 p_recognition jsonb,p_consumptions jsonb,p_amount numeric,
 p_physical timestamptz,p_lawful date,p_source_floor date,p_clock timestamptz
)returns jsonb language plpgsql immutable security invoker set search_path=''as $$
declare i jsonb;c jsonb;e date;today date;v_floor date;book date;capacity jsonb;
 candidates jsonb:='[]';selected date;selected_capacity jsonb;
begin
 if p_amount is null or p_amount::text in('NaN','Infinity','-Infinity')or p_amount<=0
  or p_amount*100<>trunc(p_amount*100)then
  raise exception 'CP7_CREDIT_CONSUMER_EXACT_POSITIVE_CENTS_REQUIRED';end if;
 if p_physical is null or p_clock is null or p_lawful is null or p_source_floor is null
  or not isfinite(p_physical)or not isfinite(p_clock)or not isfinite(p_lawful)or not isfinite(p_source_floor)
  or p_physical>p_clock then raise exception 'CP7_CREDIT_CONSUMER_EXPLICIT_VALID_DATE_REQUIRED';end if;
 e:=(p_physical at time zone'Asia/Jakarta')::date;
 today:=(p_clock at time zone'Asia/Jakarta')::date;
 if p_lawful<e then raise exception 'CP7_CREDIT_CONSUMER_LAWFUL_DATE_BEFORE_ECONOMIC';end if;
 v_floor:=greatest(p_lawful,p_source_floor);
 if v_floor>today then raise exception 'CP7_CREDIT_CONSUMER_SOURCE_BOOK_IN_FUTURE';end if;
 i:=ow04_pure_kernel.normalize_events_v1(p_recognition,false);
 c:=ow04_pure_kernel.normalize_events_v1(p_consumptions,false);
 -- Capacity changes only at actual supplied book breakpoints. Include the
 -- lawful/source floor itself, retaining early partial capacity rather than
 -- taking a max of every unrelated later funding date.
 for book in select distinct candidate_book from(
   select v_floor as candidate_book union all
   select(x->>'transaction_date')::date from jsonb_array_elements(i||c)x
  )d where candidate_book>=v_floor and candidate_book<=today order by candidate_book loop
  capacity:=ow04_pure_kernel.credit_capacity_v1(i,c,e::text,book::text);
  if capacity->'source_prefixes_nonnegative'is distinct from'true'::jsonb then
   raise exception 'CP7_CREDIT_CONSUMER_EXISTING_JOINT_HISTORY_UNFUNDED';end if;
  candidates:=candidates||jsonb_build_array(jsonb_build_object('book_date',book,
   'capacity',capacity,'enough',(capacity->>'minimum_available')::numeric>=p_amount
    and(capacity->>'current_balance')::numeric>=p_amount));
  if selected is null and(capacity->>'minimum_available')::numeric>=p_amount
   and(capacity->>'current_balance')::numeric>=p_amount then
   selected:=book;selected_capacity:=capacity;
   exit; -- This capacity already proves every later joint cutoff.
  end if;
 end loop;
 if selected is null then raise exception 'CP7_CREDIT_CONSUMER_INSUFFICIENT_DATED_SOURCE_CAPACITY';end if;
 return jsonb_build_object('contract_version','ow04.consumer-source-book-bound.v1',
  'basis','SUPPLIED_SIGNED_RECOGNITION_AND_CONSUMPTION_VECTORS',
  'source_authority_proven',false,'complete_financial_operation_proven',false,
  'amount',cp7_credit.cent_text(p_amount::cp7_credit.cent_amount),
  'economic_date',e,'supplied_lawful_book_date',p_lawful,'supplied_source_floor',p_source_floor,
  'minimum_source_book_date',selected,'source_capacity',selected_capacity,
  'recognition_sha256',ow04_pure_kernel.vector_sha256_v1(i),
  'consumptions_sha256',ow04_pure_kernel.vector_sha256_v1(c),'candidates',candidates);
end $$;
alter function cp7_credit.consumer_positive_credit_book_bound_v1(jsonb,jsonb,numeric,timestamp with time zone,date,date,timestamp with time zone)owner to postgres;
revoke all on function cp7_credit.consumer_positive_credit_book_bound_v1(jsonb,jsonb,numeric,timestamp with time zone,date,date,timestamp with time zone)
 from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write,cp7_credit_write;
