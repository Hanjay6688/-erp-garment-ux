create function cp7_credit_note_carry_de.minimum_net_v1(p_events jsonb)returns numeric
language sql immutable security invoker set search_path=''as $$
 with events as(select value e from jsonb_array_elements(p_events)),cuts as(
  select distinct e->>'economic_date'e from events),books as(select distinct e->>'transaction_date'b from events)
 select greatest(0,coalesce(max((select coalesce(sum((v.e->>'amount')::numeric),0)from events v
  where v.e->>'economic_date'<=cuts.e and v.e->>'transaction_date'<=books.b)),0))from cuts cross join books
$$;
create function cp7_credit_note_carry_de.plan_v1(p_basis jsonb,p_new_net text)returns jsonb
language plpgsql immutable security invoker set search_path=''as $$
declare net numeric;amount numeric;minimum_net numeric;issues jsonb:=p_basis->'issues';remaining numeric;begin
 net:=ow04_pure_kernel.exact_amount_v1(to_jsonb(p_new_net))::numeric;
 amount:=ow04_pure_kernel.exact_amount_v1(p_basis->'transfer_amount')::numeric;
 minimum_net:=ow04_pure_kernel.exact_amount_v1(p_basis->'minimum_replacement_net')::numeric;
 if net<0 or amount<0 or minimum_net<amount or minimum_net is distinct from cp7_credit_note_carry_de.minimum_net_v1(p_basis->'incoming_events')then
  raise exception 'CP7_CREDIT_NOTE_CARRY_EXACT_BASIS_REQUIRED';end if;
 remaining:=net-amount;
 if net<minimum_net then issues:=issues||'"BASE_OVERFLOW_NONZERO"'::jsonb;end if;
 return jsonb_build_object('contract_version','cp7.note-credit-carry-review.v1','basis_sha256',p_basis->'basis_sha256',
  'transfer_amount',cp7_credit.cent_text(amount),'replacement_net',cp7_credit.cent_text(net),
  'remaining_amount',cp7_credit.cent_text(remaining),'state',case when issues='[]'::jsonb then'READY'else'REFUSE'end,
  'issues',issues,'policy','AUTO_TRANSFER_TO_REPLACEMENT','source_authority_proven',false,
  'money_events_created',0,'original_consumptions_changed',false);
end $$;
create function cp7_credit_note_carry_de.review_payload_v1(p_plan jsonb)returns jsonb
language sql immutable security invoker set search_path=''as $$
 select jsonb_build_object('contract_version','cp7.note-credit-carry-review.v1','basis_sha256',p_plan->'basis_sha256',
  'transfer_amount',p_plan->'transfer_amount','replacement_net',p_plan->'replacement_net','remaining_amount',p_plan->'remaining_amount')
$$;
