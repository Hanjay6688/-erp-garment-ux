# Native source inverse: second product SQL error

Run39556213910 / job119076469335 on99695e103f6ec3c604f38419e65722e08013c02c
executed63 cases:59 PASS and4 INCOMPLETE, with restore and advisor gates passing.
The JSON precedence defect was passed. The same four source-inverse cases then
failed at a later actual product statement with PostgreSQL42702: the SQL alias
`f` collided with the function's declared financial-materialization variable.

The retained-recognition aggregate now uses explicitly named relation and
column aliases. Its numeric sum and all frozen money/date/stock/HPP expectations
are unchanged. The local regression executes the exact extracted statement
in a labelled synthetic PL/pgSQL context: the original reproduces42702 and
seven corrected vectors retain exact signed decimal amounts. All six related
source SQL files are also checked for variable/alias collisions, including the
original finding. None of those checks is a Native lifecycle PASS.

The full original job log is preserved byte-for-byte inside RUNTIME.log.gz.
RECEIPT.json records all63 statuses, the original errors, artifact identity and
raw report hashes. The original report is also retained compressed. A new
Native63 execution on the exact corrected source is required before rebinding
HTTP/race/browser. OW04 remains open and production_go=false.
