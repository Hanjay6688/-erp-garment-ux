# Native T3 package — frozen BA, audit run 36126474798

Run: https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36126474798; audit trigger `6699fc32261a04e9366938cf3dbc8e60c7c1a866`; writer/tool head `d1bc8adff3ba1a2a7001ef39e4819d0c3813d00b`, run_identity product_ref `61d88ee5224b2fb2da2af6f4df214fbaacf9f161`. Workflow SHA256 `a818b5eeb95796e9b7878767a192e589fbccffcf74f1a6d6e288b6d3c96992b7`. All 3 jobs completed SUCCESS on disposable AB aligned clones; no hosted write. This is **T3_PREP reproduction**, release_evidence=false, production_go=false. Writer's BB `72bf53f8d808e18fd3e2866491f28667c1b6193d` appeared afterward; **this run does not cover BB**.

| Job and artifact | Native verdict | Material checks |
|---|---|---|
| install `108043639348`, artifact `10860235932` | ALL_STAGES_INSTALLED | 25/25 file PASS; gate installed/primary_unchanged/backup_restore_drill/security_advisors all true; Auth users after0 |
| pin capture `108043639585`, artifact `10859833935` | ALL_STAGES_INSTALLED | 25/25 capture PASS, pins reproduced equal=true differ=[], same gate four true; Auth after0 |
| browser `108043639625`, artifact `10860240960` | BROWSER_PASS | 25/25 installed; real browser cases 10/10 PASS, console_errors0, rest_remaining=false; gate installed/primary_unchanged true; Auth after0 |

**25 package keys, per file (install/capture):**

| File | Install / capture |
|---|---|
| `AC` | `PASS` / `PASS` |
| `AD` | `PASS` / `PASS` |
| `AE` | `PASS` / `PASS` |
| `AF` | `PASS` / `PASS` |
| `AG` | `PASS` / `PASS` |
| `AH` | `PASS` / `PASS` |
| `AI` | `PASS` / `PASS` |
| `AJ` | `PASS` / `PASS` |
| `AK` | `PASS` / `PASS` |
| `AL` | `PASS` / `PASS` |
| `AM` | `PASS` / `PASS` |
| `AN` | `PASS` / `PASS` |
| `AO` | `PASS` / `PASS` |
| `AP` | `PASS` / `PASS` |
| `AQ` | `PASS` / `PASS` |
| `AR` | `PASS` / `PASS` |
| `AS` | `PASS` / `PASS` |
| `AT` | `PASS` / `PASS` |
| `AU` | `PASS` / `PASS` |
| `AV` | `PASS` / `PASS` |
| `AW` | `PASS` / `PASS` |
| `AX` | `PASS` / `PASS` |
| `AY` | `PASS` / `PASS` |
| `AZ` | `PASS` / `PASS` |
| `BA` | `PASS` / `PASS` |

**Browser flow, per case:**

| ID | Status |
|---|---|
| `REAL_LOGIN_PAGE` | `PASS` |
| `ANONYMOUS_REFUSED` | `PASS` |
| `REAL_PASSWORD_BROWSER_LOGIN` | `PASS` |
| `AMBIGUOUS_REFUSED_0` | `PASS` |
| `LOST_REPLY_RELOAD_EXACT_REPLAY` | `PASS` |
| `EXACT_BRAND_STOCK_HPP_0` | `PASS` |
| `LINKED_INVERSE_0` | `PASS` |
| `AMBIGUOUS_REFUSED_1` | `PASS` |
| `EXACT_BRAND_STOCK_HPP_1` | `PASS` |
| `LINKED_INVERSE_1` | `PASS` |

Pin comparison `T3_PINS_REPRODUCED.equal=true,differ=[]`. Restore drill `RESTORED_SAME_MEANING`; dump exit0, pg_restore exit1 because **19 documented pg_cron extension/schema errors**, all 19 reported and explained, catalog/data meaning and engine answer equal. This is the runner's drill criterion, **not byte-for-byte no-error restore**. Security advisor before73/after129, added 56 INFO `rls_enabled_no_policy` in erp (no higher-severity entries in added list), status REVIEW_REQUIRED; native security_advisors gate true. Read-only baseline data checks UUID CLEAN across 765 uuid columns and CASH_BANK aliases NONE; this is **not a hosted/legacy inspection**. All three primary_unchanged=true, Auth users0, supabase stop completed.

**Next:** run the already pinned rollback workflow as its own phase after this ledger commit. The 75 C6 +22 ALL cases on new BB–BE and formal owner C6 remain HOLD/UNVERIFIED; no CP6 release acceptance from this T3 success.
