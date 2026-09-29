# F02 evidence boundaries and cross-check

Candidate: `17e85404c9c5f088875099d7875be6342ca6b266`; documentation checkpoint `5dd3b781ceef161afe59739d9e74a72e049d6a30`.

The oracle was committed with the auditor probes at `e1c9e72b0ddd6fad26ffc0e21473184c73c75c2f` before execution. Writer handoff was read: this is independent testing, not blind testing. Fixture builders and the accepted isolated installation/cleanup harness are reused. Own assertions use independent values, inverse transitions, boundary arithmetic and authorization races; inherited expectations are explicitly labeled `WRITER_RERUN`.

## Historical writer evidence checked

- P03: run 36509688817, source c56c3bb9b84a8d24e8dbe7a3b22bbd98b4d39111: 10 native, 4 race, 1 HTTP PASS. The P03 source, tests and runner are byte-identical in the F02 candidate.
- P04: run 36515586854, source 17e85404c9c5f088875099d7875be6342ca6b266: 17 kernel, 11 cutting, 6 opening/mixed/non-PO, 3 race, 2 HTTP PASS.
- Both downloaded ZIP digests and their extracted raw JSON exactly match the receipts and preserved gzip evidence. All 36 source-hash entries match. Repeated smoke cases are excluded from the 54 unique cases.
- Writer application run 36515590677: 638 unit/DOM, six existing shell browser cases, security/build, and two CodeQL jobs passed. This is not connected P03/P04 UI proof.
- Auditor application job 109270404782 at run 36526434075: 638 unit/DOM and security/build passed; 48 original owner-framework files verified. No independent browser rerun is claimed for F02: UI, browser spec and P02 SQL bytes are unchanged from the accepted F01 candidate.
- Latest writer checkpoint inspected: e21f0b94c3d25a787b83470a28b557aa7a88326a. P03/P04 source and bundle files remain unchanged. Later F03 work is not borrowed to qualify the frozen F02 candidate.

## Scope that remains downstream, not a discovered defect

P03/P04 deliver versioned production policy, original/current source identity, selected current WIP capture, and private matching/yield/working-calendar kernels. They do not deliver global planner integration or connected policy/WIP screens. P06–P08 still must join the chosen policy/membership and authoritative source/target/yield/calendar in one planning run. R10 connected sell/return remains CP7/P11. Price-later failed wash remains the documented F03/P13 obligation. Full P18 lifecycles, P19 scale and P20–P21 release acceptance remain open. FG here is production disposition, not sale/conversion-adjusted on-hand.

No product fix, hosted write, merge or production authorization was performed. CP6 and passed F01 acceptance remain preserved. `production_go=false`.
