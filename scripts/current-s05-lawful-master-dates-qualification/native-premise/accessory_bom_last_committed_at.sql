CREATE OR REPLACE FUNCTION erp.accessory_bom_last_committed_at(p_bom_version_id uuid)
 RETURNS timestamp with time zone
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$ SELECT MAX(x.at) FROM (SELECT c.committed_at AS at FROM erp.po_accessory_bom_commitments c WHERE c.bom_version_id=$1 UNION ALL SELECT s.costing_basis_at FROM erp.fg_accessory_cost_snapshots s WHERE s.bom_version_id=$1) x $function$;
