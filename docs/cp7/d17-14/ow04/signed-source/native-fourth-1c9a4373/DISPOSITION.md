# Actual OID JSON representation, first owner correction

Run39552633770/job119065066879 at1c9a4373 stopped before all63 cases.
The new diagnostic confirmed the actual built-in owner `supabase_admin` and
bootstrap OID10, but PostgreSQL `jsonb` encoded that OID as the string `"10"`.
The synthetic model used the integer10; the additional strict Python type
comparison introduced in the first owner correction therefore rejected the
valid platform row. Original log, parsed failure and metadata are retained.

The fix compares the canonical textual value exactly to `10`, accepting JSON
integer10 and the actual OID string while refusing `010`,10.0,boolean,true,
unknown owners and another OID. All prior owner/language/security/arguments/
entry point/FK/RI/transition checks remain. No role, ACL or database object is
changed, no money/date/stock/HPP expected changed, and no case is relabelled.
22pure controls reproduce both earlier refusals and verify the correction.
They do not replace the real Native63 rerun.

The local9318a0c7 and GitHub1c9a4373 commits have identical tree
ccc59b55cf8d919ce87a33de3cf8b92bd23f4dd5. The connected GitHub API created
the latter when native git lacked authentication; local writer HEAD was then
aligned to that exact remote commit without changing files or pending work.
Candidate audit55c885d1 and main remain unchanged; production_go=false.
