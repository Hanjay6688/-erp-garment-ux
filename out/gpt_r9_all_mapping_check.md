# R9 ALL22 register identity cross-check

Writer frozen head: `d1bc8adff3ba1a2a7001ef39e4819d0c3813d00b`. Source register `docs/cp6-au-r1-handoff.md` §29.6, lines 2251–2305; this is writer inventory and not contract/oracle authority. Original three contracts and owner's §0 remain normative for acceptance. The prior agent oracle `out/r9_all_oracle.md` was hashed and pushed before this writer-register comparison.

| Segment | IDs in writer §29.6 | Number |
|---|---|---:|
| P | P01–P04 | 4 |
| S | S01–S03 | 3 |
| Y | Y01–Y02 | 2 |
| A | A01–A03 | 3 |
| W | W01–W06 | 6 |
| C | C01–C04 | 4 |
| Total | exact one-to-one against `out/r9_all_oracle.md` headings | 22 |

Writer inventory reports nine MAPPED (P01,P02,S01,Y01,A01,A02,W01,W03,C01), six PARTIAL (P03,S03,A03,W02,W05,C02), seven NO_ADAPTER (P04,S02,Y02,W04,W06,C03,C04). Independently compared case IDs 22/22, no missing/extra. Counts/status merely reproduce the writer's inventory and are **not** independently validated against SQL or data. Three contracts M:369–379/M:930–938 and P:80/P:1024 support ALL/cutover integrity, but do not define the 22 IDs or adapter count. Therefore this exercise resolves register provenance only; runtime coverage remains 22/22 UNVERIFIED, and no 'MAPPED' case is a PASS. Preserve source hypotheses separate from oracle-derived expected effects.

Compare API e10260be85049f0078227f5ddb5767ffe481a0d9..d1bc8adff3ba1a2a7001ef39e4819d0c3813d00b: one commit, only `docs/contracts/ERP_ADDENDUM_OWNER_DECISIONS_CP6_2026-09-25_LAMPIRAN_C6.md` changed. No product path changed in this freeze.

Next: independent source-to-code diff and 22 disposable native import→continuation→inverse→UI cases at each writer BB/BC/BD/BE exact head; compare every effect to frozen agent oracle, leaving unsupported policy pending.
