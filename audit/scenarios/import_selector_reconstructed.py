"""Reconstructed, NOT_RUN audit scenario for initial-import DRAFT discovery.

The candidate's workspace exposes the latest 50 batches to its only UI selector.
Its public reader can still load a known older batch by UUID. This test checks
that narrower UI-discovery defect with 51 ordinary public CREATE actions. It is
separate from the BS Resolution 101-laundry-source case.

Target: 9add57ea8c2b6b2dc37c0134717d4d39ba30b5dc.
The auditor runner supplies a disposable clone and an outer case transaction;
this case additionally rolls its own fixture back to its entry savepoint.
"""

from datetime import timedelta
import traceback
import uuid

import cp6_aw_probe as awp


api = awp.api
CASE_ID = "XI:C_SEL_01_INITIAL_IMPORT_51_DRAFT_SELECTOR"
PLANNED_CASE_IDS = ("XI:C_SEL_01_INITIAL_IMPORT_51_DRAFT_SELECTOR",)


def _actor(cur):
    """Check the real seeded mapping used by api.call/api.read, not a role label alone."""
    api.admin(cur)
    rows = cur.execute(
        """select u.id::text,u.is_active,r.role_code,r.id::text
           from erp.app_users u join erp.app_roles r on r.id=u.role_id
           where u.auth_user_id=%s""",
        (api.base.OPERATOR_AUTH,),
    ).fetchall()
    if len(rows) != 1 or not rows[0][1] or rows[0][2] not in ("OWNER", "ADMIN"):
        raise AssertionError("INITIAL_IMPORT_AUTHORED_ACTOR_MISSING_OR_AMBIGUOUS")
    permissions = [r[0] for r in cur.execute(
        """select p.permission_key from erp.app_role_permissions rp
           join erp.app_permissions p on p.id=rp.permission_id
           where rp.role_id=%s order by p.permission_key""", (rows[0][3],)
    ).fetchall()]
    return dict(app_user_id=rows[0][0], role=rows[0][2], role_id=rows[0][3],
                permissions=permissions, active=True,
                public_session="authenticated (api.call/api.read)")


def _probe(cur, today):
    actor = _actor(cur)
    prefix = "XI51-" + uuid.uuid4().hex[:12].upper()
    cutover = str(today - timedelta(days=1))
    authored = []
    for n in range(51):
        request_id = uuid.uuid4()
        code = f"{prefix}-{n:02d}"
        result = api.call(cur, "CREATE", dict(batch_code=code, cutover_date=cutover), request_id)
        if (result.get("action") != "CREATE" or result.get("request_id") != str(request_id)
                or result.get("status") != "DRAFT" or not result.get("batch_id")):
            raise AssertionError("INITIAL_IMPORT_CREATE_RESPONSE_NOT_DRAFT_OR_WRONG_REQUEST")
        authored.append(dict(id=str(result["batch_id"]), code=code))

    ids = [r["id"] for r in authored]
    if len(set(ids)) != 51:
        raise AssertionError("INITIAL_IMPORT_CREATED_IDENTITIES_NOT_UNIQUE")
    api.admin(cur)
    # The backend sorts by (created_at DESC,id ASC). In one transaction the
    # timestamps may tie, so infer oldest from the actual sort, not loop order.
    rows = cur.execute(
        """select id::text,batch_code,status,created_at::text
           from erp.migration_batches where id=any(%s::uuid[])
           order by created_at desc,id""",
        (ids,),
    ).fetchall()
    if len(rows) != 51 or any(r[2] != "DRAFT" for r in rows):
        raise AssertionError("INITIAL_IMPORT_51_DRAFTS_NOT_PRESENT")
    ordered = [r[0] for r in rows]
    oldest, newest = ordered[-1], ordered[0]

    # Pre-existing batches may interleave at the same/future timestamp. Compare
    # with the independent global top 50; 51 authored rows guarantee that the
    # last authored row cannot be in that 50 regardless of interleaving.
    all_top = [r[0] for r in cur.execute(
        "select id::text from erp.migration_batches order by created_at desc,id limit 50"
    ).fetchall()]

    workspace = api.read(cur, None)
    recent = workspace.get("recent")
    if not isinstance(recent, list):
        raise AssertionError("INITIAL_IMPORT_RECENT_NOT_ARRAY")
    listed = [str(r["id"]) for r in recent]
    if len(listed) != len(set(listed)):
        raise AssertionError("INITIAL_IMPORT_RECENT_DUPLICATE_ID")

    # Positive control: public facade *can* load a known old UUID, so the
    # finding concerns the UI selector, not server-side by-ID authorization.
    by_id = api.read(cur, oldest)
    batch = by_id.get("batch") or {}
    old_known_id_readable = batch.get("id") == oldest and batch.get("status") == "DRAFT"
    listed_authored = [v for v in listed if v in set(ids)]
    checks = dict(
        created_51_distinct_drafts=len(rows) == 51,
        recent_matches_independent_global_top_50=listed == all_top,
        newest_in_recent=newest in listed,
        some_authored_draft_in_recent=bool(listed_authored),
        oldest_draft_in_database=rows[-1][2] == "DRAFT",
        oldest_absent_from_recent=oldest not in listed,
        oldest_readable_with_known_uuid=old_known_id_readable,
    )
    prerequisites = (checks["created_51_distinct_drafts"]
                     and checks["some_authored_draft_in_recent"] and checks["oldest_draft_in_database"]
                     and checks["oldest_readable_with_known_uuid"])
    if not prerequisites:
        status = "INCOMPLETE"
    elif checks["recent_matches_independent_global_top_50"] and checks["oldest_absent_from_recent"]:
        status = "COUNTEREXAMPLE"
    elif not checks["oldest_absent_from_recent"]:
        status = "PASS"
    else:
        status = "INCOMPLETE"
    return dict(
        status=status,
        checks=checks, actor=actor, create_path="public.erp_save_initial_import_action_v1/CREATE",
        read_path="public.erp_get_initial_import_workspace_v1(p_batch_id)",
        created_count=len(rows), recent_count=len(listed),
        authored_in_recent=len(listed_authored), preexisting_in_recent=len(listed)-len(listed_authored),
        global_top_50_ids=all_top,
        authored_order=ordered, recent_ids=listed,
        oldest_id=oldest, oldest_code=rows[-1][1], newest_id=newest,
        old_by_id_status=batch.get("status"),
        expected=("M:1691/M:3817/M:3826/M:4486: an older editable initial-import "
                  "DRAFT remains discoverable in the UI selector after 51 drafts; "
                  "known-UUID server retrieval is a separate positive control"),
        limitation=("Native public-facade test of the UI's data source, not a browser "
                    "interaction; existing UI renders only recent as select options "
                    "and has no arbitrary-ID/search/paging control."),
    )


def selector_51(cur, today):
    api.admin(cur)
    cur.execute("savepoint xi_initial_import_selector")
    result = None
    authored_ids = []
    try:
        result = _probe(cur, today)
        authored_ids = result.get("authored_order", [])
    except Exception as exc:
        result = dict(status="INCOMPLETE", error=str(exc)[:900],
                      traceback=traceback.format_exc()[-1400:])
    finally:
        # Even if a product call aborts the transaction, this rolls back every
        # fixture row and idempotency event before the outer runner proceeds.
        cur.execute("rollback to savepoint xi_initial_import_selector")
        api.admin(cur)
        if authored_ids:
            count = cur.execute(
                "select count(*) from erp.migration_batches where id=any(%s::uuid[])",
                (authored_ids,),
            ).fetchone()[0]
            if count:
                result = dict(status="INCOMPLETE", error="INITIAL_IMPORT_SELECTOR_ROLLBACK_RESIDUE",
                              residue=count)
        cur.execute("release savepoint xi_initial_import_selector")
    result["fixture_rolled_back_to_savepoint"] = True
    return result


def cases(cur, today):
    return [(PLANNED_CASE_IDS[0], lambda: selector_51(cur, today))]
