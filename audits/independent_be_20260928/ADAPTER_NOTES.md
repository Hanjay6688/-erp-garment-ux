# Independent BE adapter boundary

Own BD suite/daily construction helpers are reused; no writer or peer tests run.
Only `native.py` orchestrates BE assertions. Helper main functions are not called.
The first suite tests no-accessory conversion at the frozen 1,234.57 unit source
value. Separate actual accessory use should add 115.85, for target 6,288.70 and
combined garment value 16,165.26 before any separately supported service fee.
An arbitrary `conversion_cost_total` field must not become unsupported cost.
No generic service-fee route is presumed to exist. Its availability remains an
acceptance question, separate from source-cost conservation.

All fixture masters and roles are created in the disposable clone. Public commands
connect as authenticator/authenticated with distinct real ERP actors. PostgreSQL
readbacks verify values directly. No native product security guard is disabled.
