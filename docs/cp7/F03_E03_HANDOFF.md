# F03 E03 — customer-owned service after partial sales return

F03 OPEN; CP6 CLOSED_CONTRACT_SCOPE; production_go=false; independent_acceptance=false. This is a selected E03 branch, not complete cash-refund or full E03 acceptance.

Source `0c35e18723d8aba2f55dbf5231e30d93c5afd453`, tree `fb4ea4365396590a9873ab7df5b388b4318be1fe`, [run36655801222](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36655801222): PENDING. One native, one Auth/HTTP and desktop/mobile browser execution are planned against the explicit26-role F03 stack.

The source is the lawful E01 production/Nota/payroll worksheet: sell20, collect200 and accept5 company GOOD returns, leaving company FG45/value675, AR175 and cash200. One **different** garment among the customer's remaining15 enters custody. It remains customer-owned while two separately received company accessories (10 PCS at2, final invoice basis) are consumed, costing4. The existing owner policy chooses a dedicated disposable service-expense account. The garment returns to its owner; there must be no company FG/HPP, extra sales return, customer AR/refundable credit or contractor entitlement created by custody.

Expected service delta is material inventory−4/service expense+4; accessories10→8; revenue/COGS/gross profit, company FG/HPP, AR and cash unchanged. The native case additionally checks exact replay, wrong-purpose and closed-custody refusals, forged cash/refund fields, and dependency-order inverse. HTTP checks real Auth, anonymous refusal and deactivation before cached replay. Mobile intentionally loses a committed accessory-use response and reconciles the identical envelope after reload. Full source tables are fingerprinted in canonical UTC, preventing timezone spelling from posing as a business mutation.

Browser actions cover custody-in, actual accessory consumption and custody-out. Production/sale/partial return are native fixture setup. The original invoice reference is retained in the existing service reference field; this is not claimed to be a new structural invoice-allocation link. No customer-service quality-grade write is invented. No cash refund is executed because this unpaid-invoice source has no legitimate refundable customer-credit right. A separate eligible-credit/refund and returned-BS contract remains visible rather than converted into an artificial company FG or cash entitlement.

Results, cleanup/restoration and screenshots will be retained after the run; no PASS or visual review is claimed yet.
