"""Private consumer assembly; no caller installer or production activation."""
from pathlib import Path
from hashlib import sha256
import json
import cp7_model_target_source as source
import cp7_model_target_projection as projection
import cp7_product_analog_provenance_stage as analog
from .timeline import render as timeline

ROOT=Path(__file__).resolve().parent


def verify_sources():
    source.verify_sources();projection.verify_sources();analog.verify_sources()
    m=json.loads((ROOT/'MANIFEST.json').read_text())
    if sha256((ROOT/'consumer.sql').read_bytes()).hexdigest()!=m['sql_sha256']:
        raise ValueError('MODEL_TARGET_CONSUMER_SQL_CHANGED')
    if (ROOT/'timeline.sql').read_text()!=timeline()or sha256((ROOT/'timeline.sql').read_bytes()).hexdigest()!=m['timeline_sql_sha256']:
        raise ValueError('MODEL_TARGET_TIMELINE_SQL_CHANGED')
    return m
