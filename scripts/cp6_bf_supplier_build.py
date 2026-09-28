"""Supplier return credit allocation preserves the original economic cent facts."""
from cp6_bc_build import last_definition, substitute
REPLACED=['erp.material_purchase_final_ap_total(uuid)','erp._cp6_supplier_cent_state(uuid[])','erp.post_supplier_payment(uuid)']

def changed(fixture,be,ap):
    final=substitute(fixture('material_purchase_final_ap_total'),[
      ('-(select amount from return_relief),0)::numeric','-(select amount from return_relief),0)::numeric+erp.bf_supplier_credit_delta_v1(p_purchase_id)')
    ],'BF supplier credit document allocation')
    cent=substitute(last_definition(be,'_cp6_supplier_cent_state'),[
      ("'ap',round(erp.material_purchase_final_ap_total(h.id),2)","'ap',round(erp.material_purchase_final_ap_total(h.id)-erp.bf_supplier_credit_delta_v1(h.id),2)")
    ],'BF economic credit remains on return cent fact')
    payment=substitute(last_definition(ap,'post_supplier_payment'),[
      ('select erp.material_purchase_payable_total(h.id)::numeric(20,2) into v_total;',
       '''select least(erp.material_purchase_payable_total(h.id),
         erp.material_purchase_payable_total(h.id)-erp.bf_supplier_credit_delta_v1(h.id)
         +erp.bf_supplier_credit_delta_v1(h.id,erp._cp3_business_date(p.payment_date)))::numeric(20,2) into v_total;'''),
      ("case when v_paid=round(v_total,2) then 'PAID'", "case when v_paid=round(erp.material_purchase_payable_total(h.id),2) then 'PAID'")
    ],'BF payment cannot borrow a future credit allocation')
    return [final,cent,payment]
