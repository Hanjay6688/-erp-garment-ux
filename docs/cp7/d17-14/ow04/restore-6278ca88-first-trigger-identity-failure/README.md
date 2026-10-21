# First internal trigger identity failure retained

Candidate6278ca88dd621f7ca1ee0b4bcea79d0a9f1d9494, run39611142956,
job119260002698 did not pass the used restore scenario. Actual CREDIT and
REFUND committed, then source manifest export refused with
`OW04_RESTORE_DUPLICATE_CATALOG_IDENTITY: triggers`, before the used dump.
The full preinstallation CP6 state was restored exactly. All five original
JSON reports are retained as unchanged bytes in gzip; the downloaded artifact
ZIP was independently SHA256-verified, as recorded in RECEIPT.json.

Internal foreign-key triggers on a common parent can share the constraint
name, function and trigger type when the constraints belong to different
child tables. The previous portable identity omitted the constraint owning
table. The correction includes that table's qualified name in both identity
and metadata; no trigger is dropped or collapsed, and local numeric OIDs are
not used as portable identities. The normal runtime raw OID census is unchanged.

The local PGlite control reproduces the old collision with two children whose
FK is named link_fk, plus a self-referencing FK and an OLD/NEW WHEN trigger.
All22 metadata groups are equal on two instances with different OIDs and a
source-only dropped column. Every trigger has a unique identity. Changing a
foreign-key delete action changes the capture and is refused. This is local
metadata evidence, not a Native17 backup or product acceptance. A new actual
used-restore run is still required.
