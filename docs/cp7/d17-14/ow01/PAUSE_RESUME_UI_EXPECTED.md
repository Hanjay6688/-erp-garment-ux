# Expected before DOM execution — paused accessory notices

Add exactly two DOM tests to the writer's current 25-test reminder file. Keep
all existing test declarations and assertions. The only source changes in this
proposal are test fixtures and tests; product changes remain with the writer.
The source contract is `PAUSE_RESUME_EXPECTED.md`: new ACCESSORY_NEED notices
retain their waiting episode while disabled, and queued repeats honor the
current repeat setting. A scheduled digest remains independent of instant
repeat timing.

| ID | Expected result |
| --- | --- |
| OW01_UI_10_PAUSED_FIRST_NOTICE | In the actual System Reminders rows, both PENDING and HELD_QUIET first notices explain WA_OFF, PHONE_MISSING, KEY_MISSING, NOT_CONFIGURED and KIND_OFF as a pause. They do not claim a repeat or hide the pause behind quiet hours. The review still says the additional need is unknown and gross186 is assumed BOM need. A fresh read of the same row IDs/episode/round with the pause reason removed shows current waiting or quiet status, and performs no write. |
| OW01_UI_11_REPEAT_WAIT_AND_DELIVERY_STATES | REPEAT_OFF and REPEAT_NOT_DUE have explicit waiting labels for both waiting states. Ordinary first waiting and an unproven recheck do not claim a resend. An actual first-round provider refusal, connection failure or owner NOT_DELIVERED decision still says it is waiting to resend; ordinary round1 waiting remains a repeat. ACCEPTED round0/round1, UNKNOWN and DISPATCHED retain their actual delivery state even if a stale pause reason is present. Legacy terminal KIND_OFF/DISABLED labels remain unchanged. |

These are DOM controls over typed public read replies. They do not prove SQL
eligibility, server history, scheduled digest coverage, provider delivery or
source rechecks. Native sender tests and race evidence remain separate. No
pass result is asserted here; execution logs are recorded after this document.
