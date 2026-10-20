# Expected before DOM execution — ACCESSORY_NEED

Proposal target: `src/ConnectedRemindersWa.dom.test.tsx` in the writer worktree
at f412e61be645b974ecca27862501b8e5b6e0c2ab plus the writer's current
ACCESSORY_NEED frontend changes. This proposal changes tests only. The original
16 test declarations and their money, quantity, label, permission, secret,
request UUID and replay assertions remain; the two existing settings arrays and
the checkbox-label array gain the new authorized kind.

The new detail fixture has exactly 20 raw keys. It is constructed from a deep
clone of `alertsReply('OWNER')`, so adding a source or updating analysis status
cannot mutate the shared `kindsOwner` or `analysisStatus` fixtures.

| ID | Expected result |
| --- | --- |
| OW01_UI_01_SETTINGS_ROUNDTRIP | The real checkbox is on in the fixture's current defaults. Save includes ACCESSORY_NEED; turning it off survives a lost reply and exact UUID/payload retry; turning it back on uses a fresh UUID and the next revision. Other kinds remain unchanged. The automatic-analysis caption includes accessories. |
| OW01_UI_02_GROSS_REVIEW | The actual System Reminders row says the additional quantity is unknown, names the category, labels gross186 as an assumed BOM need, shows analysis and recheck times and pending WA state, and never calls gross a purchase or known additional quantity. The review remains open and the analysis caption includes accessories. |
| OW01_UI_03_BOM_NOT_RECORDED | A source-complete UNKNOWN_BOM row explains that the accessory BOM has not been recorded, with no invented gross or additional zero. |
| OW01_UI_04_BOM_AMBIGUOUS | A source-complete UNKNOWN_BOM row explains overlapping BOMs, with no invented gross or purchase quantity. |
| OW01_UI_05_CATEGORY_UNAVAILABLE | An unavailable category retains its category identity and explains that it is unavailable; both gross and external quantities stay unknown. |
| OW01_UI_06_HTTP_401_RETIRE | After a successful review read, an HTTP401 response removes the old row, gross, analysis time and row WA state although the AuthProvider still says AUTHORIZED. No write is attempted. |
| OW01_UI_07_HTTP_403_RETIRE | The same retirement holds for HTTP403 and the permission error is shown. |
| OW01_UI_08_LATE_401 | A delayed success from the old identity generation cannot restore its review facts after an identity revision remount and a newer HTTP401 refusal. |
| OW01_UI_09_LATE_403 | The same old-generation isolation holds after a newer HTTP403 refusal. |

The late-result controls use the public identity-revision remount path. They do
not manufacture a second refresh through the disabled refresh button, and they
do not claim a concurrent read race within one unchanged component instance.

DOM scope only: these controls do not prove Native capture completeness,
post-lock source rechecks, physical installation, policy eligibility, provider
delivery or a full WIP freeze. The existing Native WA65 cases remain required.

No result is asserted in this expected document. Test logs and source
fingerprints are recorded separately after execution.
