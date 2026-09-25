# R9 C6 case ID/source-line crosswalk verification

Pinned owner annex C6 rev3 at `d1bc8adff3ba1a2a7001ef39e4819d0c3813d00b`, `docs/contracts/ERP_ADDENDUM_OWNER_DECISIONS_CP6_2026-09-25_LAMPIRAN_C6.md` §6.1 and §6.2 lines 231–333. Verified its 75 table rows against the original M acceptance IDs before any BB–BE candidate assessment. Oracle remains the three supplied contract files; annex maps IDs but its implementation/status labels are not evidence.

| Group | Annex IDs | Master Pulih source lines | Checked count |
|---|---|---|---:|
| Laundry | LAU-T01–T36 | M:4339–4374 consecutive | 36 |
| Accessory A | ACC-A01–A08 | M:5254–5261 consecutive | 8 |
| Accessory B | ACC-B01–B07 | M:5267–5273 consecutive | 7 |
| Accessory C | ACC-C01–C12 | M:5279–5290 consecutive | 12 |
| Accessory D | ACC-D01–D12 | M:5296–5307 consecutive | 12 |
| Total | 75 unique IDs | exact mapping | 75 |

No ID or line mismatches. Check does not validate writer scope tags BASELINE/CR or source implementations. The 39 ACC and 36 LAU expectations are frozen with SHA256 in `AUDIT_PROGRESS.md` and no cases are promoted to ACCEPT by this mapping check. ALL22 register identity is checked separately in `out/gpt_r9_all_mapping_check.md`. Next: generate fixture cases per ID against exact BB/BC/BD/BE product heads, compare native actual against the frozen oracle, preserve all untested/policy-sensitive cases UNVERIFIED/HOLD.
