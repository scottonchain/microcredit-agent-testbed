#!/usr/bin/env python3
"""
BOOTSTRAP-001 v2 sample workflow
Public-data cleanup or extraction with validation and source provenance.
Reproducible sample for rehearsal. No paid calls enabled.
"""
import csv
import json
from pathlib import Path
from datetime import datetime

INPUT_PATH = Path("data/sample_raw.csv")
OUTPUT_PATH = Path("data/cleaned.csv")
REPORT_PATH = Path("data/schema_report.json")

def load_raw():
    if not INPUT_PATH.exists():
        # synthetic fallback
        INPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(INPUT_PATH, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id","name","value","date"])
            w.writerow(["1","Alice","10","2026-01-01"])
            w.writerow(["2","","20","2026-01-02"])
            w.writerow(["3","Bob","", "bad-date"])
    with open(INPUT_PATH, newline="") as f:
        return list(csv.DictReader(f))

def clean(rows):
    cleaned = []
    errors = []
    for i, r in enumerate(rows, start=2):
        try:
            rid = int(r["id"])
            name = r["name"].strip()
            if not name:
                raise ValueError("missing name")
            val = float(r["value"]) if r["value"].strip() else None
            date = r["date"].strip()
            datetime.fromisoformat(date)
            cleaned.append({"id": rid, "name": name, "value": val, "date": date})
        except Exception as e:
            errors.append({"row": i, "error": str(e), "raw": r})
    return cleaned, errors

def write_outputs(cleaned, errors):
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id","name","value","date"])
        w.writeheader()
        w.writerows(cleaned)
    report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "source": str(INPUT_PATH),
        "rows_in": len(cleaned)+len(errors),
        "rows_out": len(cleaned),
        "errors": errors,
        "schema": {"id": "int", "name": "string", "value": "float|null", "date": "ISO date"},
        "provenance": "public/synthetic sample for rehearsal only"
    }
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)
    return report

if __name__ == "__main__":
    rows = load_raw()
    cleaned, errors = clean(rows)
    report = write_outputs(cleaned, errors)
    print(json.dumps(report, indent=2))
    print(f"Artifact written to {OUTPUT_PATH} and {REPORT_PATH}")
