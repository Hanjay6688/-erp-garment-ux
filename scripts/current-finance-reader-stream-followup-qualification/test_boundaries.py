from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import importlib.util,json,shutil,sys,unittest
import psycopg
import source_guard,workflow_guard

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


class ReaderStreamAdmissionBoundaries(unittest.TestCase):
    def test_closed_product_cannot_touch_cursor_or_load_parent(self):
        product=load('closed_reader_stream_product',HERE/'composition.py')
        class NoDatabase:
            def __getattr__(self,name):raise AssertionError('UNADMITTED_DATABASE:'+name)
        with TemporaryDirectory()as name:
            closed=Path(name);shutil.copy2(HERE/'evidence.py',closed/'evidence.py')
            (closed/'CONFIG.json').write_text('{"allow_database_execution":false}')
            with patch.object(product,'HERE',closed),patch.object(product,'base',side_effect=AssertionError('UNADMITTED_PARENT_LOAD')):
                for operation in (lambda:product.install(NoDatabase()),lambda:product.install_delta(NoDatabase(),{}),lambda:product.sources()):
                    with self.assertRaisesRegex(ValueError,'ACTUAL_AF_FIRST_FAILURE_REQUIRED'):operation()

    def test_real_probe_and_factory_share_the_exact_streamed_catalog(self):
        with patch.object(sys,'argv',[__file__]),patch.object(psycopg,'connect',side_effect=AssertionError('NO_DATABASE_ALLOWED')):
            probe=load('reader_stream_actual_dependency_probe',HERE/'probe.py')
            catalog=probe.product.runtime()[4]
            self.assertIs(catalog,probe.runner.cases.factory.product.catalog)
            self.assertIs(catalog,probe.runner.cases.retained.product.catalog)
            original=catalog._data
            with probe.stream_data.bound(catalog)as context:
                self.assertIs(catalog._data,probe.runner.cases.factory.product.catalog._data)
                self.assertIs(context['original'],original)
            self.assertIs(catalog._data,original)

    def test_all_old_assertions_are_retained_and_mutations_refused(self):
        proof=source_guard.check(ROOT,HERE)
        self.assertEqual(proof['factory.py']['assertions'],36)
        self.assertEqual(proof['probe.py']['assertions'],9)
        self.assertEqual(proof['runner.py']['assertions'],14)
        changed=(HERE/'runner.py').read_text().replace("assert catalog._data(c)==data and database._roles(c)==roles","pass",1)
        self.assertNotEqual(changed,(HERE/'runner.py').read_text())
        with self.assertRaisesRegex(AssertionError,'UNDECLARED_ORACLE_CHANGE'):
            source_guard.check(ROOT,HERE,overrides={'runner.py':changed})

    def test_actual_corrected_execution_cannot_be_skipped(self):
        value=workflow_guard.expected(ROOT,HERE)
        runtime=[step for step in value['jobs']['p21']['steps']if step.get('name')=='Run same7 with private stable opening reader and exact streaming data restoration']
        self.assertEqual(len(runtime),1);runtime[0]['run']='true'
        with self.assertRaisesRegex(AssertionError,'UNDECLARED_WORKFLOW_CHANGE'):
            workflow_guard.check(ROOT,HERE,actual=value)


if __name__=='__main__':unittest.main()
