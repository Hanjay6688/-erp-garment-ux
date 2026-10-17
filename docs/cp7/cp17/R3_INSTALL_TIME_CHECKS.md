# r3 checks that belong to installation time (not run on hosted now)

The r3 screens are tested on disposable copies only. Some facts can only be confirmed on the real Enteng database, so
they are listed here to run **when CP7 is installed** (CP7C, still held by D13-9a). They are not owner tasks and were
not run on hosted: the writer does not touch hosted (D13-9a), and agents' suggested SQL is never run against hosted.

| Screen | What to confirm at install | How | If it fails |
|---|---|---|---|
| Audit Trail (`cp7_audit_bundle.verify`) | `erp.audit_logs` column types (id bigint/integer, entity_id uuid/text, changed_by uuid, old/new jsonb, changed_at timestamptz), unique index on `id`, sequence cache 1 | Runs by itself inside the install's `verify()`; the install stops if it does not hold | The facade is not installed; nothing else changes |
| Riwayat Pelanggan | Every cancelled or reversed sales document has its Native audit row (the history needs its cancellation time) | The read-only query below, run as part of the install preflight; expected 0 in each row | The screen says in words that this customer's history cannot be read completely ("Riwayat pelanggan ini belum bisa dibaca lengkap ...") and shows no figures; no data is changed |
| Ringkasan Gudang | Column names it reads (`erp.locations.location_code`, `erp.fabric_master_profiles.minimum_stock_qty`, `erp.material_purchase_headers.status`) exist on Enteng | One read-only call of `erp_cp7_get_warehouse_summary_v1` as OWNER right after install (the facade is plpgsql, so column names are checked only when it runs, not when it is created) | The screen shows an error and no figures; no data is changed; the layer can be uninstalled |
| All new facades | Supabase advisors after install show no new warning for the r3 roles and functions | The install's advisor gate, as for every earlier CP7 layer | Uninstall drops each role with `drop owned by ... cascade` |

Riwayat Pelanggan preflight (read only):

```sql
select 'sales_headers',count(*) from erp.sales_headers h where h.status in('CANCELLED','REVERSED') and not exists(select 1 from erp.audit_logs a where a.entity_type='sales_headers' and a.entity_id=h.id and a.action='UPDATE' and a.new_data->>'status'=h.status)
union all select 'sales_payments',count(*) from erp.sales_payments p where p.status='REVERSED' and not exists(select 1 from erp.audit_logs a where a.entity_type='sales_payments' and a.entity_id=p.id and a.action='UPDATE' and a.new_data->>'status'='REVERSED')
union all select 'sales_returns',count(*) from erp.sales_returns r where r.status='REVERSED' and not exists(select 1 from erp.audit_logs a where a.entity_type='sales_returns' and a.entity_id=r.id and a.action='UPDATE' and a.new_data->>'status'='REVERSED');
```
