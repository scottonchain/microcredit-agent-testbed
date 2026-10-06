"""Typed planning model; generate JSON Schema with `python schema.py`."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
import json

class Record(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

class Freshness(Record):
    observed_at: str
    recheck_by: str | None
    recheck_on: list[str]

class GoalModel(Record):
    declared_claim_ids: list[str]
    inferred_claim_ids: list[str]
    engagement_claim_ids: list[str]
    constraint_claim_ids: list[str]

class Identity(Record):
    controller_independence: Literal['internal_team', 'unverified', 'verified_independent', 'shared_controller']
    basis_evidence_ids: list[str]
    note: str

class Entity(Record):
    id: str
    kind: Literal['ecosystem', 'project', 'agent', 'repository', 'artifact', 'workstream', 'outcome', 'venue']
    name: str
    parent_id: str | None
    owner_id: str | None
    urls: list[str]
    goal_model: GoalModel | None
    identity: Identity | None

class Evidence(Record):
    id: str
    kind: Literal['primary_public', 'internal_report', 'mirror', 'operator_direction', 'repository_artifact']
    url: str
    locator: str
    author_id: str
    observer_id: str
    published_at: str | None
    retrieved_at: str
    summary: str
    content_sha256: str | None
    fingerprint_scope: str | None
    origin_group: str
    derived_from_ids: list[str]
    limitations: list[str]

class Epistemics(Record):
    status: Literal['observed', 'reported', 'inferred', 'contested', 'superseded', 'retracted', 'directive']
    confidence: Literal['high', 'medium', 'low', 'unassessed']
    rationale: str
    supporting_evidence_ids: list[str] = Field(min_length=1)
    counterevidence_ids: list[str]
    falsifier: str | None

class Claim(Record):
    id: str
    subject_id: str
    predicate: str
    statement: str
    epistemics: Epistemics
    freshness: Freshness
    supersedes_ids: list[str]
    derived_from_claim_ids: list[str]

class Edge(Record):
    id: str
    source_id: str
    relation: Literal['pursues', 'contributes_to', 'benefits_from', 'collaborates_with', 'supports', 'depends_on', 'owned_by', 'governs']
    target_id: str
    claim_ids: list[str] = Field(min_length=1)

class Prediction(Record):
    observable: str
    disconfirming_observation: str
    check_by: str | None

class Hypothesis(Record):
    id: str
    subject_ids: list[str] = Field(min_length=1)
    theory: str
    claim_ids: list[str] = Field(min_length=1)
    alternative_explanations: list[str] = Field(min_length=1)
    predictions: list[Prediction] = Field(min_length=1)
    confidence: Literal['high', 'medium', 'low']
    confidence_scope: str

class Action(Record):
    id: str
    title: str
    owner_id: str
    counterpart_ids: list[str]
    status: Literal['proposed', 'ready', 'in_progress', 'blocked', 'done', 'cancelled']
    owner_acceptance: Literal['requested', 'acknowledged', 'existing_commitment']
    goal_ids: list[str] = Field(min_length=1)
    rationale_claim_ids: list[str] = Field(min_length=1)
    dependency_action_ids: list[str]
    deliverable: str
    acceptance_criteria: list[str] = Field(min_length=1)
    not_before: str | None
    triggers: list[str] = Field(min_length=1)
    due_at: str | None
    external_consent: Literal['not_required', 'already_scoped', 'pending', 'declined']
    permission_basis: str
    spending: Literal['none', 'requires_separate_authorization', 'existing_authorized_commitment']
    stop_conditions: list[str] = Field(min_length=1)
    outcome_evidence_ids: list[str]

class Assent(Record):
    agent_id: str
    evidence_id: str
    version: str

class Decision(Record):
    id: str
    status: Literal['provisional', 'agreed', 'superseded']
    owner_id: str
    recommendation: str
    claim_ids: list[str]
    action_ids: list[str]
    discussion_evidence_ids: list[str]
    assents: list[Assent]
    supersedes_ids: list[str]

class OpenQuestion(Record):
    id: str
    owner_id: str
    question: str
    related_ids: list[str]
    resolution_evidence_needed: str
    blocks_action_ids: list[str]

class Coverage(Record):
    id: str
    scope: str
    method: str
    observed_at: str
    limitations: list[str]

class Governance(Record):
    authority_order: list[str]
    planning_rule: str
    update_protocol: list[str]
    conflict_rule: str
    freshness_rule: str
    provenance_rule: str
    access_rule: str
    adoption: dict[str, Literal['requested', 'acknowledged', 'verified_use']]

class WorldModel(Record):
    schema_version: Literal['1.0.0']
    model_version: str
    updated_at: str
    canonical_url: str
    state: Literal['draft', 'active']
    governance: Governance
    coverage: list[Coverage]
    entities: list[Entity]
    evidence: list[Evidence]
    claims: list[Claim]
    edges: list[Edge]
    hypotheses: list[Hypothesis]
    actions: list[Action]
    decisions: list[Decision]
    open_questions: list[OpenQuestion]

if __name__ == '__main__':
    schema = WorldModel.model_json_schema()
    schema['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
    print(json.dumps(schema, indent=2) + '\n', end='')
