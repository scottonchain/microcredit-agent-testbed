#!/usr/bin/env python3
"""Validate structure, reference integrity, provenance, and planning semantics."""
import argparse
from collections import Counter
from datetime import datetime
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from schema import WorldModel

ROOT = Path(__file__).resolve().parent

def format_model(data):
    """Keep sections and one complete record per line, without changing values."""
    encode = lambda value: json.dumps(value, ensure_ascii=False, separators=(',', ':'))
    lines = ['{']
    for index, (key, value) in enumerate(data.items()):
        suffix = ',' if index < len(data) - 1 else ''
        if isinstance(value, list) and value:
            lines.append('  ' + encode(key) + ': [')
            lines.extend('    ' + encode(record) + (',' if i < len(value) - 1 else '')
                         for i, record in enumerate(value))
            lines.append('  ]' + suffix)
        else:
            lines.append('  ' + encode(key) + ': ' + encode(value) + suffix)
    return '\n'.join([*lines, '}']) + '\n'

def validate(data):
    WorldModel.model_validate(data)
    errors = []
    kinds = ['entities', 'evidence', 'claims', 'edges', 'hypotheses', 'actions', 'decisions', 'open_questions', 'coverage']
    records = [r for kind in kinds for r in data[kind]]
    duplicates = [k for k, n in Counter(r['id'] for r in records).items() if n > 1]
    if duplicates:
        errors.append('Duplicate IDs: ' + ', '.join(duplicates))
    maps = {kind: {r['id']: r for r in data[kind]} for kind in kinds}
    all_ids = {r['id'] for r in records}
    def refs(values, kind, at):
        for value in values:
            if value is not None and value not in (all_ids if kind == 'all' else maps[kind]):
                errors.append(f'{at}: unknown {kind} reference {value}')
    def acyclic(adjacency, name):
        active, done = set(), set()
        def visit(node):
            if node in active:
                errors.append(f'{name}: cycle at {node}')
                return
            if node in done:
                return
            active.add(node)
            for target in adjacency.get(node, []):
                visit(target)
            active.remove(node)
            done.add(node)
        for node in adjacency:
            visit(node)
    def timestamp(value, at):
        if value is None:
            return
        try:
            if not value.endswith('Z') or datetime.fromisoformat(value.replace('Z', '+00:00')).tzinfo is None:
                raise ValueError()
        except (ValueError, TypeError):
            errors.append(f'{at}: require RFC3339 UTC time ending Z')
    timestamp(data['updated_at'], 'updated_at')
    for r in records:
        if not re.fullmatch(r'[a-z][a-z0-9_-]*:[a-z0-9][a-z0-9._-]*', r['id']):
            errors.append(f"Invalid stable ID: {r['id']}")
    for e in data['entities']:
        refs([e['parent_id'], e['owner_id']], 'entities', e['id'])
        if e['goal_model']:
            for values in e['goal_model'].values(): refs(values, 'claims', e['id'])
        if e['identity']: refs(e['identity']['basis_evidence_ids'], 'evidence', e['id'])
    acyclic({r['id']: [r['parent_id']] if r['parent_id'] else [] for r in data['entities']}, 'containment')
    for e in data['evidence']:
        refs([e['author_id'], e['observer_id']], 'entities', e['id'])
        refs(e['derived_from_ids'], 'evidence', e['id'])
        timestamp(e['published_at'], e['id'] + '/published_at')
        timestamp(e['retrieved_at'], e['id'] + '/retrieved_at')
        if e['content_sha256'] and not re.fullmatch('[0-9a-f]{64}', e['content_sha256']):
            errors.append(e['id'] + ': invalid source fingerprint')
        if bool(e['content_sha256']) != bool(e['fingerprint_scope']):
            errors.append(e['id'] + ': fingerprint and scope must be present together')
        if e['kind'] == 'primary_public' and e['derived_from_ids']:
            errors.append(e['id'] + ': a mirror is not primary evidence')
        if e['kind'] == 'mirror' and not e['derived_from_ids']:
            errors.append(e['id'] + ': mirror requires originating evidence')
        for original in e['derived_from_ids']:
            if e['kind']=='mirror' and maps['evidence'].get(original,{}).get('origin_group') != e['origin_group']:
                errors.append(e['id'] + ': mirror cannot mint a new origin group')
    acyclic({r['id']:r['derived_from_ids'] for r in data['evidence']}, 'provenance')
    for c in data['claims']:
        refs([c['subject_id']], 'entities', c['id'])
        ep = c['epistemics']
        refs(ep['supporting_evidence_ids'] + ep['counterevidence_ids'], 'evidence', c['id'])
        refs(c['supersedes_ids'], 'claims', c['id'])
        refs(c['derived_from_claim_ids'], 'claims', c['id'])
        if ep['status'] == 'inferred' and not ep['falsifier']:
            errors.append(c['id'] + ': inferred claim needs a falsifier')
        if ep['status'] == 'inferred' and not any(maps['claims'].get(i,{}).get('epistemics',{}).get('status')=='observed' for i in c['derived_from_claim_ids']):
            errors.append(c['id'] + ': inference needs an observed supporting claim')
        if ep['status'] == 'contested' and not ep['counterevidence_ids']:
            errors.append(c['id'] + ': contested claim needs counterevidence')
        if ep['status'] == 'directive' and not any(maps['evidence'].get(i,{}).get('kind') == 'operator_direction' for i in ep['supporting_evidence_ids']):
            errors.append(c['id'] + ': directive needs operator-direction provenance')
        timestamp(c['freshness']['observed_at'], c['id'] + '/observed_at')
        timestamp(c['freshness']['recheck_by'], c['id'] + '/recheck_by')
    acyclic({r['id']:r['supersedes_ids'] for r in data['claims']}, 'claim supersession')
    acyclic({r['id']:r['derived_from_claim_ids'] for r in data['claims']}, 'claim inference')
    for e in data['edges']:
        refs([e['source_id'],e['target_id']], 'entities', e['id'])
        refs(e['claim_ids'], 'claims', e['id'])
    dep_graph = {}
    for e in data['edges']:
        if e['relation'] == 'depends_on': dep_graph.setdefault(e['source_id'],[]).append(e['target_id'])
    acyclic(dep_graph, 'entity dependencies')
    for h in data['hypotheses']:
        refs(h['subject_ids'], 'entities', h['id'])
        refs(h['claim_ids'], 'claims', h['id'])
        for p in h['predictions']: timestamp(p['check_by'], h['id'] + '/check_by')
    for a in data['actions']:
        refs([a['owner_id']]+a['counterpart_ids']+a['goal_ids'], 'entities', a['id'])
        refs(a['rationale_claim_ids'], 'claims', a['id'])
        refs(a['dependency_action_ids'], 'actions', a['id'])
        refs(a['outcome_evidence_ids'], 'evidence', a['id'])
        timestamp(a['not_before'], a['id']+'/not_before'); timestamp(a['due_at'], a['id']+'/due_at')
        if a['due_at']:
            deadline = datetime.fromisoformat(a['due_at'].replace('Z', '+00:00'))
            for dependency_id in a['dependency_action_ids']:
                dependency = maps['actions'].get(dependency_id, {})
                if dependency.get('due_at') and dependency.get('status') != 'done':
                    dependency_deadline = datetime.fromisoformat(dependency['due_at'].replace('Z', '+00:00'))
                    if dependency_deadline > deadline:
                        errors.append(a['id'] + ': completion deadline precedes unfinished dependency ' + dependency_id)
        if a['status'] == 'done' and not a['outcome_evidence_ids']:
            errors.append(a['id'] + ': done requires outcome evidence')
        if a['status'] in ['in_progress','done'] and a['owner_acceptance'] == 'requested':
            errors.append(a['id'] + ': activity requires owner acknowledgment')
        if a['external_consent'] in ['pending','declined'] and a['status'] in ['ready','in_progress','done']:
            errors.append(a['id'] + ': external activity cannot progress without consent')
    acyclic({r['id']:r['dependency_action_ids'] for r in data['actions']}, 'action dependencies')
    for d in data['decisions']:
        refs([d['owner_id']], 'entities', d['id']); refs(d['claim_ids'],'claims',d['id'])
        refs(d['action_ids'],'actions',d['id']); refs(d['discussion_evidence_ids'],'evidence',d['id'])
        refs(d['supersedes_ids'],'decisions',d['id'])
        for assent in d['assents']:
            if set(assent) != {'agent_id','evidence_id','version'}:
                errors.append(d['id'] + ': assent must bind agent, evidence and version')
            refs([assent.get('agent_id')], 'entities', d['id'])
            refs([assent.get('evidence_id')], 'evidence', d['id'])
            if assent.get('version') != d['id']:
                errors.append(d['id'] + ': assent must match this exact decision version')
        if d['status']=='agreed' and not {'agent:coordinator','agent:claude'}.issubset({a.get('agent_id') for a in d['assents']}):
            errors.append(d['id'] + ': joint decision requires explicit coordinator and Claude assent')
    for q in data['open_questions']:
        refs([q['owner_id']],'entities',q['id']); refs(q['related_ids'],'all',q['id']); refs(q['blocks_action_ids'],'actions',q['id'])
    for c in data['coverage']: timestamp(c['observed_at'], c['id'])
    refs(list(data['governance']['adoption']), 'entities', 'governance/adoption')
    if errors: raise ValueError('\n'.join(errors))
    return {kind:len(data[kind]) for kind in kinds}

def main():
    p=argparse.ArgumentParser(); p.add_argument('model',nargs='?',default=str(ROOT/'model.json')); p.add_argument('--check-schema',action='store_true')
    p.add_argument('--format', action='store_true', help='after validation, atomically store compact records; all values are preserved')
    args=p.parse_args()
    path=Path(args.model)
    data=json.loads(path.read_text(encoding='utf-8'))
    result=validate(data)
    if args.check_schema:
        expected=WorldModel.model_json_schema(); expected['$schema']='https://json-schema.org/draft/2020-12/schema'
        if json.loads((ROOT/'schema.json').read_text()) != expected: raise ValueError('schema.json differs from schema.py; regenerate')
    if args.format:
        temporary=None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as handle:
                temporary=Path(handle.name)
                handle.write(format_model(data))
                handle.flush()
                os.fchmod(handle.fileno(), path.stat().st_mode & 0o777)
            os.replace(temporary, path)
        finally:
            if temporary is not None: temporary.unlink(missing_ok=True)
    print(json.dumps({'valid':True,'counts':result}))

if __name__=='__main__':
    try: main()
    except Exception as e:
        print(str(e),file=sys.stderr);sys.exit(1)
