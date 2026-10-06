import copy
import json
from pathlib import Path
import unittest
from validate import validate

class PlanningIntegrity(unittest.TestCase):
    def setUp(self):
        self.model=json.loads(Path(__file__).with_name('model.json').read_text())
    def rejects(self, change):
        change(self.model)
        with self.assertRaises((ValueError, TypeError)): validate(self.model)
    def test_current_model(self): validate(self.model)
    def test_duplicate_id(self): self.rejects(lambda m:m['entities'].append(copy.deepcopy(m['entities'][0])))
    def test_dangling_edge(self): self.rejects(lambda m:m['edges'][0].update(target_id='agent:missing'))
    def test_containment_cycle(self): self.rejects(lambda m:m['entities'][0].update(parent_id='project:microcredit'))
    def test_inference_without_observation(self):
        self.rejects(lambda m:next(c for c in m['claims'] if c['epistemics']['status']=='inferred').update(derived_from_claim_ids=[]))
    def test_provenance_cycle(self):
        def mutation(m):
            a,b=m['evidence'][:2]
            a.update(kind='internal_report',derived_from_ids=[b['id']]);b.update(kind='internal_report',derived_from_ids=[a['id']])
        self.rejects(mutation)
    def test_mirror_cannot_be_independent_witness(self):
        self.rejects(lambda m:next(e for e in m['evidence'] if e['kind']=='mirror').update(origin_group='fake-independent-origin'))
    def test_action_cycle(self):
        self.rejects(lambda m:m['actions'][0].update(dependency_action_ids=[m['actions'][0]['id']]))
    def test_completion_before_dependency(self):
        self.rejects(lambda m:next(a for a in m['actions'] if a['id']=='action:codex-show-diff').update(due_at='2026-10-07T12:00:00Z'))
    def test_false_completion(self): self.rejects(lambda m:m['actions'][0].update(status='done',outcome_evidence_ids=[]))
    def test_unconsented_activity(self):
        self.rejects(lambda m:m['actions'][0].update(status='in_progress',external_consent='pending'))
    def test_fabricated_consensus(self): self.rejects(lambda m:m['decisions'][0].update(status='agreed',assents=[]))
    def test_assent_wrong_revision(self):
        self.rejects(lambda m:m['decisions'][0].update(assents=[{'agent_id':'agent:claude','evidence_id':m['evidence'][0]['id'],'version':'decision:old'}]))
    def test_unknown_field(self): self.rejects(lambda m:m['actions'][0].update(authority_to_spend=True))
    def test_ambiguous_time(self): self.rejects(lambda m:m.update(updated_at='tomorrow'))

if __name__=='__main__': unittest.main()
