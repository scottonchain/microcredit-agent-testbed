"""Command line: screen one application folder, or every worked example.

    python3 -m screening --example market-trader
    python3 -m screening --all-examples
    python3 -m screening --application app.json --documents documents.json --pool-record pool.json --out decision.json
    python3 -m screening --questions          # the interview script as JSON (what the app renders)

An application folder holds application.json (the interview answers), documents.json
([{"type": ..., "file": ...}]) and optionally pool-record.json (what demo.mjs --pool-record
wrote). `--extractor claude` reads PDFs and images through the Anthropic SDK and reports
the measured cost; the default rule-based extractor reads labelled text only.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from .documents import HashRegistry, RuleBasedExtractor, intake_documents
from .interview import QUESTIONS, application_from_answers, follow_ups
from .policy import POLICY_VERSION, WEIGHTS, screen

EXAMPLES = Path(__file__).resolve().parent / "examples"


def load_folder(application: Path, documents: Path | None, pool_record: Path | None, extractor, registry=None, today=None):
    answers = json.loads(application.read_text(encoding="utf-8"))
    app = application_from_answers(answers)
    entries = []
    if documents and documents.exists():
        base = documents.parent
        for entry in json.loads(documents.read_text(encoding="utf-8")):
            path = (base / entry["file"]).resolve()
            entries.append((entry["type"], path.name, path.read_bytes()))
    docs = intake_documents(entries, extractor)
    record = json.loads(pool_record.read_text(encoding="utf-8")) if pool_record and pool_record.exists() else None
    owner = registry.owner if registry else None
    dossier, decision = screen(app, docs, record, today=today, seen_document_owner=owner)
    return {
        "policy_version": POLICY_VERSION, "weights": WEIGHTS,
        "application": app.to_dict(), "follow_ups": follow_ups(app, {d.doc_type for d in docs}),
        "documents": [d.to_dict() for d in docs], "dossier": dossier.to_dict(), "decision": decision.to_dict(),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--application", type=Path)
    parser.add_argument("--documents", type=Path, help="documents.json next to the files it names")
    parser.add_argument("--pool-record", type=Path)
    parser.add_argument("--example", help="name of a folder under screening/examples")
    parser.add_argument("--all-examples", action="store_true")
    parser.add_argument("--extractor", choices=("rules", "claude"), default="rules")
    parser.add_argument("--registry", type=Path, help="JSON file of document hashes seen before (private)")
    parser.add_argument("--today", help="YYYY-MM-DD, for reproducible freshness checks")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--questions", action="store_true", help="print the interview script")
    parser.add_argument("--summary", action="store_true", help="one line per case instead of the full record")
    args = parser.parse_args(argv)
    if args.questions:
        print(json.dumps([{k: (v if not isinstance(v, dict) else dict(v)) for k, v in q.items()} for q in QUESTIONS], indent=1))
        return 0
    if args.extractor == "claude":
        from .documents import ClaudeExtractor
        extractor = ClaudeExtractor()
    else:
        extractor = RuleBasedExtractor()
    registry = HashRegistry(args.registry) if args.registry else None
    today = date.fromisoformat(args.today) if args.today else None
    folders: list[tuple[str, Path]] = []
    if args.all_examples:
        folders = [(p.name, p) for p in sorted(EXAMPLES.iterdir()) if p.is_dir()]
    elif args.example:
        folders = [(args.example, EXAMPLES / args.example)]
    elif args.application:
        folders = [(args.application.stem, args.application.parent)]
    else:
        parser.error("give --application, --example or --all-examples")
    results = {}
    for name, folder in folders:
        application = args.application if args.application else folder / "application.json"
        documents = args.documents if args.documents else folder / "documents.json"
        pool = args.pool_record if args.pool_record else folder / "pool-record.json"
        results[name] = load_folder(application, documents, pool, extractor, registry, today)
    if args.out:
        args.out.write_text(json.dumps(results if len(results) > 1 else next(iter(results.values())), indent=1), encoding="utf-8")
    if args.summary or args.all_examples:
        for name, r in results.items():
            dec = r["decision"]
            print(f"{name}: {dec['decision']} tier={dec['tier']} cap={dec['cap_usdc']:.2f} USDC score={dec['score']}/{dec['max_score']} "
                  f"extraction={dec['extraction_cost_usd']:.4f} USD follow-ups={len(r['follow_ups'])}")
            for reason in dec["reasons"]:
                print("   reason:", reason)
    elif not args.out:
        print(json.dumps(next(iter(results.values())), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
