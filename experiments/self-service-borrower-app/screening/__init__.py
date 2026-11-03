"""Trust interview, document intake and deterministic policy for first-time borrowers.

Work in progress (direction D16, requirement 1). Pieces land in this order:
interview (done), documents, dossier, policy, intake server, tests.
Policy code decides; the agent only extracts and flags. Nothing here creates credit.
"""
from .interview import Application, QUESTIONS, PROHIBITED_KEYS, follow_ups, application_from_answers

__all__ = ["Application", "QUESTIONS", "PROHIBITED_KEYS", "follow_ups", "application_from_answers"]
