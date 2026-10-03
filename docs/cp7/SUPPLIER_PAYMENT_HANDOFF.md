# Supplier payment owning history and inverse

Writer increment, successor of404252fb. First Native50 was INCOMPLETE; the successor retest is declared within Native57. This is payment history and a reviewed inverse, not arbitrary payment editing or a new payment-creation engine. Do not describe it as complete CP7 acceptance.

`SupplierPaymentPanel` is inside the existing connected procurement workspace. An actual supplier-payment journal opens its actual receipt and selects that exact payment, including payment26 on page25. The public reader calculates the child's current page in the database; recovery also supplies the exact original child UUID. No guessed parent, browser scan or first-page substitution is used.

| Boundary | Source and behavior |
|---|---|
| `erp_cp7_get_supplier_payments_v1` | Current receipt/payment FK, current Auth permissions, 25 payments ordered by payment_date/created_at/id; optional exact payment UUID calculates its actual owning page. |
| Outstanding AP | Exact existing `erp_get_supplier_credit_v1` purchase object, including credit delta and payment status. No second AP formula. |
| Review | Original amount, date, cash source and Native journal; own reason and explicit confirmation. Token covers full Native payment/receipt/cash/AP/journal/lines in UTC and restores the caller timezone. |
| `erp_cp7_reverse_supplier_payment_v1` | Immutable current actor/request UUID and exact intent, Native source locks, fresh authority after waits and current review, then unchanged `erp.reverse_supplier_payment` once. |
| Recovery | Lost committed reply retains the identical original UUID and payload across reload. Cached committed outcome is bound to both original intent and Native child. Current rights remain required for replay. |
| History | Original payment date, cash source, original journal and inverse link remain visible. Inverse booking date comes from Native server behavior. |

The worksheet is final AP1000,26 actual Native payments of10, paid260 and remaining740. Inverting the exact26th payment produces paid250 and remaining750; cash changes from-260 to-250 with no stock/HPP change. Native accounting and all original-row checks must prove this; synthetic frontend fixtures are not that proof.

The current candidate declares50 actual controls: the existing41 retained, plus4 supplier DB controls,2 real concurrent schedules,1 current Auth/HTTP journey and2 desktop/mobile journeys. The new schedules observe actual same-request serialization and actual Native payment lock waits before ordinary ADMIN permission revocation. Late outcome-storage failure must roll back every Native financial effect and request record. Desktop drops an actual committed server reply, reloads and reconciles the same UUID; the inverse journal must reopen the same immutable child. All predecessor/restoration/primary/advisor/backup/Auth cleanup gates remain unchanged.

`first4042/RECEIPT.json` retains the preceding Native41 INCOMPLETE Original and full failure diagnostics. Both failures searched literal size31 although Native QC fixture sizes are BF-prefixed. The successor uses the size_code from the same Native response, without changing product QC rules or dropping controls. Shell4042 is separately qualified1374 tests/143 files,6 Shell browsers and zero CodeQL findings.

80 impacted local checks in5 files, build and security pass; the exact source/log hashes are in `evidence/transaction-source/supplier-payment-local/LOCAL_RECEIPT.json`. Fresh Native50 and complete composition qualification remain required. Independent acceptance and installed/production GO remain false. Continue material/P08 and P18/P19 work while qualification runs; the owner continuation remains active.

Native50 at22d0 observed42 PASS/8 INCOMPLETE. All previous41 passed. The actual nonsuperuser postgres helper lacked EXECUTE on private payment_access. The successor grants only access_now/payment_access/payment_ap/payment_detail to that Native locking owner and verifies the exact dependencies; no App ERP DML is added. Full stock/HPP hashes now use UTC and restore the caller timezone across independent fixture connections, preserving every field. Browser failure capture preserves the original assertion even if its observer also fails. Exact first50 Originals: evidence/transaction-source/first22d0/RECEIPT.json. Shell on22d0 separately passes1386 tests/144 files/6 browsers/zero CodeQL findings. Native57 retains all50 supplier/source controls and adds seven QC-source controls; it remains pending.

First Native57 atfac73 has56 PASS/one authority-fixture INCOMPLETE. All added QC and all14 browser controls pass, including actual committed reply loss/reload exact UUID/payload/version. Supplier Native inverse/atomicity/current-revoke schedules/Auth HTTP also pass. The remaining authority comparator must snapshot AFTER its intentional role regrant, preserving all Native role version/timestamp fields and exact cached receipt equality. Full57 retest remains mandatory. First Original and8 unedited Native images retained at evidence/transaction-source/first57-fac73/RECEIPT.json; no retrospective PASS.
