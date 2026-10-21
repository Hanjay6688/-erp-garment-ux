"""Exact CP7 apply-command hooks; capture/metadata authority belongs to assembler."""
IDENTITY = 'cp7_sales.apply_command(text,jsonb,uuid,text)'


def once(body, anchor, changed):
    if body.count(anchor) != 1:
        raise ValueError('OW04_SOURCE_COMMAND_ANCHOR_CHANGED: ' + anchor)
    return body.replace(anchor, changed, 1)


def apply_command(body):
    if 'cp7_credit.source_request_enter_v1' in body or 'cp7_credit.source_request_finish_v1' in body:
        raise ValueError('OW04_SOURCE_COMMAND_ALREADY_HOOKED')
    for action, source, native in (
        ('RETURN_REVERSE', 'return_id', 'reverse_sales_return'),
        ('PAYMENT_REVERSE', 'payment_id', 'reverse_sales_payment'),
    ):
        if body.count("elsif p_action='" + action + "' then") != 1:
            raise ValueError('OW04_SOURCE_COMMAND_ACTION_BRANCH_CHANGED: ' + action)
        anchor = '  perform erp.' + native + '(' + source + ",btrim(p_payload->>'change_reason'));"
        body = once(body, anchor,
            '  perform cp7_credit.source_request_enter_v1(p_action,p_payload,p_request,p_expected);\n'
            + anchor + '\n  perform cp7_credit.source_request_finish_v1(p_request);')
    return body
