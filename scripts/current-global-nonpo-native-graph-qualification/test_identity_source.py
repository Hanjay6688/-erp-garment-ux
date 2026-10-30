"""Bounded documentary successor source/schema controls; Native cases remain0."""
from pathlib import Path
from hashlib import sha256
from unittest import TestCase,main
import gzip,json,re
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];RUNTIME=ROOT/'scripts/cp7_global_nonpo_native_graph_adapter'


def columns(definition):
    return set(re.findall(r'(?:\(|,)\s*([a-z][a-z0-9_]*)\s+(?:uuid|text|jsonb|numeric|integer|bigint|boolean|varchar|character varying|timestamptz|timestamp|date)\b',definition,re.I))


class IdentitySourceControls(TestCase):
    def test_frozen_4e263_receipts_and_first_counterexample_are_preserved(self):
        historical=json.loads((HERE/'retained/4e263_SOURCE.json').read_bytes())
        first=json.loads(gzip.decompress((HERE/'evidence/IDENTITY_CLOSURE_FIRST_4e263_REPRO.json.gz').read_bytes()))
        self.assertEqual(first['status'],'CONFIRMED_INSPECTOR_IDENTITY_CUT_GAP');self.assertEqual(first['actual_Native'],0)
        self.assertEqual(first['direct_before'],first['direct_after']);self.assertFalse(first['qualified_for_runtime'])
        for name in ['scope.sql','capture.sql']:
            raw=(HERE/'retained'/('4e263_'+name)).read_bytes()
            self.assertEqual(sha256(raw).hexdigest(),historical['files']['scripts/cp7_global_nonpo_native_graph_adapter/'+name]['sha256'])
        for name in ['authority.sql','inspect.sql']:
            raw=(RUNTIME/name).read_bytes()
            self.assertEqual(sha256(raw).hexdigest(),historical['files']['scripts/cp7_global_nonpo_native_graph_adapter/'+name]['sha256'])
        for name in ['test_model.mjs','retained/Native_authority.sql','retained/Current_parent_readers.sql']:
            raw=(HERE/name).read_bytes()
            self.assertEqual(sha256(raw).hexdigest(),historical['files']['scripts/current-global-nonpo-native-graph-qualification/'+name]['sha256'])

    def test_exact_schema_proof_has_nullable_dimensions_and_shared_document_keys(self):
        proof=json.loads((HERE/'IDENTITY_CLOSURE_SOURCE_PROOF.json').read_bytes())
        self.assertEqual(len(proof['tables']),15)
        for name,pin in proof['tables'].items():
            raw=pin['definition'].encode();self.assertEqual(len(raw),pin['bytes']);self.assertEqual(sha256(raw).hexdigest(),pin['sha256'])
            if not Path(pin['source']).is_absolute():self.assertIn(pin['definition'],(ROOT/pin['source']).read_text())
        ddl=proof['tables']['erp.journal_lines']['definition']
        self.assertRegex(ddl,r'\n\s+product_id uuid,');self.assertRegex(ddl,r'\n\s+po_id uuid,')
        self.assertIn('primary key(document_id,link_kind,link_id)',proof['tables']['erp.bc_document_links_v1']['definition'])
        self.assertIn('document_id uuid references',proof['tables']['erp.bc_return_lots_v1']['definition'])

    def test_typed_models_cover_every_retained_shared_native_column(self):
        proof=json.loads((HERE/'IDENTITY_CLOSURE_SOURCE_PROOF.json').read_bytes());model=(HERE/'model.sql').read_text()
        for name,pin in proof['tables'].items():
            match=re.search(r'create table '+re.escape(name)+r'\((.*?);',model,re.S|re.I)
            self.assertIsNotNone(match,name)
            modeled=columns('('+match[1]);modeled.update(re.findall(r'\badd\s+([a-z][a-z0-9_]*)\s+', '\n'.join(re.findall(r'alter table '+re.escape(name)+r'\s+(.*?);',model,re.S|re.I))))
            expected=columns(pin['definition'])
            self.assertTrue(expected<=modeled,(name,sorted(expected-modeled)))
            self.assertEqual(modeled-expected,{'amount'}if name=='erp.material_adjustments'else set(),name)

    def test_identity_edges_use_concrete_ids_without_account_category_hubs(self):
        sql=(RUNTIME/'scope.sql').read_text()
        for table in ['be_conversion_cost_events_v1','be_nonpo_transfer_events_v1','bc_document_links_v1','bc_adjustment_purposes_v1','bc_lot_events_v1']:
            self.assertIn('erp.'+table,sql)
        self.assertIn("'JOURNAL',j.id,'JOURNAL',j.reversal_of_id",sql)
        self.assertIn('support except select *from relevant',sql)
        self.assertNotRegex(sql,r"'(?:ACCOUNT|CATEGORY|MATERIAL)'\s*[,)]")
        self.assertIn("'account_or_category_identity_hubs_used',false",sql)
        a=json.loads((RUNTIME/'AUTHORITY.json').read_bytes())
        self.assertFalse(a['identity_closure_source_profile']['Native_G_predicates_changed']);self.assertIsNone(a['runtime_entry'])
        self.assertIn('20260925030000_erp_v2_6_20bc_cp6_accessory_service_returns.sql',' '.join(a['parent_source_files']))

    def test_native_cycle_query_is_exact_exists_body_without_writer_execution(self):
        native=(HERE/'retained/Native_authority.sql').read_text();query=(HERE/'retained/Native_lineage_guard_query.sql').read_text()
        body=re.search(r"  if exists\(\n(    with recursive reachable\(lot_id,path,depth\)[\s\S]*?)\n  \) then\n    raise exception 'BE_NON_PO_LINEAGE_ORPHAN_OR_CYCLE';",native).group(1)
        self.assertIn(body,query);self.assertNotRegex(query,r'(?i)\b(insert|update|delete|nextval|gen_random_uuid)\b')
        proof=json.loads((HERE/'IDENTITY_CLOSURE_SOURCE_PROOF.json').read_bytes())
        self.assertEqual(sha256(body.encode()).hexdigest(),proof['Native_lineage_query']['query_body_sha256'])
        visits=re.search(r'(    with recursive rooted\(lot_id,depth,path\)[\s\S]*?    order by x.depth,a.id)\n  loop',native).group(1)
        self.assertIn(visits,(HERE/'retained/Native_propagation_visits_query.sql').read_text())
        self.assertEqual(sha256(visits.encode()).hexdigest(),proof['Native_ordered_visits_query']['query_body_sha256'])
        self.assertIn('context DML',proof['Native_dispatcher_purity_limitation'])
        self.assertIsNone(proof['runtime_entry']);self.assertFalse(proof['writer_or_phantom_lock_closed'])


if __name__=='__main__':main(verbosity=2)
