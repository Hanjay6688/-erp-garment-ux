# Current used-state restore first result: INCOMPLETE

Candidate5359767befe09fb54bf421ff0eef07c26d6560f0,
treeea8f15e9f2d8569b3aeb327b4595d2a873b29ba9,
run39718548008/job119626408939, artifact12400825872.

Both actual APPLY100/REFUND100 correction900/restore1000 chains committed;
used-installation removal refused unchanged. The full used database dump
restored fresh with all649 table hashes equal and physical database/platform
owner, ACL and settings reproduced. Only the known19 pg_cron restore errors
were present. Whole pre-install database/CP6/roles/advisors were restored.

The scenario did not finish. Its actual row-drift control tried deactivating
the only active owner, so Native correctly refused LAST_ACTIVE_OWNER_PROTECTED
before the intended backup-row comparison. No final census rebind, restored
old/current receipt replay or restored UNDO/inverse is claimed. This is a
fixture fault, not evidence to loosen owner protection or the restore oracle.
The follow-up control changes an actual name field under a rolled-back
savepoint, preserving the same full-row-drift refusal requirement.

All6 original JSON streams are retained exactly; the18,912,887-byte trusted
manifest is losslessXZ, the other5 are gzip. Every raw-byte roundtrip was
checked, including the original report and partial controls/cleanup evidence.
Main193,535bytes SHA256
`944e3a87be886f09835a32e4d95fc51662f2461056c8e4242f447d3b5721decd`.
ZIP3,432,015bytes SHA256
`9e6ae0779215b9ca7876713dea7c2339cd9017b205d2f3d99a038737944448c6`.
WholeOW04 remains open; this is not operational backup setup or formalCP7C.
