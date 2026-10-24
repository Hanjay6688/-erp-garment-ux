"""One opt-in correction to the direct baseline reader; no default changes."""
from pathlib import Path
from hashlib import sha256
import json
from cp7_production_stage import _body
from cp7_product_analog_consumer_stage.render import block,once,replacements

ROOT=Path(__file__).resolve().parent
SIGNATURE='cp7_baseline_native.serve(uuid)'


def original():
    return block('cp7_production_stage/sql/cp7_baseline_native__serve.sql','cp7_baseline_native.serve')


def replacement():
    old=original()
    anchor="'production_policies',c->'production_policies'->'rows'"
    result=once(old,anchor,anchor+",'product_analog_choices',c->'product_analog_choices','analog_consumer_engine',c->'analog_consumer_engine'")
    # The reader must use exactly the producer's source identity expression.
    producer=replacements()['cp7_baseline_native.build(jsonb,jsonb)']
    expression=producer.split(' hash:=',1)[1].split(';',1)[0]
    assert result.split('hash:=',1)[1].split(';',1)[0]==expression
    return result+'\n'


def manifest():
    return dict(contract='cp7.baseline-freshness-stage.v1',existing_replacements=1,
      new_private_functions=0,new_public_rpcs=0,new_tables=0,
      predecessor_body_sha256=sha256(_body(original()).encode()).hexdigest(),
      replacement_body_sha256=sha256(_body(replacement()).encode()).hexdigest(),
      sql_sha256=sha256(replacement().encode()).hexdigest(),
      old_immutable_results_rewritten=False,default_installed=False,production_go=False)


if __name__=='__main__':
    (ROOT/'reader.sql').write_text(replacement())
    (ROOT/'MANIFEST.json').write_text(json.dumps(manifest(),indent=2)+'\n')
