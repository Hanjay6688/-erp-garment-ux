"""Local source/metadata controls; no Native runtime or installation claim."""
import ast,importlib.util,unittest
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('sku_manual_native_delta',HERE/'native_delta.py')
delta=importlib.util.module_from_spec(spec);spec.loader.exec_module(delta)
spec=importlib.util.spec_from_file_location('sku_manual_ri_catalog',HERE/'ri_catalog.py')
ri_catalog=importlib.util.module_from_spec(spec);spec.loader.exec_module(ri_catalog)

def function(path,name):
    text=(ROOT/path).read_text();start=text.index('CREATE OR REPLACE FUNCTION '+name+'(')
    end=text.index('$function$;',start)+len('$function$;')
    return text[start:end]

class DeltaTests(unittest.TestCase):
    def originals(self):
        return dict(zip(delta.SIGNATURES,(
          function('scripts/cp6_bf_objects_router.sql','public.erp_get_sku_workspace_v1'),
          function('scripts/cp6_bf_objects_router.sql','public.erp_save_sku_action_v1'),
          function('scripts/cp6_be_objects_conversion.sql','public.erp_get_product_conversion_workspace_v1'),
          function('scripts/cp6_be_objects_conversion.sql','public.erp_save_product_conversion_action_v1'),
          function('scripts/cp6_be_objects_conversion.sql','erp.be_conversion_preview_v1'),
          function('supabase/release/cp6-t3-src/20260926050000_erp_v2_6_20be_cp6_conversion_redye_pocket.sql','erp.reverse_product_conversion'))))

    def test_exact_six_and_narrow_private_context(self):
        originals=self.originals();patched=delta.patched(originals)
        self.assertEqual(set(patched),set(originals))
        self.assertIn('manual_allocation_v1(l.id,t.id,',patched[delta.SIGNATURES[4]])
        self.assertIn('BE_DIMENSION_MISMATCH',patched[delta.SIGNATURES[4]])
        self.assertIn('assert_group_reverse_v1(p_conversion_id)',patched[delta.SIGNATURES[5]])
        self.assertNotIn('erp.post_product_conversion(uuid)',patched)
        self.assertNotIn('current_setting(',patched[delta.SIGNATURES[4]])

    def test_changed_predecessor_missing_or_additional_signature_is_refused(self):
        originals=self.originals()
        for mutation in ('missing','additional','guard','redirect'):
            damaged=dict(originals)
            if mutation=='missing':del damaged[delta.SIGNATURES[0]]
            elif mutation=='additional':damaged['erp.unreviewed()']='select 1'
            elif mutation=='guard':damaged[delta.SIGNATURES[4]]=damaged[delta.SIGNATURES[4]].replace('if t.model_id','if (t.model_id')
            else:damaged[delta.SIGNATURES[0]]=damaged[delta.SIGNATURES[0]].replace('erp.get_sku_workspace_v1(p_filters)','erp.unreviewed(p_filters)')
            with self.assertRaisesRegex(ValueError,'EXACT_SIX_REQUIRED|PREDECESSOR_CHANGED'):delta.patched(damaged)

    def test_metadata_transition_refuses_outside_changes_and_changed_old_ownership(self):
        tree=ast.parse((HERE/'composition.py').read_text())
        nodes=[node for node in tree.body if isinstance(node,ast.FunctionDef)and node.name=='transition']
        namespace={'SCHEMA':delta.SCHEMA,'FUNCTIONS':('cp7_sku_conversion.example()',),'ri_catalog':ri_catalog}
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'<transition>','exec'),namespace)
        before={name:{}for name in ('schemas','functions','relations','columns','constraints','indexes','triggers','types','type_implementation','policies',*[f'other_{i}'for i in range(12)])}
        before['functions']['erp.old()']=['before','postgres','acl']
        after={key:dict(values)for key,values in before.items()};after['schemas'][delta.SCHEMA]=['postgres'];after['functions']['cp7_sku_conversion.example()']=['new','postgres','acl'];after['functions']['erp.old()']=['after','postgres','acl']
        after['constraints'].update(ri_catalog.expected_constraints());after['triggers'].update(ri_catalog.expected_parent_triggers(after['constraints']))
        namespace['transition'](before,after,{'erp.old()':'after'})
        after['functions']['erp.old()']=['after','other_owner','acl']
        with self.assertRaisesRegex(ValueError,'UNDECLARED_CATALOG_DELTA'):namespace['transition'](before,after,{'erp.old()':'after'})
        after['functions']['erp.old()']=['after','postgres','acl'];after['relations']['erp.unauthorized']=['table']
        with self.assertRaisesRegex(ValueError,'UNDECLARED_CATALOG_DELTA'):namespace['transition'](before,after,{'erp.old()':'after'})

    def test_only_six_declared_parent_RI_triggers_with_exact_constraint_references(self):
        expected=ri_catalog.expected_parent_triggers(ri_catalog.expected_constraints())
        self.assertEqual(len(expected),6)
        key,row=next(iter(expected.items()))
        self.assertTrue(ri_catalog.permitted_parent_trigger(key,row,expected))
        self.assertFalse(ri_catalog.permitted_parent_trigger('erp.bf_skus_v1:rogue_user_trigger',row,expected))
        for index,value in((0,False),(1,'D'),(2,5),(8,'erp.rogue()'),(12,'other_fkey'),(13,'erp.other'),(15,'erp.other')):
            wrong=list(row);wrong[index]=value
            self.assertFalse(ri_catalog.permitted_parent_trigger(key,wrong,expected),(index,wrong))
        constraints=ri_catalog.expected_constraints();constraint=next(iter(constraints));constraints[constraint]=list(constraints[constraint]);constraints[constraint][-1]='FOREIGN KEY (left_id) REFERENCES erp.other(id)'
        with self.assertRaisesRegex(ValueError,'FOREIGN_KEY_EDGE_CHANGED'):ri_catalog.expected_parent_triggers(constraints)

if __name__=='__main__':unittest.main()
