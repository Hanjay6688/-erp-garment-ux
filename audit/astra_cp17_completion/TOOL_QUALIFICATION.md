# Astra tool qualifications — all original attempts retained

Frozen product and original case IDs/oracles remain unchanged. This document records tool defects, not product failures.

- First matrix/retained attempt: run 38791612672, control c839a3c51a4511342d0ce46e8adc5202401a2b4b. All four jobs failed before Python or any case. Destination `auditor/audit` did not exist, so cp renamed the copied directory to `audit`; the declared probe path was absent. Full logs retained.
- One allowed identical-scope pre-case retry: run 38792368517, control adc91c0f47ffd8d0ec877767c3016953b5535076. The inserted newline was inside a YAML quoted multiline string and folded into a space. The parsed command became `mkdir -p ../auditor/audit cp -R ...`; mkdir rejected option R. All affected jobs have zero cases. This attempt is INCOMPLETE/TOOL_ERROR and is closed, not credited as a product pass.
- The new integration workflow at aae283cfb9a492d68abcbbfcd6b251cec0514c69 inherited that same parsed-command defect (run 38792810239). It is preserved as the first qualification attempt for its two predeclared IDs.
- Tool correction qualification under Pro Max §16.2: set the run field as a parsed string with four explicit command newlines, serialize YAML, read it back and compare exact strings, run bash -n, and execute the copy path against a temporary synthetic directory with a dummy Python probe. Both workflows passed that LOCAL_QUALIFIED check. No product file, case ID, data, seed, timeout, assertion, expected result, permission gate, or branch pin changed. This is not an identical rerun to search for green.

The first two attempts remain part of the final receipt; this qualification cannot erase them. The run's acceptance is determined from actual per-case output and restoration gates, not workflow color. Candidate stays dfab13bf62398a69a02bf6221c06d29075e5e40b.
