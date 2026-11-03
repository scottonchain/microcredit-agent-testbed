"""Trust interview, document intake and deterministic policy for first-time borrowers.

The pieces, in the order an application moves through them:

- interview: seven low-load questions, then the evidence stage; follow-up questions.
- documents: uploaded documents, hashed and reduced to claims by an extractor
  (rule-based for labelled text, Claude for PDFs and images, cost measured).
- dossier: every statement tagged stated, evidenced or verified; contradictions coded.
- policy: published weights, the score, the cap and the adverse-action reasons.

Policy code decides; the agent only extracts and flags (MANDATORY_CREDIT_OFFICER_COMPARISON.md).
Nothing here creates credit: a first loan still needs a named backer's stake or the
applicant's own deposit on-chain, and the cap never exceeds that backing.
"""
from .interview import (Application, QUESTIONS, PROHIBITED_KEYS, CORE, EVIDENCE, follow_ups,
                        application_from_answers, InterviewError)
from .documents import Document, DOCUMENT_TYPES, RuleBasedExtractor, ClaudeExtractor, HashRegistry, intake_documents
from .dossier import Dossier, build_dossier
from .policy import Decision, POLICY_VERSION, WEIGHTS, decide, screen

__all__ = [
    "Application", "QUESTIONS", "PROHIBITED_KEYS", "CORE", "EVIDENCE", "follow_ups", "application_from_answers", "InterviewError",
    "Document", "DOCUMENT_TYPES", "RuleBasedExtractor", "ClaudeExtractor", "HashRegistry", "intake_documents",
    "Dossier", "build_dossier",
    "Decision", "POLICY_VERSION", "WEIGHTS", "decide", "screen",
]
