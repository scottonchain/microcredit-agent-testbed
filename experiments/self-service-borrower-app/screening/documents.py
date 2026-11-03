"""Supporting documents: typed, hashed, reduced to structured claims.

A document never changes the decision by itself. An extractor turns it into claims
(who paid, how much, how often, when, in whose name); the dossier compares those
claims with what the applicant said and the policy weighs the result. Two
extractors exist:

- RuleBasedExtractor: labelled text (`amount: 120`, `date: 2026-10-20`, ...). Used
  by the tests and by any intake that pre-fills fields. No network.
- ClaudeExtractor: PDFs, images and free text through the Anthropic SDK with a
  structured output schema. Cost per document is measured from the usage counts
  and a published price table, so the per-assessment cost target (D16: at most
  10 cents) is a measurement, not an assumption. Imported lazily; the package
  works without the SDK installed.

Document bytes stay wherever the lender stores them (never in this repository);
only the hash, the claims and the extractor's notes enter the dossier. A hash seen
on another application is a contradiction (the same pay stub cannot be two people's).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Protocol

DOCUMENT_TYPES = {
    "pay_stub": {"evidences": "repayment_source", "fields": ("party", "amount_usd", "period", "date", "name_on_document")},
    "employment_letter": {"evidences": "repayment_source", "fields": ("party", "amount_usd", "period", "date", "name_on_document")},
    "bank_statement": {"evidences": "repayment_source", "fields": ("party", "amount_usd", "period", "date", "name_on_document")},
    "mobile_money_statement": {"evidences": "repayment_source", "fields": ("party", "amount_usd", "period", "date", "name_on_document")},
    "sales_record": {"evidences": "repayment_source", "fields": ("party", "amount_usd", "period", "date", "name_on_document")},
    "benefit_letter": {"evidences": "repayment_source", "fields": ("party", "amount_usd", "period", "date", "name_on_document")},
    "customer_order": {"evidences": "purpose", "fields": ("party", "amount_usd", "date", "due_date", "name_on_document")},
    "supplier_quote": {"evidences": "purpose", "fields": ("party", "amount_usd", "date", "name_on_document")},
    "backer_attestation": {"evidences": "backing", "fields": ("party", "amount_usd", "date", "name_on_document")},
    "id_document": {"evidences": "identity", "fields": ("name_on_document", "date")},
}
PERIODS = ("weekly", "monthly", "one_off")
MAX_DOCUMENT_BYTES = 8 * 1024 * 1024
MAX_DOCUMENTS = 5
FRESH_DAYS = 90

CLAIM_SCHEMA = {
    "type": "object",
    "properties": {
        "party": {"type": "string", "description": "the employer, customer, supplier, bank or sender named on the document; empty if none"},
        "amount_usd": {"type": "number", "description": "the main amount in US dollars (net pay, monthly inflow, order value, quote total); 0 if none"},
        "period": {"type": "string", "enum": ["weekly", "monthly", "one_off", ""], "description": "how often the amount recurs"},
        "date": {"type": "string", "description": "the document's date or period end, YYYY-MM-DD; empty if none"},
        "due_date": {"type": "string", "description": "for an order: when the customer pays, YYYY-MM-DD; else empty"},
        "name_on_document": {"type": "string", "description": "the person the document is about or addressed to; empty if none"},
        "looks_like": {"type": "string", "description": "what kind of document this appears to be, in a few words"},
        "concerns": {"type": "array", "items": {"type": "string"}, "description": "anything that looks edited, inconsistent, or unlike the claimed type; empty if none"},
    },
    "required": ["party", "amount_usd", "period", "date", "due_date", "name_on_document", "looks_like", "concerns"],
    "additionalProperties": False,
}
EMPTY_CLAIMS = {"party": "", "amount_usd": 0.0, "period": "", "date": "", "due_date": "", "name_on_document": "", "looks_like": "", "concerns": []}


@dataclass
class Document:
    doc_type: str
    filename: str
    sha256: str
    size_bytes: int
    submitted_at: str
    claims: dict = field(default_factory=lambda: dict(EMPTY_CLAIMS))
    extractor: str = "none"
    cost_usd: float = 0.0
    tokens: dict = field(default_factory=dict)
    note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def document_date(self) -> date | None:
        return parse_date(self.claims.get("date", ""))

    def age_days(self, today: date) -> int | None:
        when = self.document_date
        return None if when is None else (today - when).days


def parse_date(text: str) -> date | None:
    text = (text or "").strip()
    if not text:
        return None
    for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d %B %Y", "%B %d, %Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    return None


class Extractor(Protocol):
    name: str

    def extract(self, doc_type: str, filename: str, data: bytes) -> tuple[dict, dict]:
        """Return (claims, meta); meta may hold cost_usd, tokens and note."""


class RuleBasedExtractor:
    """Reads `key: value` lines from a text document. Anything else needs the agent extractor."""
    name = "rules"
    ALIASES = {"amount": "amount_usd", "net": "amount_usd", "net_pay": "amount_usd", "total": "amount_usd",
               "monthly_inflow": "amount_usd", "payer": "party", "employer": "party", "customer": "party",
               "supplier": "party", "bank": "party", "sender": "party", "name": "name_on_document",
               "to": "name_on_document", "period_end": "date", "due": "due_date"}

    def extract(self, doc_type: str, filename: str, data: bytes) -> tuple[dict, dict]:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            return dict(EMPTY_CLAIMS), {"note": "not text; needs the agent extractor"}
        claims = dict(EMPTY_CLAIMS)
        found = 0
        for line in text.splitlines():
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = self.ALIASES.get(key.strip().lower().replace(" ", "_"), key.strip().lower().replace(" ", "_"))
            value = value.strip()
            if key == "amount_usd":
                number = re.sub(r"[^0-9.]", "", value)
                try:
                    claims[key] = float(number)
                    found += 1
                except ValueError:
                    continue
            elif key == "period":
                if value.lower() in PERIODS:
                    claims[key] = value.lower()
                    found += 1
            elif key in ("party", "date", "due_date", "name_on_document", "looks_like"):
                claims[key] = value
                found += 1
            elif key == "concerns" and value:
                claims["concerns"] = [v.strip() for v in value.split(";") if v.strip()]
        note = "" if found else "no labelled fields found"
        return claims, {"note": note}


PRICE_PER_MTOK = {  # USD per million tokens (input, output), from the Anthropic price table, 2026-10-06
    "claude-opus-5-5": (4.0, 20.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-haiku-5-5": (0.10, 0.50),
}
DEFAULT_MODEL = "claude-opus-5-5"
MEDIA_TYPES = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
               ".gif": "image/gif", ".webp": "image/webp"}


class ClaudeExtractor:
    """Reduce a PDF, image or text document to CLAIM_SCHEMA through the Anthropic SDK.

    The model only extracts: it never sees the applicant's answers, so it cannot be
    talked into agreeing with them, and it never scores. Refusals (stop_reason
    "refusal") and malformed output produce empty claims with a note; the dossier then
    treats the document as present but unread, which the policy counts as stated only.
    """
    name = "claude"

    def __init__(self, model: str | None = None, client: Any = None):
        self.model = model or os.environ.get("SCREENING_MODEL", DEFAULT_MODEL)
        self._client = client

    def client(self):
        if self._client is None:
            import anthropic  # imported here so the package works without the SDK
            self._client = anthropic.Anthropic()
        return self._client

    @staticmethod
    def content_block(filename: str, data: bytes) -> dict:
        import base64
        media = MEDIA_TYPES.get(Path(filename).suffix.lower())
        if media == "application/pdf":
            return {"type": "document", "source": {"type": "base64", "media_type": media, "data": base64.b64encode(data).decode()}}
        if media:
            return {"type": "image", "source": {"type": "base64", "media_type": media, "data": base64.b64encode(data).decode()}}
        return {"type": "text", "text": data.decode("utf-8", errors="replace")[:20000]}

    def extract(self, doc_type: str, filename: str, data: bytes) -> tuple[dict, dict]:
        instruction = (f"This file was uploaded as a '{doc_type.replace('_', ' ')}' supporting a small loan application. "
                       "Extract only what the document itself shows. Do not infer missing values; leave them empty or 0. "
                       "Note any sign of editing or inconsistency in 'concerns'.")
        response = self.client().messages.create(
            model=self.model,
            max_tokens=2048,
            messages=[{"role": "user", "content": [self.content_block(filename, data), {"type": "text", "text": instruction}]}],
            output_config={"format": {"type": "json_schema", "schema": CLAIM_SCHEMA}},
        )
        usage = getattr(response, "usage", None)
        tokens = {"input": getattr(usage, "input_tokens", 0) or 0, "output": getattr(usage, "output_tokens", 0) or 0}
        price_in, price_out = PRICE_PER_MTOK.get(self.model, PRICE_PER_MTOK[DEFAULT_MODEL])
        cost = tokens["input"] * price_in / 1e6 + tokens["output"] * price_out / 1e6
        meta = {"cost_usd": round(cost, 6), "tokens": tokens, "model": self.model}
        if getattr(response, "stop_reason", "") == "refusal":
            return dict(EMPTY_CLAIMS), {**meta, "note": "extractor declined to read this document"}
        text = next((b.text for b in response.content if getattr(b, "type", "") == "text"), "")
        try:
            raw = json.loads(text)
        except json.JSONDecodeError:
            return dict(EMPTY_CLAIMS), {**meta, "note": "extractor returned no usable JSON"}
        claims = dict(EMPTY_CLAIMS)
        for key in EMPTY_CLAIMS:
            if key in raw:
                claims[key] = raw[key]
        try:
            claims["amount_usd"] = float(claims["amount_usd"] or 0)
        except (TypeError, ValueError):
            claims["amount_usd"] = 0.0
        if claims["period"] not in PERIODS:
            claims["period"] = ""
        claims["concerns"] = [str(c) for c in (claims.get("concerns") or [])][:10]
        return claims, meta


class HashRegistry:
    """Hashes of documents seen on earlier applications, so a reused document is caught."""

    def __init__(self, path: str | os.PathLike | None = None):
        self.path = Path(path) if path else None
        self.seen: dict[str, str] = {}
        if self.path and self.path.exists():
            try:
                self.seen = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                self.seen = {}

    def owner(self, sha256: str) -> str | None:
        return self.seen.get(sha256)

    def record(self, sha256: str, application_id: str) -> None:
        self.seen.setdefault(sha256, application_id)
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.seen, indent=1, sort_keys=True), encoding="utf-8")


def intake_documents(entries: Iterable[tuple[str, str, bytes]], extractor: Extractor | None = None,
                     now: datetime | None = None) -> list[Document]:
    """Turn (doc_type, filename, bytes) entries into Documents with extracted claims."""
    extractor = extractor or RuleBasedExtractor()
    stamp = (now or datetime.now(timezone.utc)).isoformat()
    documents: list[Document] = []
    for doc_type, filename, data in entries:
        if doc_type not in DOCUMENT_TYPES:
            raise ValueError(f"unknown document type {doc_type!r}")
        if len(data) > MAX_DOCUMENT_BYTES:
            raise ValueError(f"{filename}: larger than {MAX_DOCUMENT_BYTES // (1024 * 1024)} MB")
        if len(documents) >= MAX_DOCUMENTS:
            raise ValueError(f"at most {MAX_DOCUMENTS} documents")
        claims, meta = extractor.extract(doc_type, filename, data)
        documents.append(Document(
            doc_type=doc_type, filename=Path(filename).name, sha256=hashlib.sha256(data).hexdigest(),
            size_bytes=len(data), submitted_at=stamp, claims=claims, extractor=extractor.name,
            cost_usd=float(meta.get("cost_usd", 0.0)), tokens=dict(meta.get("tokens", {})), note=str(meta.get("note", "")),
        ))
    return documents
