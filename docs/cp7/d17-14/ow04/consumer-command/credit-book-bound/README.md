# Source-credit book-date bound: not whole-operation date approval

consumer/04_credit_book_bound.sql finds the earliest supplied Native lawful/
source book breakpoint with sufficient credit over every later joint cutoff.
It uses the unchanged pure kernel on supplied signed recognition/consumption
vectors. A later unrelated funded amount does not delay an earlier supported
partial amount. Negative historical rectangles refuse even when current net
consumption is zero. The first sufficient bound terminates the search; that
kernel capacity already covers all later cutoffs.

This private pure helper proves arithmetic from supplied vectors only. It
neither authenticates those vectors nor approves a target invoice, cash source,
Native period resolution or a complete financial operation. The owning caller
must supply actual materialized data, current Native lawful floor and clock,
then independently prove all target-family/cash/permission/lock constraints.
The output explicitly keeps source_authority_proven and
complete_financial_operation_proven false. No free book-date API is exposed.

Sixteen local PGlite0.5.11 controls cover early80/later120 split funding, Native
lawful/source floors, later undo versus earlier economic use, both joint-margin
traps, historical withdrawal with current net C=0, one-cent overdraw, invalid
amounts/dates and private EXEC. Original first compile failure is retained:
a reserved DAY alias was rejected before any case executed. An explicit
candidate_book alias fixed it without changing expected money/date oracles.
The file remains behind its barrier and outside SQL_FILES. No Native case or
consumer command has been executed or implemented by this helper.
