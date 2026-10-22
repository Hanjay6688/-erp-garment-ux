-- OW-08b (D17-13 2.18). A kasbon journal (source CP7_KASBON) and its cancellation inverse open the kasbon itself from
-- the ledger. Reader only: the kasbon tables, writers and journals are unchanged.
create schema cp7_kasbon_source authorization postgres;
revoke all on schema cp7_kasbon_source from public,anon,authenticated,service_role,cp7_capture;
grant usage on schema cp7_kasbon_source to cp7_transaction_source_read;

-- The kasbon as the ledger's source document: its number, status and the Mandor whose kasbon list holds it.
create function cp7_kasbon_source.document_v1(p_id uuid)returns jsonb
language sql stable security definer set search_path=''as $$
 select jsonb_build_object('number',k.number,'status',k.status,'contractor_id',k.contractor_id)
 from cp7_kasbon.advances k where k.id=p_id
$$;

revoke all on function cp7_kasbon_source.document_v1(uuid)from public,anon,authenticated,service_role,cp7_capture;
grant execute on function cp7_kasbon_source.document_v1(uuid)to cp7_transaction_source_read;
