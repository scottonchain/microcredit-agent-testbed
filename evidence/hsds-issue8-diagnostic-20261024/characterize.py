"""Characterization only: synthetic tool inputs, not normative HSDS profiles.
Execute only four reviewed function definitions; no module imports/CLI/profile downloads.
"""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import pathlib
import traceback

ROOT = Path(__file__).parent
FUNCTIONS = {'compile_definitions', 'compile_schema', 'remove_one_to_many', '_compile_schemas'}
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('main_source', type=Path)
parser.add_argument('pr12_source', type=Path)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
ROOT = args.output
ROOT.mkdir(parents=True, exist_ok=True)
SOURCES = {
    'main-8ca351861dd82dfc347140123f7764fde6da1e9a': args.main_source,
    'pr12-206560f42291c66e1adfe8b343428281c4b34d1b': args.pr12_source,
}
EXPECTED_HASHES = ['29a7ac485773408f40d7cf62e2a201770650ec33450f5330fb09d1e0196b9416', 'aab8a615f4d832430a05555e1fdb8736bf8db313f7931edb47d5de2085f32562']
assert [hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCES.values()] == EXPECTED_HASHES


def load_functions(source):
    tree = ast.parse(source.read_text(), filename=str(source))
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in FUNCTIONS]
    assert {n.name for n in nodes} == FUNCTIONS
    assert all(not n.decorator_list for n in nodes)
    ns = {'os': os, 'pathlib': pathlib, 'json': json, 'copy': copy}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), ns)
    return ns

def schema(name, order):
    return {'name': name, 'type': 'object', 'properties': {}, 'datapackage_metadata': {'order': order}}

results = []
for label, source in SOURCES.items():
    ns = load_functions(source)
    for case in ['control', 'removed_entity', 'removed_link_only']:
        case_root = ROOT / 'runs' / label / case
        inputs, outputs = case_root / 'input', case_root / 'output'
        inputs.mkdir(parents=True, exist_ok=True)
        # Fresh output per run prevents stale generated files masking failure.
        outputs.mkdir(parents=True, exist_ok=True)
        for p in outputs.glob('*.json'):
            p.unlink()
        data = {'service': schema('service', 1), 'organization': schema('organization', 2)}
        if case != 'removed_entity':
            data['service_at_location'] = schema('service_at_location', 3)
        if case == 'control':
            data['service']['properties']['service_at_locations'] = {'type': 'array', 'items': {'$ref': 'service_at_location.json'}}
        for p in inputs.glob('*.json'):
            p.unlink()
        for name, value in data.items():
            (inputs / (name + '.json')).write_text(json.dumps(value, indent=2) + '\n')
        before = {p.name: p.read_bytes() for p in inputs.glob('*.json')}
        result = {'source': label, 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'case': case}
        try:
            ns['_compile_schemas'](inputs, outputs)
            result['outcome'] = 'success'
        except Exception as e:
            result['outcome'] = type(e).__name__
            result['message'] = str(e)
            # Exception class/message suffice; omit execution-machine paths.
        result['outputs'] = sorted(p.name for p in outputs.glob('*.json'))
        result['inputs_unchanged'] = before == {p.name: p.read_bytes() for p in inputs.glob('*.json')}
        assert result['inputs_unchanged']
        if case == 'control':
            assert result['outcome'] == 'success' and len(result['outputs']) == 10
        elif case == 'removed_entity':
            assert result['outcome'] == 'KeyError' and result['message'] == "'service_at_location.json'" and len(result['outputs']) == 7
        else:
            assert result['outcome'] == 'KeyError' and result['message'] == "'service_at_locations'" and len(result['outputs']) == 7
        results.append(result)
        print(label, case, result['outcome'], result.get('message', ''), 'outputs=' + str(len(result['outputs'])))
(ROOT / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
print('All six characterization checks passed. This does not assert desired behavior or schema conformance.')
