"""Apply the S06 routing change above the installed P21 alert module.

The caller owns installation, commit and recovery. The frozen WA source also
serves as the expected predecessor, so retained P21 evidence keeps its pins.
"""

from hashlib import sha256
from pathlib import Path
import re


SOURCE = Path(__file__).resolve().parent / 'cp7-src/alerts/alerts.sql'
SOURCE_SHA256 = '219adb738c65aa56301b4befd266e76da29f0c46db3dba2cc9b97ee4fb214410'
CHANGES = {
    'queue_manual(uuid)': (
        ("where r.owner_user_id=p_owner and r.status='OPEN'and r.due_at<=clock_timestamp()",
         "where p_owner=(cp7_alert_native.current_settings()).actor_user_id\n"
         "   and r.status='OPEN'and r.due_at<=clock_timestamp()"),
    ),
    'waiting_eligible(cp7_alert_native.outbox,cp7_alert_native.settings,timestamp with time zone,boolean)': (
        ("o.alert_kind=any(s.kinds)and(p_digest",
         "o.alert_kind=any(s.kinds)\n"
         "  and(o.item_kind<>'MANUAL_REMINDER'or exists(\n"
         "   select 1 from erp.manual_reminders r where r.id=o.item_id and r.status='OPEN'\n"
         "    and r.due_at<=p_at and cp7_alert_native.ts_key(r.due_at)=o.item_episode))\n"
         "  and(p_digest"),
    ),
    'send_tick()': (
        ("when r.id is null then'REMINDER_MISSING'when r.owner_user_id<>s.actor_user_id then'REMINDER_NOT_OWNER'",
         "when r.id is null then'REMINDER_MISSING'"),
        ("and(r.id is null or r.owner_user_id<>s.actor_user_id or r.status<>'OPEN'",
         "and(r.id is null or r.status<>'OPEN'"),
        ("where'MANUAL_REMINDER'=any(s.kinds)and r.owner_user_id=s.actor_user_id and r.status='OPEN'",
         "where'MANUAL_REMINDER'=any(s.kinds)and r.status='OPEN'"),
    ),
}


def expected_bodies():
    raw = SOURCE.read_bytes()
    if sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError('CP7_S06_PREDECESSOR_SOURCE_CHANGED')
    source = raw.decode()
    bodies = {}
    for signature, edits in CHANGES.items():
        name = signature.split('(', 1)[0]
        match = re.search(r'(?ms)^create function cp7_alert_native\.' + re.escape(name) + r'\([^\n]*\n'
                          r'[^\n]*as \$\$(.*?)\$\$;', source)
        if not match:
            raise ValueError('CP7_S06_PREDECESSOR_BODY_MISSING: ' + signature)
        original = patched = match[1]
        for before, after in edits:
            if patched.count(before) != 1:
                raise ValueError('CP7_S06_PREDECESSOR_ANCHOR_CHANGED: ' + signature)
            patched = patched.replace(before, after, 1)
        bodies['cp7_alert_native.' + signature] = (original, patched)
    return bodies


def catalogue(cur, signatures):
    result = {}
    for signature in signatures:
        row = cur.execute("""select p.prosrc, pg_get_functiondef(p.oid), to_jsonb(p)-'prosrc',
                            pg_get_userbyid(p.proowner), p.prosecdef
                           from pg_proc p where p.oid=to_regprocedure(%s)""", (signature,)).fetchone()
        if row is None or row[3:] != ('cp7_alert', True):
            raise ValueError('CP7_S06_ALERT_AUTHORITY_CHANGED: ' + signature)
        result[signature] = row
    return result


def install(cur):
    if cur.connection.autocommit:
        raise ValueError('CP7_S06_CALLER_TRANSACTION_REQUIRED')
    bodies = expected_bodies()
    # Keep the upgrade atomic with respect to active collector, sender and settings writes.
    for operation in ('CP7:WA:SEND', 'CP7:ALERT:COLLECT', 'CP7:WA:SETTINGS'):
        cur.execute('select pg_advisory_xact_lock(hashtextextended(%s,0))', (operation,))
    with cur.connection.transaction():
        before = catalogue(cur, bodies)
        if all(before[sig][0] == patched for sig, (_, patched) in bodies.items()):
            return dict(status='ALREADY_INSTALLED', changed_functions=list(bodies))
        if any(before[sig][0] != original for sig, (original, _) in bodies.items()):
            raise ValueError('CP7_S06_EXACT_INSTALLED_P21_ALERTS_REQUIRED')
        for signature, (original, patched) in bodies.items():
            definition = before[signature][1]
            if definition.count(original) != 1:
                raise ValueError('CP7_S06_INSTALLED_DEFINITION_CHANGED: ' + signature)
            cur.execute(definition.replace(original, patched, 1), prepare=False)
        after = catalogue(cur, bodies)
        for signature, (_, patched) in bodies.items():
            if after[signature][0] != patched or after[signature][2:] != before[signature][2:]:
                raise ValueError('CP7_S06_FUNCTION_IDENTITY_OR_GRANTS_CHANGED: ' + signature)
    return dict(status='INSTALLED', changed_functions=list(bodies), predecessor_sha256=SOURCE_SHA256)
