"""Reject unbound dynamic trigger inputs without executing the SELECT."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import importlib.util
import json
import os
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('automatic_trigger_scope_control_subject', HERE / 'trigger_dispatch.py')
subject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)


class DynamicTriggerScope(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = Path(os.environ['CP7_GLOBAL_RETAINED_ACTUAL25']).read_bytes()
        if len(raw) != 14755737 or sha256(raw).hexdigest() != '80856b7ec2cebf08318a21617091b73c6744161b72bb3be98bcb9ecd2b8109eb':
            raise ValueError('TRIGGER_CONTROL_EXACT_RETAINED_ACTUAL25_REQUIRED')
        complete = {key: dict(rows) for key, rows in json.loads(raw).items()}
        cls.retained = dict(functions={subject.SIGNATURE: complete['functions'][subject.SIGNATURE]},
                            triggers={key: row for key, row in complete['triggers'].items() if row[8] == subject.SIGNATURE},
                            columns=complete['columns'], relations=complete['relations'])

    def bind(self, candidate):
        return subject.bind(candidate, self.retained, dict(literal_dynamic_source_bounds={}))

    def test_all_trigger_slots_expand_to_only_exact_parameterized_read_queries(self):
        prior = dict(literal_dynamic_source_bounds={})
        proof = subject.bind(self.retained, self.retained, prior)
        self.assertEqual((len(proof['bindings']), proof['distinct_literal_queries']), (21, 18))
        from pglast.parser import parse_sql_json
        for statement in prior['literal_dynamic_source_bounds'][subject.SIGNATURE]['statements']:
            nodes = json.loads(parse_sql_json(statement['query']))['stmts']
            self.assertEqual([list(item['stmt']) for item in nodes], [['SelectStmt']])
            self.assertIn('WHERE id=$1 FOR SHARE', statement['query'])
        self.assertEqual(proof['actual_SQL_executed'], 0)

    def test_each_function_attribute_and_each_trigger_attribute_refuses_when_changed(self):
        for index in range(19):
            candidate = dict(self.retained, functions=deepcopy(self.retained['functions']))
            candidate['functions'][subject.SIGNATURE][index] = 'FORGED'
            with self.subTest(function_attribute=index), self.assertRaises(ValueError):
                self.bind(candidate)
        for key in self.retained['triggers']:
            for index in range(16):
                candidate = dict(self.retained, triggers=deepcopy(self.retained['triggers']))
                candidate['triggers'][key][index] = 'FORGED'
                with self.subTest(trigger=key, attribute=index), self.assertRaises(ValueError):
                    self.bind(candidate)

    def test_missing_and_additional_trigger_bindings_refuse(self):
        for key in self.retained['triggers']:
            candidate = dict(self.retained, triggers=dict(self.retained['triggers']))
            candidate['triggers'].pop(key)
            with self.subTest(missing=key), self.assertRaises(ValueError):
                self.bind(candidate)
        candidate = dict(self.retained, triggers=dict(self.retained['triggers']))
        candidate['triggers']['erp.future_table:unreviewed'] = next(iter(candidate['triggers'].values()))
        with self.assertRaises(ValueError):
            self.bind(candidate)

    def test_parent_and_child_uuid_or_missing_parent_status_refuse(self):
        for identity, trigger in self.retained['triggers'].items():
            arguments = bytes.fromhex(trigger[4])[:-1].decode().split('\0')
            parent = 'erp.' + arguments[0]
            for name in (parent + ':id', identity.split(':')[0] + ':' + arguments[1]):
                candidate = dict(self.retained, columns=deepcopy(self.retained['columns']))
                candidate['columns'][name][2] = 'text'
                with self.subTest(column=name), self.assertRaises(ValueError):
                    self.bind(candidate)
            candidate = dict(self.retained, columns=dict(self.retained['columns']))
            candidate['columns'].pop(parent + ':status')
            with self.subTest(status=parent), self.assertRaises(ValueError):
                self.bind(candidate)


if __name__ == '__main__':
    unittest.main()
