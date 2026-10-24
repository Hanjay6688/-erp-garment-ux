# Explicit second-customer successor for real Auth return2

The first run c52f3923 (40084287050, artifact12557000872) stopped both cases at
SECOND_FIXTURE_CUSTOMER_REQUIRED before quote or settlement. Fresh aligned copies
contain no second customer. Both original cases and their result remain frozen.

This successor creates a distinct active customer using the unchanged Native
master-data fixture, then runs every original money, stock, receipt, replay,
authority and inverse assertion unchanged. No product, permission or oracle
change. Real Auth users and copy are removed; full composed source preuse inverse
and CP6/advisor proof remain mandatory. production_go=false; no audit acceptance.
