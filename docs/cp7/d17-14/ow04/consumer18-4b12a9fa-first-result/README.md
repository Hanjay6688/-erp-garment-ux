# First actual consumer18 result —16 PASS /2 INCOMPLETE, retained

Candidate `4b12a9fab45c4fad5dbfc6bf9087b4c7604c6bab`, tree
`182969e7d0d992895a0a55fcf05220160c2358e4`.
[Run39650695392](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/39650695392),
job119397924771, workflow failure. Actual qualifier INCOMPLETE, not PASS.
All18 cases observed; exact CP6 restoration and advisor gate passed.

Original consumer9 all passed, including the actual bound unsafe Native payment
correction refusal (I0/C200/balance-200 at D2 despite currentC0). The first7
new REFUND cases passed. The2 initial-full-refund UNDO cases stopped at quote
with `CP7_CREDIT_CONSUMER_UNDO_BEFORE_ORIGINAL_PHYSICAL`.

The product guard correctly refused the test input. The initial cash event is
explicitly13:00:00.654321 at D2; the shared test helper incorrectly used the source
return's12:00 clock plus5min for its UNDO. Correct the fixture to capture the
actual immutable initial-refund physical time and construct the later UNDO from
that time. Original monetary expectations and economic/book dates stay exact;
no product SQL, physical-order guard, source pin or refusal code is relaxed.
Both cases remain mandatory and the overall gate remains18/18.

Artifact12369328123 ZIP2070948bytes client SHA256
`c1d5306f65b2418c7ec31a4cbe68832aedbb3ea99d9ae8e20c04fe2a6c1e7525`.
Main original report4448950bytes SHA256
`af103af7c93bc594304787aee11e57859611134df6aaf34f3f31163a96235301`.
All5 original JSON byte streams retained unchanged gzip with extraction receipt.
Original logs also retained in session store `consumer18FirstResult_1`.

No whole-OW04, general successful-correction, new real Auth/HTTP/browser/race,
independent acceptance, production or CP7C claim follows from this result.
