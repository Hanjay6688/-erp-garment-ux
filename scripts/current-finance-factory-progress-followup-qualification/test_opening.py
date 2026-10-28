from pathlib import Path
import json,unittest
import opening


class ExactPrivateOpeningReader(unittest.TestCase):
    def test_live_Native_body_and_HPP_arithmetic_are_retained_exactly(self):
        result=opening.derived();binding=json.loads((Path(__file__).with_name('BINDING.json')).read_bytes())
        self.assertEqual(result['body'],binding['native_opening']['definition'].split('$function$')[1])
        old=binding['private_hpp']['definition'].split('$function$')[1]
        self.assertEqual(result['hpp_body'].replace(opening.NEW,opening.OLD,1),old)
        self.assertEqual(result['hpp_body'].count(opening.NEW),1)
        self.assertIn("stable security definer set search_path=''",result['definition'])
        self.assertIn('perform erp.require_internal();',result['body'])
        self.assertIn("time zone 'Asia/Jakarta'",result['body'])
        self.assertEqual(binding['native_opening']['volatility'],'v')


if __name__=='__main__':unittest.main()
