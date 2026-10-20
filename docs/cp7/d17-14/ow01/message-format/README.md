# Literal message-format counter

This executes actual extracted SQL in isolated in-memory PGlite. It does not run
Native source collection, the real provider, Auth, PostgREST, or production. No
active repository file was edited. It adds zero Native/provider case claims.

`EXPECTED.json` was frozen before the runner and product formatter change at
SHA256 `77e6dc2c7310f6f3c1908e8132cc33ea093910630520c9da616cc2374dcaa7f1`.
All ten cases were declared first. The same literal expected is used before and
after; no fixture label, source detail/ID or numeric oracle was shortened.

- Old actual b65 source: **4 PASS / 6 FAIL**. The 98-character Native LRC label
  plus full UNKNOWN/review suffix is138 characters. Its old observed result
  ends exactly `: nilai belum diketahu`. The known max-cent value is also cut.
- Root's actual fixed source: **10/10 PASS**. It preserves the exact LRC138 and
  max-cent/date148 lines. Overbudget labels alone receive a visible ellipsis;
  complete suffixes survive at256 characters. SUMMARY privacy is unchanged.
- Ten long items produce three complete lines and `dan 7 lainnya`; the full
  message has881 Unicode codepoints and ends `Buka ERP > Reminder`.
- Of the six extracted actual definitions, only `item_line` changed. Actual
  `num`, `rp`, `tgl`, `label` and `render` are unchanged. No settings stub is
  required or installed. Sources and function hashes are in the receipts.

Run from any directory with the existing PGlite module:

```sh
node /workspace/scratch/9442228ed2dc/ow01-proposals/message-format/check_message_format.mjs /workspace/scratch/9442228ed2dc/ow01-proposals/message-format/BEFORE_b65_alerts.sql /workspace/scratch/9442228ed2dc/ow01-proposals/message-format/BEFORE_RECHECK.json
```

The old-source command intentionally exits1 with6 failed controls.

```sh
node /workspace/scratch/9442228ed2dc/ow01-proposals/message-format/check_message_format.mjs /workspace/scratch/9442228ed2dc/ow01-proposals/message-format/AFTER_actual_alerts.sql /workspace/scratch/9442228ed2dc/ow01-proposals/message-format/AFTER_RECHECK.json
```

The after-source command exits0 with10 passing controls. To check another actual
candidate, pass its absolute SQL path and a new receipt filename in this proposal
directory. `OW01_PGLITE_MODULE` can point to another installed PGlite module;
the default is the existing `sql-dev/node_modules/@electric-sql/pglite/dist/index.js`.

The runner extracts the six real functions and any real function dependencies;
it does not copy formatter logic into an oracle. Inputs and expected output are
literal frozen JSON. Unknown/private/missing source dependencies fail the harness
instead of receiving an unnamed stub. Before/after receipts and COMPARISON.json
preserve the distinction between intentional old failures and current checks.
