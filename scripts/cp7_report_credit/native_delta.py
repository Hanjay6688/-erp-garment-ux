"""Counted substitutions of the two installed report check readers (OW-08a).

Each invoice's adjustment U-I is read once per check run in a materialized CTE
and joined by sale id; posted payments, net sales, the GL side and every other
check stay byte-for-byte. An invoice without OW04 credit has adjustment 0, so
its result is unchanged. An unprovable credit profile (null) is a new critical
check instead of an error that would stop the whole owner report.
"""
REPORT='erp.run_v268_financial_report_checks()'
SCOPE='erp._v268_financial_report_checks_pre_scope()'
SIGNATURES=(REPORT,SCOPE)
CHECK='CP7_CUSTOMER_CREDIT_REPORT_UNPROVEN'
CTE=("  with cp7_credit_effective as materialized(\n"
     "    select h.id sale_id,cp7_report_credit.adjustment_v1(h.id) adjustment\n"
     "    from erp.sales_headers h where h.status in('POSTED','PARTIAL_PAID','PAID')\n"
     "  )")


def once(body,old,new,label):
    if body.count(old)!=1:
        raise ValueError('OW08A_PREDECESSOR_SOURCE_CHANGED: '+label)
    return body.replace(old,new,1)


def patched(originals):
    if set(originals)!=set(SIGNATURES):raise ValueError('OW08A_NATIVE_DELTA_SET_CHANGED')
    result=dict(originals)
    head=("  return query\n"
          "  select r.check_name,r.severity,r.issue_count,r.details\n"
          "  from erp._v268_financial_report_checks_pre_scope() r\n")
    result[REPORT]=once(result[REPORT],head,"  return query\n"+CTE+"\n"+head[len("  return query\n"):],REPORT+':credit-cte')
    status=("  from erp.sales_headers h\n"
            "  cross join lateral(\n"
            "    select round(erp.sale_net_total(h.id),2)::numeric(20,2) total,\n"
            "      round(coalesce(sum(round(p.amount,2)),0),2)::numeric(20,2) paid\n"
            "    from erp.sales_payments p where p.sale_id=h.id and p.status='POSTED'\n"
            "  ) x\n")
    result[REPORT]=once(result[REPORT],status,
        "  from erp.sales_headers h\n"
        "  left join cp7_credit_effective ce on ce.sale_id=h.id\n"
        "  cross join lateral(\n"
        "    select round(erp.sale_net_total(h.id),2)::numeric(20,2) total,\n"
        "      round(coalesce(sum(round(p.amount,2)),0)+coalesce(ce.adjustment,0),2)::numeric(20,2) paid\n"
        "    from erp.sales_payments p where p.sale_id=h.id and p.status='POSTED'\n"
        "  ) x\n",REPORT+':status')
    customer=("          where p.sale_id=h.id and p.status='POSTED'),0) amount\n"
              "        from erp.sales_headers h where h.status in('POSTED','PARTIAL_PAID','PAID')\n")
    result[REPORT]=once(result[REPORT],customer,
        "          where p.sale_id=h.id and p.status='POSTED'),0)-coalesce(ce.adjustment,0) amount\n"
        "        from erp.sales_headers h left join cp7_credit_effective ce on ce.sale_id=h.id\n"
        "        where h.status in('POSTED','PARTIAL_PAID','PAID')\n",REPORT+':by-customer')
    anchor="\n  union all\n  select 'V2620G_LAUNDRY_WIP_CUSTODY_MISMATCH'"
    result[REPORT]=once(result[REPORT],anchor,
        "\n  union all\n  select '"+CHECK+"','CRITICAL',count(*)::bigint,\n"
        "    'Every active invoice customer-credit adjustment must be provable from its retained credit parts, journals and uses'\n"
        "  from cp7_credit_effective where adjustment is null\n"+anchor,REPORT+':unproven')
    head="  return query\n  with expected_daily as(\n"
    result[SCOPE]=once(result[SCOPE],head,"  return query\n"+CTE+",expected_daily as(\n",SCOPE+':credit-cte')
    ar=("          from erp.sales_payments p where p.sale_id=h.id and p.status='POSTED'),0)\n"
        "      ) from erp.sales_headers h\n"
        "          where h.status in('POSTED','PARTIAL_PAID','PAID')),0)::numeric\n")
    result[SCOPE]=once(result[SCOPE],ar,
        "          from erp.sales_payments p where p.sale_id=h.id and p.status='POSTED'),0)-coalesce(ce.adjustment,0)\n"
        "      ) from erp.sales_headers h left join cp7_credit_effective ce on ce.sale_id=h.id\n"
        "          where h.status in('POSTED','PARTIAL_PAID','PAID')),0)::numeric\n",SCOPE+':ar')
    return result
