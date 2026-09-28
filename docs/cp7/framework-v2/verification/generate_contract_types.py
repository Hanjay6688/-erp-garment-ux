"""Generate the proposed AnalysisResult shape from JSON Schema, no product writes."""
from pathlib import Path
import json
P=Path(__file__).resolve().parents[1]
def ts(node):
    if 'oneOf' in node:return '('+' | '.join(ts(x) for x in node['oneOf'])+')'
    if 'enum' in node:return ' | '.join(json.dumps(x) for x in node['enum'])
    kind=node.get('type')
    if isinstance(kind,list):return ' | '.join(ts({**node,'type':k}) for k in kind)
    if kind=='object':
        return '{ '+ '; '.join(json.dumps(k)+('' if k in node.get('required',[]) else '?')+': '+ts(v) for k,v in node.get('properties',{}).items())+' }'
    if kind=='array':return 'Array<'+ts(node['items'])+'>'
    return {'string':'string','integer':'number','number':'number','boolean':'boolean','null':'null'}.get(kind,'unknown')
def render(schema,apply_types):
    sp=schema['properties']
    ref=sp['sources']['items']['properties']['refs']['items']
    value=sp['metrics']['items']['properties']['value']
    return '/** Generated proposed CP7 v2 shape. NOT ERP code. Runtime semantic validation mandatory. */\n'+\
        'export type SourceRef = '+ts(ref)+';\nexport type FactValue = '+ts(value)+';\n'+\
        'export type AnalysisRequest = { request_id: string; scope_id: string; effective_as_of: string; known_as_of: string; knowledge_mode: "CURRENT" | "AS_KNOWN" | "RESTATED"; policy_version: string };\n'+\
        'export type AnalysisResult = '+ts(schema)+';\n'+apply_types
if __name__=='__main__':
    file=P/'contracts/backbone.ts';current=file.read_text()
    apply_types=current[current.index('export type ApplyPlanActionRequest'):]
    file.write_text(render(json.loads((P/'contracts/analysis.schema.json').read_text()),apply_types))
