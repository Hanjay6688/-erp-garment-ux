"""Diagnostic controls only; no ERP case, source fixture or clock is changed."""
from contextlib import redirect_stdout
from unittest.mock import patch
import ast,io,json,unittest
from pathlib import Path
from cp7_accessory_nonpayable import progress


class ProgressControls(unittest.TestCase):
    def test_every_actual_qualifier_phase_enters_the_real_guard_before_database_setup(self):
        here=Path(__file__).resolve().parent;declared=set()
        for name in ('qualification.py','qualification_component.py'):
            for node in ast.walk(ast.parse((here/name).read_bytes())):
                if(isinstance(node,ast.Call)and isinstance(node.func,ast.Attribute)
                    and isinstance(node.func.value,ast.Name)and node.func.value.id=='progress'
                    and node.func.attr=='phase'):
                    self.assertTrue(node.args and isinstance(node.args[0],ast.Constant))
                    self.assertIs(type(node.args[0].value),str);declared.add(node.args[0].value)
        self.assertIn('COMPLETE_STATE_PREREQUISITE',declared)
        self.assertEqual(declared,progress.PHASES)
        output=io.StringIO();entered=[]
        with redirect_stdout(output):
            for name in sorted(declared):
                with progress.phase(name):entered.append(name)
        self.assertEqual(entered,sorted(declared))
        rows=[json.loads(line)for line in output.getvalue().splitlines()]
        self.assertEqual([(row['phase'],row['afui_progress'])for row in rows],
            [(name,event)for name in sorted(declared)for event in ('ENTER','RETURNED')])
        self.assertTrue(all(row['diagnostic_only']is True for row in rows))

    def test_small_phase_receipts_do_not_relabel_business_acceptance(self):
        output=io.StringIO();ran=[]
        with redirect_stdout(output):
            with progress.phase('NATIVE_CASE','UNCHANGED_CASE'):ran.append('original operation')
        self.assertEqual(ran,['original operation']);rows=[json.loads(x)for x in output.getvalue().splitlines()]
        self.assertEqual([r['afui_progress']for r in rows],['ENTER','RETURNED'])
        for row,line in zip(rows,output.getvalue().splitlines()):
            self.assertLess(len(line.encode()),1024);self.assertTrue(row['diagnostic_only'])
            self.assertNotIn('status',row);self.assertNotIn('payload',row);self.assertGreaterEqual(row['elapsed_seconds'],0)

    def test_original_exception_and_cancellation_are_preserved_without_payload_logging(self):
        for error in (RuntimeError('private payload never copied'),KeyboardInterrupt()):
            output=io.StringIO();caught=None
            try:
                with redirect_stdout(output),progress.phase('WHOLE_PACKAGE'):raise error
            except BaseException as observed:caught=observed
            self.assertIs(caught,error);self.assertNotIn('private payload',output.getvalue())
            rows=[json.loads(x)for x in output.getvalue().splitlines()]
            self.assertEqual(rows[-1]['afui_progress'],'RAISED');self.assertEqual(rows[-1]['error_type'],type(error).__name__)

    def test_broken_log_stream_cannot_replace_result_failure_or_cleanup(self):
        entered=[];error=ValueError('original refusal')
        with patch('builtins.print',side_effect=BrokenPipeError('log disconnected')):
            with progress.phase('HTTP_GROUP'):entered.append('returned')
            with self.assertRaises(ValueError)as caught:
                try:
                    with progress.phase('SESSION_GROUP'):raise error
                finally:entered.append('original cleanup')
        self.assertIs(caught.exception,error);self.assertEqual(entered,['returned','original cleanup'])

    def test_unbounded_or_payload_like_labels_refuse_before_operation(self):
        for name,case in (('unreviewed',None),('NATIVE_CASE','x\nsecret'),('NATIVE_CASE','A'*161),('NATIVE_CASE',{})):
            with self.subTest(name=name,case=case),self.assertRaisesRegex(ValueError,'FIXED_BOUNDED_PROGRESS_ID'):
                with progress.phase(name,case):self.fail('invalid diagnostic label entered original operation')


if __name__=='__main__':unittest.main()
