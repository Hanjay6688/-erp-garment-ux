# CP6 continuation: accepted owner choices, 22 September 2026

Incoming product checkpoint: c6b0e4fb119c4e91fecea66ebf2d789426b22c2b,
tree b14b6ed3cf686eba34f68883ae4129ebba132a2b. Single writer, competition branch,
fast-forward only. CP6_HOLD; independent acceptance pending; production_go:false.

The owner explicitly chose invoice date for corrections in an open period and
manual retail price entry. On the next exchange the owner approved the proposed
complete initial-data import scope and asked work to continue without repeating
these questions until a substantial verified checkpoint.

Accepted scope:

- ERP-DEC01: use invoice date for the open-period correction family, including
  material cost, WIP, FG, COGS, journals, dated reports, and readiness. Preserve
  existing controlled closed-period adjustments and immutable filed snapshots.
- ACC-DEC02: exact physical PCS independent of the price basis. Retail price is
  entered manually as a valid monetary number. No forced fraction of a dozen,
  invented new rounding rule, or rewriting of posted historical prices.
- ERP-DEC03 / AUD-G08: templates and real upload/preview/draft/finalization for
  required initial masters, physical opening stock and valuation, cash and party
  balances, and outstanding operational documents. This includes materials,
  products/model/size, suppliers, customers, contractors, laundry vendors,
  locations, accounts; fabric rolls/accessories/FG/BS/WIP; receivables, payables,
  advances; open orders, uninvoiced receipts, and partly settled invoices.
  Map each item to the existing domain contract before extending it. A posted
  opening document and its supporting detail must never double-count the same
  money or physical quantity. The owner did not authorize invented historical
  transactions or automatic approval of unknown source values.

Drafts remain editable until finalization. All submitted data must be checked
again under the finalization lock, errors identify rows/fields, retry must not
duplicate data, and authorization remains authoritative on the server.

AO covers invoice-date/retail behavior; AP covers the connected initial-import
family. Names describe work in progress, not acceptance. Old migrations, old
test outcomes, and failed attempts remain immutable. Focused checks during
development; one combined affected-family gate after the product stabilizes.

The workbench workflow packages public database/CLI binaries for an isolated
local scratch database so iteration does not require a complete remote gate
after every edit. No live database is exported or contacted. Local experiments
do not replace the pinned Supabase runtime gate, rollback, cleanup, or CodeQL.

No product implementation or new test PASS is claimed by this initial record.

VENI. VIDI. VICI. ERP. — I CONQUERED ERP.
Reliable data adalah dewa.
Keuangan—termasuk laporan—stok, dan HPP adalah raja.
