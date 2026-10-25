# Captured physical inputs for scoped-model targets

The global baseline and a scoped model must describe the same physical inputs.
`non_stock` verifies all global non-stock completeness conditions before selecting
one root, its sales, returns and original/reversal journals. A target cannot hide
an overflow elsewhere in the captured global arrays.

`reference` combines that subset with the complete server-owned stock row digest
for this target at the exact global capture clock and the scoped producer hash.
Its identity payload is identical to the pinned scoped-history identity. When the
global capture includes all raw stock, it also checks the digest against those
exact raw rows. When global stock is omitted, it retains the INCOMPLETE raw status
and the separate SQL digest; it neither fabricates a complete raw source nor
substitutes empty rows or zero stock.

These are private pure functions with no public method or default installation.
The caller must obtain the digest from `cp7_history_reference.stock_digest` for
the exact target/capture time, obtain the current producer from the qualified
scoped capture, bind the history query and current model eligibility, and carry
the versioned model reference through source/provenance/cache checks. This does
not apply forecasts or replace the shared target/projection kernel. Native,
after-use restoration, model-target integration and independent acceptance need
their own evidence.
