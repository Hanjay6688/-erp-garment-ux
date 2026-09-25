# GPT C0 independent oracle freeze — 25 September 2026
Tool9dd7bc2/producta095a9d; AUDITOR_SCENARIO, no release acceptance. C0 SHA256 e83d56e66812011c9a7a4057bf29987d0bcf62aabc17ad23ab422170abb00c99; sections1–8 identical to approved d39762da… precursor. Ratification provenance is the owner's supplied writer handoff and preserved §9 quotation; external chat was not separately obtained. D06 is excluded.

Scenario `audit/scenarios/c0_round8/gpt_c0_oracles.py` SHA256 7c2c19b6e722d325ba902cfd9eb1ae2f98d4e2ec27245070ab485df0af9e66a7. Frozen before runtime. 25 unique planned IDs: 8 DATE:False:{Asia/Jakarta,UTC,Etc/GMT+12,Pacific/Kiritimati}:True:{20,20.003}; 12 CALENDAR:{1_MONTHS,2_MONTHS,3_MONTHS,JAN31,FEB28,MAY31}:{UTC,Pacific/Kiritimati}:False; 4 AO:INVOICE:{UTC,Pacific/Kiritimati}:{False,True}; AS:ADJUSTMENT_DATE:False. New IDs have G8C0 prefix; raw historical12HOLD and original cases remain unchanged.

## Oracle / contract
C0 D01.1 supplier invoice at economic E (exception before receipt not exercised). D01.2 each correction part at max(E,physical stage), D01.3 adjustment at max(E,A); D01.4 closedE economicE/booktoday; D01.5 reports by prefix. M3816,3818,3820,3825 and M6632 apply.
Three independent readings per prefix: raw posted/reversed journals, account_daily_balances, public owner financial report. Only fixture/command helpers reused from writer; no writer assertion functions. Source originals are not patched.

| Fixture | At receipt day E, before cutting | At goods day G (cut/FG/sale) |
|---|---|---|
| AS20 | Material200,AP−200; WIP/FG/COGS0 | Material0,WIP135,FG81,COGS54 |
| AS20.003 | Material200.03,AP−200.03; WIP/FG/COGS0 | Material0,WIP135.01,FG81.01,COGS54.01 |
| First partial3×8.25 | Material94.75,AP−24.75,GRNI−70 | Material0,WIP82.37,FG49.43,COGS32.95 |
| Final plus7×11.75 | Material107,AP−107,GRNI0 | Material0,WIP88.50,FG53.10,COGS35.40 |
| Adjustment−2 | Material200.03,expense0 | On A: qty8,material160.02,expense40.01 |

Laundry is70, zero sewing wage, fiveWIP/threeFG/two sold. Each document rounds to cents. WIP is total minus rounded completed cost, not an independently rounded half. Closed cases retain old book balances until recognitiontoday; old filing contents stay identical. Flag observations are retained separately; these 25 cases alone do not close all close/report gates. Invoice exact-replay, dates, rawquantity0,FGquantity3,contextcleared,queueDONE checked. Adjustment linked inverse today restores material80/expense20/GRNI100/AP0 while prior dates retain corrected history.

## Cross-review of Fable draft
Read `out/fable_t2_oracles_post_addendum.md` as a peer hypothesis, not authority. Clarifications:
- “Material always0” is valid only after consumption, not as-of receiptE; the oracle must observe both.
- First partial WIP is82.37 exactly, not82.37/82.38; FG49.43+COGS32.95 leave82.37 from164.75.
- D01.1 fixes the supplier invoice journal's E. It does not force every derived open-period fact's economic_date to E; D01.2/3 explicitly date the value part at max(E,A). Check fact/economic/book=A for this open adjustment; closed branch usesE/E/today as specified.
- Reclassification is a new dated oracle outcome, not a retroactive edit of the old 12HOLD.

## Runtime plan
Single job next phase in audit-owned workflow. Candidate product untouched; local disposable Supabase only. Planned calls may be INCOMPLETE if a legitimate fixture cannot be prepared; no fixture exception is PASS. Record run/jobIDs immediately, then per-case logs and cleanup. Re-review any counterexample against the literal C0 before promoting.
