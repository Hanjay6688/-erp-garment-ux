# Additional AG writer review

Owner requested continuation after AG writer PASS. This is additional writer
checking on original AG `119f8f133131eaf373f08cc45b7b3d6fc27a3d3e`, tree
`bd7dd026d40e64f08f03e122338d8a82ebfd292c`; independent AG review stays PENDING.

Seventeen native ordinary-caller cases cover return destination/grade, partial
returns and quantity caps, return posting/reversal retries, return header source
changes, full-stock repeated draft editing, duplicate SKU lines, changed payload
replay, cancellation replay, and physical dates before inventory availability.

The specific new hypothesis is a valid return to a different active FG warehouse
being refused because posting confuses the allocation's original warehouse with
the receipt destination. The existing item normalizer accepts an active FG
destination; the SalesPages simulation offers both main and reserve warehouses.
Paired same-warehouse controls distinguish this from fixture or permission errors.
This is a hypothesis until a complete native report reproduces it.

All product sources, admitted SQL, old tests, AG pins, and runtime construction
remain byte-identical. Only the two workflow routing shims and four new review
files change. The routing verifier restores each complete original workflow body
and compares it to frozen AG; any unknown path requires the full gate.

The separate runner constructs exact AC/AD/AE/AF/AG from admitted sources and
verifies all 690 AG objects. It verifies incoming Native AG #3 artifact10432153459,
SHA256 c7292683dcb0729b9634f1736f1dc42d2ed56b32af6a209b569b001a20e0b469,
before executing the new cases. No historical 500-case matrix is rerun.

Synthetic fixtures only; authenticated/OWNER operations with temporary schema
USAGE restored after testing. No table privileges added. HTTP/UI/real CSV,
hosted execution, and independent acceptance are not proved. Every case and full
unseeded boundary must be restored; all original functions remain exact. Preserve
failed attempts and distinguish fixture errors from business counterexamples.

Single writer; check branch before edits and push. CP6 and disposable test DB
only. Main, PR24/25, hosted databases, merge, deploy, and CP7 remain untouched.
`production_go:false`. Any proven material defect requires the entire affected
family to be fixed before relevant combined testing and independent handoff.
