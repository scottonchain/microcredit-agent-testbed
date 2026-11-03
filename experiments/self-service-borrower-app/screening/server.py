"""A local intake page: seven taps, optional evidence and uploads, a decision with reasons.

    python3 -m screening.server --port 8765 --data-dir ~/private-intake --pool-record pool.json

This is the lender-side prototype of the real app's application screen. It runs on the
lender's own machine, not on the public test network: answers and documents are stored
under --data-dir (default ~/.microcredit-intake, outside any repository), each
application in its own folder with the dossier and the decision. The practice app on
the test network keeps its public chat; this page is what replaces it when money is real.

Standard library only. No cookies, no analytics, no outside calls (the Claude extractor
is opt-in with --extractor claude and needs the Anthropic SDK and a key).
"""
from __future__ import annotations

import argparse
import html
import json
import secrets
import sys
from datetime import date, datetime, timezone
from email.parser import BytesParser
from email.policy import HTTP
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .documents import DOCUMENT_TYPES, HashRegistry, MAX_DOCUMENT_BYTES, RuleBasedExtractor, intake_documents
from .interview import (CORE, DOCUMENT_LABELS, EVIDENCE, InterviewError, QUESTIONS, application_from_answers, follow_ups)
from .policy import POLICY_VERSION, screen

STYLE = """
body{font-family:system-ui,sans-serif;max-width:640px;margin:0 auto;padding:16px;line-height:1.45;color:#1b1b1b;background:#fafaf8}
.card{background:#fff;border:1px solid #ddd;border-radius:12px;padding:14px;margin:12px 0}
.q{font-weight:600;margin:6px 0}.chips label{display:inline-block;margin:4px 6px 4px 0}
.chips input{position:absolute;opacity:0}.chips span{display:inline-block;padding:8px 12px;border:1px solid #888;border-radius:20px;cursor:pointer}
.chips input:checked+span{background:#0b5a4a;color:#fff;border-color:#0b5a4a}
input[type=text],input[type=number],textarea{width:100%;padding:8px;border:1px solid #999;border-radius:8px;box-sizing:border-box}
button{background:#0b5a4a;color:#fff;border:0;border-radius:10px;padding:12px 18px;font-size:16px;cursor:pointer}
.muted{color:#555;font-size:14px}.ok{background:#e4f3ec}.bad{background:#fbe9e7}.reason{margin:4px 0 4px 12px}
details summary{cursor:pointer;font-weight:600}
"""


def render_form(message: str = "", values: dict | None = None) -> str:
    values = values or {}
    parts = [f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
             f"<title>Apply for a small loan</title><style>{STYLE}</style><h1>Apply for a small loan</h1>"
             "<p class=muted>Seven quick questions. Then, for a real loan, your name, a sentence in your own words and something that shows your income. "
             "Your answers and documents stay private with the lender; they are used only to decide this loan and to give you the reasons. "
             "No question asks who you are beyond your name.</p>"]
    if message:
        parts.append(f"<div class='card bad'>{html.escape(message)}</div>")
    parts.append("<form method=post action=/apply enctype=multipart/form-data>")
    for stage, title in ((CORE, "Seven taps"), (EVIDENCE, "For a real loan")):
        parts.append(f"<div class=card><h2>{title}</h2>")
        for q in QUESTIONS:
            if q["stage"] != stage:
                continue
            key, kind = q["key"], q["kind"]
            parts.append(f"<div class=q>{html.escape(q['text'])}</div>")
            if kind == "choice":
                parts.append("<div class=chips>")
                for value, label in q["choices"].items():
                    checked = " checked" if str(values.get(key, "")) == value else ""
                    parts.append(f"<label><input type=radio name={key} value='{html.escape(value)}'{checked}><span>{html.escape(label)}</span></label>")
                parts.append("</div>")
            elif kind == "number" and q.get("chips"):
                parts.append("<div class=chips>")
                for chip in q["chips"]:
                    checked = " checked" if str(values.get(key, "")) == str(chip) else ""
                    parts.append(f"<label><input type=radio name={key} value='{chip:g}'{checked}><span>${chip:g}</span></label>")
                parts.append(f"</div><input type=number name={key}_other step=0.01 min=1 placeholder='or another amount'>")
            elif kind == "number":
                parts.append(f"<input type=number name={key} step=0.01 min=0 value='{html.escape(str(values.get(key, '')))}'>")
            elif kind == "boolean":
                parts.append(f"<label><input type=checkbox name={key} value=on> I agree</label>")
            elif key in ("purpose_text", "documents_note"):
                parts.append(f"<textarea name={key} rows=3>{html.escape(str(values.get(key, '')))}</textarea>")
            else:
                parts.append(f"<input type=text name={key} value='{html.escape(str(values.get(key, '')))}'>")
            if q.get("asks_for"):
                parts.append(f"<div class=muted>Helps: {html.escape(q['asks_for'])}</div>")
        if stage == EVIDENCE:
            parts.append("<div class=q>Show something (up to three files: a photo or PDF of a pay stub, statement, sales record, order or quote)</div>")
            for i in range(1, 4):
                options = "".join(f"<option value={t}>{html.escape(DOCUMENT_LABELS[t])}</option>" for t in DOCUMENT_TYPES)
                parts.append(f"<div><select name=doc{i}_type><option value=''>type of document</option>{options}</select> <input type=file name=doc{i}></div>")
        parts.append("</div>")
    parts.append("<div class=card><label><input type=radio name=stage value=core> Practice only (seven taps)</label><br>"
                 "<label><input type=radio name=stage value=evidence checked> Real loan (with evidence)</label><br><br>"
                 "<button type=submit>Send my application</button></div></form>")
    return "".join(parts)


def render_decision(result: dict, application_id: str) -> str:
    dec, asks = result["decision"], result["follow_ups"]
    ok = dec["decision"] == "approve"
    parts = [f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
             f"<title>Your application</title><style>{STYLE}</style><h1>Your application</h1><p class=muted>Reference {application_id}</p>"]
    if ok:
        parts.append(f"<div class='card ok'><h2>Yes, up to ${dec['cap_usdc']:.2f}</h2><p>Score {dec['score']} of {dec['max_score']}. "
                     f"The loan needs ${dec['backing_required_usdc']:.2f} of backing in place; ${dec['backing_available_usdc']:.2f} was found.</p>")
        if dec["reasons"]:
            parts.append("<p>Why not the full amount:</p>" + "".join(f"<div class=reason>{html.escape(r)}</div>" for r in dec["reasons"]))
        parts.append("</div>")
    else:
        parts.append(f"<div class='card bad'><h2>Not yet</h2><p>Score {dec['score']} of {dec['max_score']}. The main reasons:</p>"
                     + "".join(f"<div class=reason>{html.escape(r)}</div>" for r in dec["reasons"]) + "</div>")
    if asks:
        parts.append("<div class=card><h2>What would help</h2>" + "".join(f"<div class=reason>{html.escape(a)}</div>" for a in asks) + "</div>")
    comp = dec["components"]
    parts.append("<details class=card><summary>How the score was made (policy " + html.escape(dec["policy_version"]) + ")</summary><table>"
                 + "".join(f"<tr><td>{html.escape(k.replace('_', ' '))}</td><td>{v} of {result['weights'][k]}</td></tr>" for k, v in comp.items())
                 + "</table><p class=muted>Document reading cost: $" + f"{dec['extraction_cost_usd']:.4f}" + "</p></details>")
    if dec["notes"]:
        parts.append("<div class=card><h2>Notes</h2>" + "".join(f"<div class=reason>{html.escape(n)}</div>" for n in dec["notes"]) + "</div>")
    parts.append("<p><a href=/>Start again</a></p>")
    return "".join(parts)


def parse_multipart(content_type: str, body: bytes) -> tuple[dict, list[tuple[str, str, bytes]]]:
    message = BytesParser(policy=HTTP).parsebytes(b"Content-Type: " + content_type.encode() + b"\r\nMIME-Version: 1.0\r\n\r\n" + body)
    fields: dict[str, str] = {}
    files: list[tuple[str, str, bytes]] = []
    for part in message.walk():
        if part.is_multipart():
            continue
        name = part.get_param("name", header="content-disposition")
        if not name:
            continue
        filename = part.get_filename()
        payload = part.get_payload(decode=True) or b""
        if filename:
            if payload:
                files.append((name, filename, payload))
        else:
            fields[name] = payload.decode("utf-8", errors="replace").strip()
    return fields, files


class Intake:
    def __init__(self, data_dir: Path, pool_record: dict | None, extractor):
        self.data_dir = data_dir
        self.pool_record = pool_record
        self.extractor = extractor
        self.registry = HashRegistry(data_dir / "document-hashes.json")

    def apply(self, fields: dict, files: list[tuple[str, str, bytes]]) -> tuple[str, dict]:
        stage = fields.get("stage", EVIDENCE)
        if not fields.get("amount_usdc") and fields.get("amount_usdc_other"):
            fields["amount_usdc"] = fields["amount_usdc_other"]
        app = application_from_answers(fields, stage=stage)
        entries = []
        for field_name, filename, data in files:
            doc_type = fields.get(field_name + "_type", "")
            if not doc_type:
                raise InterviewError(f"{filename}: choose the type of document")
            if len(data) > MAX_DOCUMENT_BYTES:
                raise InterviewError(f"{filename}: too large")
            entries.append((doc_type, filename, data))
        docs = intake_documents(entries, self.extractor)
        application_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-") + secrets.token_hex(3)
        dossier, decision = screen(app, docs, self.pool_record, today=date.today(), seen_document_owner=self.registry.owner)
        result = {"policy_version": POLICY_VERSION, "weights": __import__("screening.policy", fromlist=["WEIGHTS"]).WEIGHTS,
                  "application": app.to_dict(), "follow_ups": follow_ups(app, {d.doc_type for d in docs}),
                  "documents": [d.to_dict() for d in docs], "dossier": dossier.to_dict(), "decision": decision.to_dict()}
        folder = self.data_dir / application_id
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "record.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
        for (doc_type, filename, data), doc in zip(entries, docs):
            (folder / f"{doc.sha256[:16]}-{Path(filename).name}").write_bytes(data)
            self.registry.record(doc.sha256, application_id)
        return application_id, result


def make_handler(intake: Intake):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: str):
            data = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path.startswith("/decision/"):
                folder = intake.data_dir / Path(self.path).name
                record = folder / "record.json"
                if record.exists():
                    return self._send(200, render_decision(json.loads(record.read_text(encoding="utf-8")), folder.name))
                return self._send(404, "<p>No such application.</p>")
            return self._send(200, render_form())

        def do_POST(self):
            if self.path != "/apply":
                return self._send(404, "<p>Not found.</p>")
            length = int(self.headers.get("Content-Length", "0"))
            if length > 4 * MAX_DOCUMENT_BYTES:
                return self._send(413, "<p>Too large.</p>")
            body = self.rfile.read(length)
            try:
                fields, files = parse_multipart(self.headers.get("Content-Type", ""), body)
                application_id, result = intake.apply(fields, files)
            except (InterviewError, ValueError) as error:
                return self._send(400, render_form(str(error)))
            self._send(200, render_decision(result, application_id))

        def log_message(self, fmt, *args):  # no request logging: the path carries nothing, but keep it quiet anyway
            pass
    return Handler


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--data-dir", type=Path, default=Path.home() / ".microcredit-intake")
    parser.add_argument("--pool-record", type=Path, help="JSON from demo.mjs --pool-record (the chain's view of backer and borrower)")
    parser.add_argument("--extractor", choices=("rules", "claude"), default="rules")
    args = parser.parse_args(argv)
    if args.extractor == "claude":
        from .documents import ClaudeExtractor
        extractor = ClaudeExtractor()
    else:
        extractor = RuleBasedExtractor()
    record = json.loads(args.pool_record.read_text(encoding="utf-8")) if args.pool_record else None
    args.data_dir.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(Intake(args.data_dir, record, extractor)))
    print(f"intake on http://{args.host}:{args.port}/  records in {args.data_dir}  policy {POLICY_VERSION}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
