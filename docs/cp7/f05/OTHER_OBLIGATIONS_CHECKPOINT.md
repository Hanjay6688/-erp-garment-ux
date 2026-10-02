# Other Native obligations — implementation checkpoint, not acceptance

The active integration candidate remains `bb9a34d6d5801ee587cfcb7c005dc0da4c542d30`: fixed Native 247 cases, with no external delivery. This checkpoint preserves the unfinished private reader in `scripts/cp7-src/reminders/other-obligation-source.sql`. The file is not in the installer and has no public facade. It has not passed Native installation or qualification.

The reader must copy accepted Native balances rather than add a second money formula. Recorded due dates remain unknown when Native has none. Opening balances retain one canonical identity; payroll uses the accepted E05 installment reader; laundry uses the accepted BD documents and ledger reconciliation. Laundry receipts awaiting an invoice still need composition.

Accessory return carry needs particular care: `bc_carry_remaining_v1` measures the amount available for allocation to payroll, including unpaid payroll allocations. Its zero is not a payment. The draft keeps the unpaid balance unknown until accepted Native payment evidence proves the entitlement settled. Partial installments must not be attributed to a particular carry without a Native allocation proof.

Before integration: verify all accepted function and table fields; declare the exact private read role and ACLs; compose the source into the same statement snapshot; extend the typed DTO without fabricated revisions; recheck the current payroll, accessory, laundry and financial rights on every cached result and lock-wait continuation; retain inactive documents for suppression; qualify actual Native transitions, concurrency, HTTP and desktop/mobile flows. No claim of full F04/F05 acceptance, production go, or external delivery follows from this checkpoint.

VENI. VIDI. VICI. ERP. Reliable data adalah dewa. Keuangan—termasuk laporan—stok, dan HPP adalah raja.
