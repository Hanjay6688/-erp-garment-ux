# Plan errata, retained alongside frozen plan

The initial prose counted transport as11 from its legacy phase name `p19-transport11`. The pre-run frozen `P19_TRANSPORT_PREDECLARED.json` already declares15 (6 Native,3 race,3 HTTP,3 browser), and the candidate runner executes that full declaration. Correct total is396 coverage slots, not392. P19 subtotal40, not36. No manifest ID, product, expected or CI execution was changed to correct this reporting mistake.

First own run39238457513 remains9PASS+2INCOMPLETE. Q2 is a new tool qualification under Pro Max§16.3 for exactly those two IDs. See Q2_PREDECLARED.json and Q2_TOOL_DIFF.patch; the business expecteds, fixture and candidate stay unchanged. Commit8c5c86a384bf32cff26a1946b52d1f6a0c74b613 produced no run because its trigger path had a duplicated q2 suffix; commit2731eb5b53d7bb4b4be6572cacdc3214b914bbd3 corrects that path only and starts39239850748. No job was rerun.
