"""Resolve commercial search labels without rewriting physical product history."""
from cp6_bc_build import last_definition, substitute

REPLACED=['erp.get_product_conversion_workspace_v1(jsonb)']


def changed(be):
    workspace=substitute(last_definition(be,'get_product_conversion_workspace_v1'),[
        ('l.produced_at,p.sku,p.product_name,p.model_id,p.size_id,',
         'l.produced_at,erp.bf_commercial_sku_at_v1(p.id,statement_timestamp()) sku,p.product_name,p.model_id,p.size_id,'),
        ("lower(p.sku||' '||p.product_name||' '||l.lot_number)",
         "lower(concat_ws(' ',p.sku,erp.bf_commercial_sku_at_v1(p.id,statement_timestamp()),p.product_name,l.lot_number))"),
        ('with targets as(select p.id,p.sku,p.product_name,p.model_id,p.size_id',
         'with targets as(select p.id,erp.bf_commercial_sku_at_v1(p.id,statement_timestamp()) sku,p.product_name,p.model_id,p.size_id'),
        ("lower(p.sku||' '||p.product_name)",
         "lower(concat_ws(' ',p.sku,erp.bf_commercial_sku_at_v1(p.id,statement_timestamp()),p.product_name))"),
        ('p.sku source_sku,t.sku target_sku',
         'erp.bf_commercial_sku_at_v1(p.id,c.physical_at) source_sku,erp.bf_commercial_sku_at_v1(t.id,c.physical_at) target_sku'),
    ],'BF commercial SKU search with unchanged physical IDs and historical conversion labels')
    return [workspace]
