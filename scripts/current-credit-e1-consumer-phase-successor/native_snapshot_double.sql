-- LOCAL typed Native snapshot DOUBLE, not the actual private Native copy.
-- Retain real source rows, status, both dates and physical model; own Native
-- document excludes consumer-money journals exactly as the E copy contract.
create function cp7_credit_note_carry_de.raw_native_snapshot_v1(p uuid)returns jsonb
language plpgsql stable as $$begin
 return cp7_credit.source_native_snapshot_v1(p)||cp7_credit_note_carry_de.raw_document_v1(p);
end$$;
