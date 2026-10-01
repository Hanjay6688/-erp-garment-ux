# F03 independent evidence

The final decision and scope are in `ACCEPTANCE.json`. `runtime/INDEX.json` binds
each original workflow artifact, download SHA256, probe source and exact raw
report hash. The independent new checks and retained reruns are separate.

Each `runtime/*.json.gz` decompresses into a JSON object mapping original
filenames to their exact original JSON text. Parse a string value as JSON to
inspect a report; write that string unchanged to reproduce the original file
hash. Initial incomplete runs remain in `own_first` and `journeys_first`.
They are not included in the final passing execution counts.

`visual/` retains two original independent browser PNGs and the exact list/hash
of sixteen selected screenshots visually inspected. The remaining screenshots
are available in their workflow artifacts while GitHub retains them.

The local receipt and logs beside this file predate the runtime completion and
remain unchanged. They do not claim native execution or override the final
source-bound acceptance.
