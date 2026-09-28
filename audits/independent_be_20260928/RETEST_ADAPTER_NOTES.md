# Retest adapter log (product e96db5a remains unchanged)

Original ORACLE.md and PLAN.md remain byte-identical. The revised public contract is read only to call the actual interface; business amounts are independently calculated.

- BD partial five-piece component now supplies explicit recipient size s2. Whole-shipment and invalid/ambiguous coverage controls remain exercised.
- The original IND-08 call supplied KNOWN0.00. That is an invalid-free negative control, not a legitimate waiver. The revised run now labels it correctly; separate FREE and WAIVED master, physical, unknown-resolution and UI cases test legitimate positive paths.
- First revision run created new component rates on a vendor that already had later dispatches. The public history guard refused the backdated master. Positive free tests now create their own unused vendors. No guard is bypassed, and no product failure is inferred from the fixture refusal.
- Old discovery test attempted overlapping FREE/WAIVED/UNKNOWN versions after FREE became supported. Its four status versions now have separate effective dates, with exact readback zero versus null.
- Source paging button label is the actual `Simpan draf invoice`. The first draft-submit adapter used a shortened label. Paging itself already returned all201 sources without duplicate IDs.
- Browser targets are scrolled into view before normal clicks when sticky runtime chrome covers them. No force clicks, DOM business-state edits, or network mocks are used.
- CodeQL identified response-header reflection and unrestricted forwarding paths in the auditor's local proxy, not product files. The proxy now emits a constant local CORS origin and uses a literal allowlist of local routes. Product CodeQL policy is unchanged.
- Pending-sale refusal attempts are rolled back after actual native execution so a possible unexpected acceptance cannot deplete the later control fixture. Successful ALLOW_PENDING sale, return and price resolution stay committed and are verified separately.
- Added direct per-size final HPP assertions: M30947.63; L29921.09 known, or26526.54 pending. Labor100 per PCS, wash4321.09 per PCS, finish678.91 on five L only. A conserved total alone is insufficient proof of allocation.
