"""Independent account/stock/AR equations; no ERP imports or DB operations."""
from decimal import Decimal as D


def require(value,message):
    if not value:raise ValueError(message)


def money(value):
    require(type(value)is str,'MANDOR_ORACLE_EXACT_DECIMAL_TEXT_REQUIRED')
    amount=D(value);require(amount.is_finite()and amount==amount.quantize(D('.01')),'MANDOR_ORACLE_FINITE_CENTS_REQUIRED')
    return amount


def deltas(before,after):
    left,right=before['balances'],after['balances']
    return {k:money(right.get(k,'0'))-money(left.get(k,'0'))for k in set(left)|set(right)
        if money(right.get(k,'0'))!=money(left.get(k,'0'))}


def unchanged_sale_assets(before,after):
    require(before['inventory']==after['inventory'],'MANDOR_ORACLE_OFFSET_CHANGED_STOCK_HPP_OR_COGS_ALLOCATIONS')
    require(before['ordinary_sales_payment_rows']==after['ordinary_sales_payment_rows'],'MANDOR_ORACLE_FICTITIOUS_CASH_SALES_PAYMENT')
    require(before['invoice']['sale_id']==after['invoice']['sale_id']and before['invoice']['customer_id']==after['invoice']['customer_id'],'MANDOR_ORACLE_INVOICE_OR_CUSTOMER_REPLACED')
    require(money(before['invoice']['net'])==money(after['invoice']['net']),'MANDOR_ORACLE_INVOICE_COMMERCIAL_AMOUNT_CHANGED')


def reservation(before,after,amount):
    amount=money(amount);unchanged_sale_assets(before,after)
    require(deltas(before,after)=={},'MANDOR_ORACLE_DRAFT_ALLOCATION_POSTED_MONEY')
    require(money(before['invoice']['paid'])==money(after['invoice']['paid'])and money(before['invoice']['outstanding'])==money(after['invoice']['outstanding']),'MANDOR_ORACLE_DRAFT_ALLOCATION_PAID_INVOICE')
    require(money(before['payroll']['net_payable'])-money(after['payroll']['net_payable'])==amount,'MANDOR_ORACLE_EXACT_DRAFT_NET_DEDUCTION')
    return dict(status='PASS',reserved_amount=str(amount),paid_amount_delta='0',cash_delta='0')


def payment(before,after,amount,accounts):
    amount=money(amount);net=money(before['payroll']['net_payable']);gross=net+amount
    require(net>=0 and amount>0,'MANDOR_ORACLE_VALID_PAYMENT_EQUATION')
    unchanged_sale_assets(before,after)
    require(after['payroll']['status']=='PAID','MANDOR_ORACLE_NATIVE_PAID_STATUS')
    require(money(after['invoice']['paid'])-money(before['invoice']['paid'])==amount,'MANDOR_ORACLE_SAME_AR_INVOICE_PAID_ONCE')
    require(money(before['invoice']['outstanding'])-money(after['invoice']['outstanding'])==amount,'MANDOR_ORACLE_EXACT_REMAINING_AR')
    require(after['invoice']['status']==('PAID'if money(after['invoice']['outstanding'])==0 else'PARTIAL_PAID'),'MANDOR_ORACLE_NATIVE_INVOICE_PAYMENT_STATUS')
    expected={accounts['CONTRACTOR_PAYABLE']:gross,accounts['AR_CUSTOMER']:-amount}
    if net:expected[accounts['CASH']]=-net
    require(len(expected)==(3 if net else 2),'MANDOR_ORACLE_DISTINCT_PAYABLE_AR_CASH_ACCOUNTS')
    require(deltas(before,after)==expected,'MANDOR_ORACLE_EXACT_PAYABLE_AR_NET_CASH_AND_NO_FICTITIOUS_INCOME')
    return dict(status='PASS',gross=str(gross),offset=str(amount),cash_out=str(net),same_invoice_paid_delta=str(amount),other_income_or_wage_expense_delta='0',stock_or_HPP_changed=False)


def released(before,after,amount):
    amount=money(amount);unchanged_sale_assets(before,after)
    require(deltas(before,after)=={},'MANDOR_ORACLE_RELEASE_OR_UNPAID_CANCEL_POSTED_MONEY')
    require(money(before['invoice']['paid'])==money(after['invoice']['paid']),'MANDOR_ORACLE_RELEASE_CHANGED_PAID_AR')
    require(money(after['payroll']['net_payable'])-money(before['payroll']['net_payable'])==amount,'MANDOR_ORACLE_RELEASE_DID_NOT_RESTORE_NET_CAPACITY')
    return dict(status='PASS',released=str(amount),cash_delta='0',invoice_paid_delta='0')


def cancelled_release(before,after,before_reservation,after_cancellation,amount):
    amount=money(amount);unchanged_sale_assets(before,after)
    require(deltas(before,after)=={},'MANDOR_ORACLE_RELEASE_OR_UNPAID_CANCEL_POSTED_MONEY')
    require(before['invoice']==after['invoice'],'MANDOR_ORACLE_CANCEL_CHANGED_INVOICE')
    require(after['payroll']['status']=='REVERSED','MANDOR_NATIVE_UNPAID_CANCELLATION_STATUS')
    require(after['payroll']['net_payable']==before['payroll']['net_payable'],'MANDOR_ORACLE_CANCEL_REWROTE_HISTORICAL_NET')
    old={row['allocation_id']:row for row in before['allocation_states']}
    new={row['allocation_id']:row for row in after['allocation_states']}
    require(set(old)==set(new)and all(row['state']=='RELEASED'for row in new.values()),
        'MANDOR_NATIVE_CANCEL_MUST_RELEASE_ALL_ALLOCATIONS')
    reserved=sum(money(str(row['amount'])) for row in old.values() if row['state']=='RESERVED')
    require(reserved==amount,'MANDOR_ORACLE_CANCEL_WRONG_RESERVED_AMOUNT')
    require(money(after_cancellation['available_to_reserve'])==money(before_reservation['available_to_reserve'])
        and money(after_cancellation['allocated_amount'])==money(before_reservation['allocated_amount']),
        'MANDOR_ORACLE_CANCEL_DID_NOT_RETURN_EXACT_INVOICE_CAPACITY')
    return dict(status='PASS',released=str(amount),cash_delta='0',invoice_paid_delta='0',
        historical_payroll_net_unchanged=True,invoice_capacity_restored=True)


def reversal(before_approval,after_payment,after_reversal,amount):
    amount=money(amount);unchanged_sale_assets(after_payment,after_reversal)
    require(after_reversal['payroll']['status']=='REVERSED','MANDOR_ORACLE_NATIVE_PAID_REVERSAL_STATUS')
    # Existing Native reversal also reverses attendance/extra/manual accruals;
    # compare with the PRE-APPROVAL books, never the already accrued payable.
    require(after_reversal['balances']==before_approval['balances'],'MANDOR_ORACLE_APPROVAL_PAYMENT_AND_OFFSET_REVERSALS_MUST_RESTORE_BOOKS')
    require(money(after_reversal['invoice']['paid'])==money(before_approval['invoice']['paid']),'MANDOR_ORACLE_LAWFUL_REVERSAL_MUST_REOPEN_SAME_INVOICE')
    require(after_reversal['invoice']['status']==before_approval['invoice']['status'],'MANDOR_ORACLE_LAWFUL_REVERSAL_MUST_RESTORE_INVOICE_STATUS')
    return dict(status='PASS',lawful_Native_reversal=True,offset_reversed=str(amount),same_invoice_reopened=True,net_cash_and_offset_books_restored=True)


def installment(before,after,cash_amount,offset_amount,accounts,status):
    cash,offset=money(cash_amount),money(offset_amount)
    unchanged_sale_assets(before,after)
    require(status in('APPROVED','PAID')and after['payroll']['status']==status,'MANDOR_ORACLE_INSTALLMENT_NATIVE_STATUS')
    require(money(after['invoice']['paid'])-money(before['invoice']['paid'])==offset,
        'MANDOR_ORACLE_INSTALLMENT_OFFSET_ONLY_AT_FINAL_OR_REOPEN')
    require(money(before['invoice']['outstanding'])-money(after['invoice']['outstanding'])==offset,
        'MANDOR_ORACLE_INSTALLMENT_EXACT_SAME_INVOICE_BALANCE')
    expected={accounts['CONTRACTOR_PAYABLE']:cash+offset,accounts['CASH']:-cash}
    if offset:expected[accounts['AR_CUSTOMER']]=-offset
    require(len(expected)==(3 if offset else 2),'MANDOR_ORACLE_DISTINCT_INSTALLMENT_ACCOUNTS')
    require(deltas(before,after)==expected,'MANDOR_ORACLE_INSTALLMENT_EXACT_CASH_PAYABLE_AR_AND_NO_NEW_EXPENSE')
    return dict(status='PASS',cash_out=str(cash),offset_paid_delta=str(offset),payable_settled=str(cash+offset),
        actual_Native_status=status,stock_or_HPP_changed=False)
