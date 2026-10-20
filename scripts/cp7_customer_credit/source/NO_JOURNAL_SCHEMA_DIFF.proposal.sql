-- SOURCE-ONLY DELTA against ledger/01_immutable_facts.proposal.sql.
-- Deliberately not an installer. The owning registration writer, immutable
-- source-proof verifier and deferred factual closure must be integrated first.
do $not_an_installer$begin
 raise exception 'OW04_NO_JOURNAL_SCHEMA_REQUIRES_OWNING_SOURCE_PROOF';
end $not_an_installer$;

-- Existing immutable history columns and their values are retained. Existing
-- members with a real journal qualify mechanically as JOURNAL; this does not
-- qualify unknown historical ordinals or replay/header lineage.
alter table cp7_credit.return_family_members
 add column financial_state text not null default 'JOURNAL',
 add column financial_source_proof jsonb,
 alter column source_journal_id drop not null;
alter table cp7_credit.return_family_members
 alter column financial_state drop default,
 add constraint return_member_financial_state check(
  financial_state in('JOURNAL','NO_JOURNAL')and
  ((financial_state='JOURNAL'and source_journal_id is not null)
   or(financial_state='NO_JOURNAL'and source_journal_id is null))),
 add constraint return_member_no_journal_proof check(
  financial_state<>'NO_JOURNAL'or coalesce((
   financial_source_proof is not null and
   jsonb_typeof(financial_source_proof)='object'and
   financial_source_proof->>'contract_version'='ow04.native-no-return-journal-proof.v1'and
   financial_source_proof->>'return_id'=return_id::text and
   jsonb_typeof(financial_source_proof->'document')='object'and
   jsonb_typeof(financial_source_proof->'items')='array'and
   jsonb_array_length(financial_source_proof->'items')>0 and
   jsonb_typeof(financial_source_proof->'actual_original_fg_movements')='array'and
   jsonb_typeof(financial_source_proof->'actual_allocations')='array'and
   financial_source_proof->>'financial_event'='ABSENT'),false));

-- The CHECK validates shape only. The owning writer and factual closure must
-- recompute exactly the supplied full proof from actual rows under FG/source
-- locks and compare its digest with the immutable source_sha256 contract:
--  * actual POSTED/REVERSED non-draft return, nonempty positive-quantity items;
--  * every refund_amount=0 AND actual frozen unit_hpp_snapshot=0;
--  * exact Native allocation/item/lot/product/location/grade/quantity lineage;
--  * exactly one original SALE_RETURN movement per actual item, customer and
--    physical_at equal the document, no duplicate/unbound original movements;
--  * actual originals and source-bound inverse movement facts are retained;
--  * no SALES_RETURN original journal exists for this return at all;
--  * no economic/book event, invented UUID, zero journal or surrogate book date.
-- Nonzero HPP/cumulative-target cases without an original journal need their
-- own exact Native target proof; the narrow zero-HPP proof must refuse them.
-- Changed Native document status or appended inverse rows are separate state
-- bindings; they do not rewrite an original immutable source digest.

-- A financial cohort is created only when target/reconciliation components
-- exist. A zero-refund family itself has no marginal recognition target;
-- nevertheless, if a future authorized causal adjustment creates a cohort
-- whose recorded source member is NO_JOURNAL, its provenance is representable.
alter table cp7_credit.cohorts
 add column source_return_financial_state text not null default 'JOURNAL',
 add column source_return_financial_proof jsonb,
 alter column source_return_journal_id drop not null;
alter table cp7_credit.cohorts
 alter column source_return_financial_state drop default,
 add constraint cohort_return_financial_state check(
  source_return_financial_state in('JOURNAL','NO_JOURNAL')and
  ((source_return_financial_state='JOURNAL'and source_return_journal_id is not null)
   or(source_return_financial_state='NO_JOURNAL'and source_return_journal_id is null))),
 add constraint cohort_return_no_journal_proof check(
  source_return_financial_state<>'NO_JOURNAL'or coalesce((
   source_return_financial_proof is not null and
   jsonb_typeof(source_return_financial_proof)='object'and
   source_return_financial_proof->>'contract_version'='ow04.native-no-return-journal-proof.v1'and
   source_return_financial_proof->>'return_id'=source_return_id::text),false));

-- Final factual closure must require cohort financial_state/proof/journal to
-- equal the same immutable source member, not merely this local CHECK. No
-- caller-controlled JSON value, preserved actor, or execution context is proof.
-- The old source_sale_journal_id remains required for financial cohorts here;
-- a zero-money sale with no dated causal journal cannot use the paired poster.
