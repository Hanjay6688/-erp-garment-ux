"""Pure exact-anchor RETURN/source/FG transforms. No DB calls or installer.

Authoritative derivation requires the trusted current installed definition AND
metadata captured before the candidate is transformed. Release hashes below
are static footprints only. They do not establish an installed predecessor.
"""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import argparse
import json
import re

FG = "  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));"
REFUSAL = 'Retur ini membuat pembayaran customer melebihi nilai penjualan tersisa. Nilai setelah retur %, sudah dibayar %. Reverse/koreksi pembayaran customer dulu agar kelebihan bayar tidak hilang dari pembukuan.'


def digest(s):
    return sha256(s.encode()).hexdigest()


def once(body, anchor, replacement):
    if body.count(anchor) != 1:
        raise ValueError('OW04_EXACT_NATIVE_ANCHOR_CHANGED: ' + anchor[:100])
    return body.replace(anchor, replacement, 1)


def before_terminal_end(body, statement):
    for suffix in ('\nend;\n','\nend;','\nend\n','\nend'):
        if body.endswith(suffix):
            return body[:-len(suffix)] + '\n  ' + statement + suffix
    raise ValueError('OW04_EXACT_NATIVE_TERMINAL_CHANGED')


def post_return(body):
    # Native require_internal and its existing FG remain exactly where accepted.
    out = once(body, FG, FG + '\n  perform erp.require_internal();'
        '\n  perform cp7_credit.native_return_enter(p_return_id);\n  perform erp.require_internal();')
    out = once(out, '  if v_paid>v_net_total then',
        '  v_paid:=cp7_credit.native_return_guard(h.id,v_refund,v_net_total,v_paid);\n  if v_paid>v_net_total then')
    out = once(out, "erp.post_journal('SALES_RETURN',h.id,",
        "cp7_credit.post_return_journal('SALES_RETURN',h.id,")
    # Run for both the journal and legitimate journal-free Native branches.
    anchor = "      'Sales return from customer · cumulative exact HPP target',v_lines);\n  end if;"
    out = once(out, anchor, anchor + '\n  perform cp7_credit.flush_opening_return_hpp_v1(h.id);'
        '\n  v_paid:=cp7_credit.native_return_complete(h.id,v_refund,v_net_total);'
        '\n  perform erp.require_internal();')
    out = before_terminal_end(out, 'perform cp7_credit.native_return_leave(h.id);\n  perform erp.require_internal();')
    if body.count(REFUSAL) != out.count(REFUSAL) or body.count(REFUSAL) != 1:
        raise ValueError('OW04_NATIVE_PAID_REFUSAL_MUST_REMAIN_EXACT')
    for guard in ('Sales return must be DRAFT', 'Native sales return must reference the original sale',
                  'Sales return customer does not match original sale customer',
                  'Refund exceeds original net sale value for product'):
        if body.count(guard) != out.count(guard) or not body.count(guard):
            raise ValueError('OW04_NATIVE_RETURN_GUARD_CHANGED')
    return out


def opening_return_status(body):
    # Preserve the accepted trigger's invoker metadata and entire original
    # loop. Only a typed, actually guarded DRAFT->POSTED return can defer it.
    if digest(body) != '5bd16275dc867461f672526766b7ea0f999f8a7ce8a2ab4760a750d02d811a01':
        raise ValueError('OW04_OPENING_RETURN_TRIGGER_PREDECESSOR_CHANGED')
    anchor = '  if new.status is not distinct from old.status then return new; end if;'
    return once(body, anchor, anchor + '\n  if cp7_credit.defer_opening_return_hpp_v1(new.id,old.status::text,new.status::text)then return new;end if;')


def post_payment(body):
    out = once(body, '  perform erp.require_internal();',
        '  perform erp.require_internal();\n' + FG + '\n  perform erp.require_internal();'
        "\n  perform cp7_credit.native_source_enter('PAYMENT',p_payment_id);\n  perform erp.require_internal();")
    out = once(out, '  if v_paid>=v_total then',
        '  v_paid:=cp7_credit.current_effective_paid(h.id);\n  if v_paid>=v_total then')
    out = once(out, '  v_paid:=v_paid+v_amount;',
        '  v_paid:=cp7_credit.current_effective_paid(h.id);')
    # The Native payment row is already POSTED at the amount calculation,
    # but the invoice status is updated afterward. Complete the source only
    # after that original header/audit tail, never at the intermediate state.
    out = before_terminal_end(out, "perform cp7_credit.native_source_complete('PAYMENT',p_payment_id);"
        '\n  perform erp.require_internal();')
    return out


def reverse_payment(body):
    out = once(body, '  perform erp.require_owner_admin();',
        '  perform erp.require_owner_admin();\n' + FG + '\n  perform erp.require_owner_admin();'
        "\n  perform cp7_credit.native_source_enter('PAYMENT_REVERSE',p_payment_id);\n  perform erp.require_owner_admin();")
    out = once(out, '  if v_paid>v_total then',
        '  v_paid:=cp7_credit.current_effective_paid(h.id);\n  if v_paid>v_total then')
    out = before_terminal_end(out, "perform cp7_credit.native_source_complete('PAYMENT_REVERSE',p_payment_id);"
        '\n  perform erp.require_owner_admin();')
    return out


def prepayment_helper(body):
    # Latest20ba, not the old20ap precursor. This hook precedes its existing
    # payment/header/advance lock and preserves the20ba dated-capacity check.
    anchor = ' perform erp.require_owner_admin();'
    out = once(body, anchor, anchor + '\n perform cp7_credit.prepayment_entry(false);')
    dated = ' if erp.initial_prepayment_dated_floor_v1(a.id,v_date)<0 then'
    if body.count(dated) != 1 or out.count(dated) != 1:
        raise ValueError('OW04_LATEST20BA_DATED_FLOOR_REQUIRED')
    return out


def prepayment_outer(body):
    # Latest20bb. BEFORE its idempotency/batch locks, alongside existing FG-first
    # FINALIZE/WIP_OUTPUT/OPENING_RETURN admission. No unshared party probe.
    anchor = " if v_action='WIP_OUTPUT' then perform erp.pocket_period_lock_v1();end if;"
    out = once(body, anchor, anchor + "\n if v_action='PREPAYMENT'then perform cp7_credit.prepayment_entry(true);end if;")
    anchor = ' if v_cached is not null then return v_cached; end if;'
    out = once(out, anchor,
        " if v_action='PREPAYMENT'then perform cp7_credit.prepayment_entry(true);end if;\n" + anchor)
    return out


def reverse_return(body):
    out = once(body, FG, FG + '\n  perform erp.require_owner_admin();'
        "\n  perform cp7_credit.native_source_enter('RETURN_REVERSE',p_return_id);\n  perform erp.require_owner_admin();")
    anchor = "  from erp.sales_payments where sale_id=s.id and status='POSTED';"
    out = once(out, anchor, anchor + '\n  v_paid:=cp7_credit.current_effective_paid(s.id);')
    out = before_terminal_end(out, "perform cp7_credit.native_source_complete('RETURN_REVERSE',p_return_id);"
        '\n  perform erp.require_owner_admin();')
    return out


def reverse_sale(body):
    out = once(body, FG, FG + '\n  perform erp.require_owner_admin();'
        "\n  perform cp7_credit.native_source_enter('SALE_REVERSE',p_sale_id);\n  perform erp.require_owner_admin();")
    # Source completion/receipt finalization remains AFTER every actual inverse
    # and HPP statement. Existing source payment/return guards stay unchanged.
    out = before_terminal_end(out, "perform cp7_credit.native_source_complete('SALE_REVERSE',p_sale_id);"
        '\n  perform erp.require_owner_admin();')
    return out


@dataclass(frozen=True)
class Capture:
    identity: str
    definition: str
    body: str
    owner: str
    acl: tuple
    security_definer: bool
    volatility: str
    config: tuple


@dataclass(frozen=True)
class Approved:
    identity: str
    definition_sha256: str
    body_sha256: str
    owner: str
    acl: tuple
    security_definer: bool
    volatility: str
    config: tuple


def derive(capture, approved, transform):
    # Approved is read from the trusted composed-phase manifest, NEVER minted
    # from this candidate. Raw release SHA may not be substituted here.
    actual = (capture.identity,digest(capture.definition),digest(capture.body),capture.owner,
              tuple(sorted(capture.acl)),capture.security_definer,capture.volatility,capture.config)
    wanted = (approved.identity,approved.definition_sha256,approved.body_sha256,approved.owner,
              tuple(sorted(approved.acl)),approved.security_definer,approved.volatility,approved.config)
    if actual != wanted or capture.owner != 'postgres':
        raise ValueError('OW04_NATIVE_COMPOSED_PREDECESSOR_OR_METADATA_CHANGED')
    changed = transform(capture.body)
    definition = once(capture.definition,capture.body,changed)
    return definition, {'identity':capture.identity,'source_definition_sha256':digest(capture.definition),
        'source_body_sha256':digest(capture.body),'expected_target_definition_sha256':digest(definition),
        'owner':capture.owner,'acl':sorted(capture.acl),'security_definer':capture.security_definer,
        'volatility':capture.volatility,'config':list(capture.config),'native_execution_proven':False}


CAPTURE_QUERY = """select p.oid::regprocedure::text,pg_get_functiondef(p.oid),p.prosrc,
 pg_get_userbyid(p.proowner),coalesce((select array_agg(a::text order by a::text)
 from unnest(p.proacl)a),'{}'::text[]),p.prosecdef,p.provolatile::text,coalesce(p.proconfig,'{}'::text[])
 from pg_proc p where p.oid=%s::regprocedure"""


def derive_no_ambient_context(tables, approved_tables):
    """Use tables from the trusted, verified R4-05 full context-probe manifest.

    Extract through cp7_internal_guard_bundle.unpatched/contexts during the
    owning build after exact guard capture. Never infer a prefix catalogue or
    silently skip a missing table. This helper admits no Native operation.
    """
    if not tables or tuple(tables)!=tuple(approved_tables) or len(set(tables))!=len(tables):
        raise ValueError('OW04_COMPLETE_CONTEXT_MANIFEST_REQUIRED')
    if any(re.fullmatch(r'[a-z0-9_]+\.[a-z0-9_]*context',t)is None for t in tables):
        raise ValueError('OW04_CONTEXT_IDENTIFIER_NOT_TRUSTED')
    query=' union all '.join('select 1 from '+t+' c where c.backend_pid=pg_backend_pid() and c.transaction_id=txid_current()'for t in tables)
    return ("create function cp7_credit.assert_no_ambient_native_context()returns void "
        "language plpgsql volatile security definer set search_path=''as $own$begin if exists("+query+")then "
        "raise exception using errcode='42501',message='CP7_CREDIT_AMBIENT_CONTEXT_REFUSED';end if;end $own$;\n"
        "alter function cp7_credit.assert_no_ambient_native_context()owner to postgres;\n"
        "revoke all on function cp7_credit.assert_no_ambient_native_context()from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write;")

SPECS = (
 ('erp.post_sales_return(uuid)','20260916070451_erp_v2_6_20ah_cp6_return_allocation_eligibility.sql','post_sales_return',post_return),
 ('erp.post_sales_payment(uuid)','20260922135615_erp_v2_6_20ap_cp6_connected_import_materials.sql','post_sales_payment',post_payment),
 ('erp.reverse_sales_payment(uuid,text)','20260922135615_erp_v2_6_20ap_cp6_connected_import_materials.sql','reverse_sales_payment',reverse_payment),
 ('erp.manage_initial_prepayment_v1(jsonb)','20260925010000_erp_v2_6_20ba_cp6_audit_closure.sql','manage_initial_prepayment_v1',prepayment_helper),
 ('erp.save_initial_import_action_v1(text,jsonb,uuid)','20260925020000_erp_v2_6_20bb_cp6_open_cutover_states.sql','save_initial_import_action_v1',prepayment_outer),
 ('erp.reverse_sales_return(uuid,text)','20260915031500_erp_v2_6_20ac_cp6_temporal_surface_closure.sql','reverse_sales_return',reverse_return),
 ('erp.reverse_sale(uuid,text)','20260915031500_erp_v2_6_20ac_cp6_temporal_surface_closure.sql','reverse_sale',reverse_sale),
 ('erp.sync_opening_hpp_after_return_status()','20260915031500_erp_v2_6_20ac_cp6_temporal_surface_closure.sql','sync_opening_hpp_after_return_status',opening_return_status),
)


def static_check(repo):
    output=[]
    for identity,file,name,transform in SPECS:
        text=(repo/'supabase/release/cp6-t3'/file).read_text()
        pattern=rf'CREATE OR REPLACE FUNCTION erp\.{re.escape(name)}\([^$]*?\$function\$(.*?)\$function\$'
        matches=list(re.finditer(pattern,text,re.S))
        if len(matches)!=1:raise ValueError('OW04_STATIC_RELEASE_FUNCTION_NOT_UNIQUE: '+identity)
        definition,body=matches[0].group(0),matches[0].group(1)
        changed=transform(body)
        duplicate_refused=False
        try:transform(body+body)
        except ValueError:duplicate_refused=True
        if not duplicate_refused:raise AssertionError('duplicated anchors accepted')
        output.append({'identity':identity,'release':file,'raw_release_definition_sha256':digest(definition),
            'raw_release_body_sha256':digest(body),'transformed_body_sha256':digest(changed),
            'duplicate_anchor_refused':True})
    return {'scope':'STATIC_RELEASE_ANCHORS_ONLY','native_execution_proven':False,
            'not_an_installer':True,'results':output}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--static-check',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(static_check(args.static_check.resolve()),indent=2))
