"""Offline evidence gate. No network, credentials, signatures or real settlement."""
import hashlib
import json


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def natural(value):
    return type(value) is int and value >= 0


def reconcile(grant, usage, invoice, *, payload, now, acceptance, payment):
    """Return a simulated accounting decision; unknown consumption is never zero.

    Money is integer micro-USDC. Unit prices in this fixture are also integer
    micro-USDC. The caller supplies already-collected evidence, never authority
    to debit a wallet. Identity labels here are assertions, not authentication.
    """
    result = {"mode": "offline_simulation", "usage_micro_usdc": None,
              "simulation_settlement_eligible": False, "real_payment_authorized": False,
              "decision": "hold", "reasons": [], "meter_is_payee": None}
    reasons = result["reasons"]
    needed = ("grant_id", "payload_sha256", "authorizer_id", "provider_id", "meter_id")
    if not all(isinstance(grant.get(k), str) and grant[k] for k in needed):
        reasons.append("invalid_grant_identity")
    if not all(natural(grant.get(k)) for k in ("cap_micro_usdc", "unit_price_micro_usdc",
                                              "authorized_at", "dispatched_at", "expires_at")):
        reasons.append("invalid_grant_amount_or_time")
    if reasons:
        return result
    if not natural(now):
        reasons.append("invalid_or_expired_authorization")
        return result
    if not (grant["authorized_at"] <= grant["dispatched_at"]
                                <= now <= grant["expires_at"]):
        reasons.append("invalid_or_expired_authorization")
    if grant["payload_sha256"] != digest(payload):
        reasons.append("payload_mismatch")
    if usage is None:
        reasons.append("usage_unknown")
        return result
    # An invoice alone is never consumption evidence, even if it has unit fields.
    if usage.get("kind") != "usage":
        reasons.append("not_usage_evidence")
    for key in ("grant_id", "payload_sha256", "provider_id", "meter_id"):
        if usage.get(key) != grant[key]:
            reasons.append("usage_" + key + "_mismatch")
    if not natural(usage.get("units")) or not natural(usage.get("observed_at")):
        reasons.append("invalid_usage")
        return result
    if not grant["dispatched_at"] <= usage["observed_at"] <= now:
        reasons.append("usage_time_mismatch")
    if reasons:
        return result
    measured = usage["units"] * grant["unit_price_micro_usdc"]
    result["usage_micro_usdc"] = measured
    if measured > grant["cap_micro_usdc"]:
        reasons.append("budget_exhausted")
    # Optional independent authorizer observation is not the authorization cap.
    observation = grant.get("authorizer_observed_micro_usdc")
    if observation is not None and (not natural(observation) or observation != measured):
        reasons.append("authorizer_provider_usage_conflict")
    if invoice is None:
        reasons.append("invoice_missing")
        return result
    if invoice.get("kind") != "invoice":
        reasons.append("invalid_invoice_kind")
    for key in ("grant_id", "payload_sha256", "provider_id"):
        if invoice.get(key) != grant[key]:
            reasons.append("invoice_" + key + "_mismatch")
    if not natural(invoice.get("amount_micro_usdc")) or invoice["amount_micro_usdc"] != measured:
        reasons.append("invoice_usage_conflict")
    result["meter_is_payee"] = usage["meter_id"] == invoice.get("payee_id")
    if not isinstance(invoice.get("payee_id"), str) or not invoice["payee_id"]:
        reasons.append("payee_missing")
    elif invoice["payee_id"] != grant["provider_id"]:
        reasons.append("payee_not_authorized")
    if result["meter_is_payee"]:
        reasons.append("meter_is_payee_review_required")
    if acceptance not in ("accepted", "rejected", "pending", "expired"):
        reasons.append("invalid_acceptance")
    elif acceptance != "accepted":
        reasons.append("customer_" + acceptance)
    if payment not in ("confirmed", "unknown", "unpaid"):
        reasons.append("invalid_payment_evidence")
    elif payment != "confirmed":
        reasons.append("customer_payment_" + payment)
    if not reasons:
        result["decision"] = "simulated_reconciliation_ready"
        result["simulation_settlement_eligible"] = True
    return result


def clean_rows(rows):
    """Synthetic public-data-shaped example: retain sources, reject ambiguous rows."""
    cleaned, rejected, seen = [], [], set()
    for line, row in enumerate(rows, 1):
        key = str(row.get("id", "")).strip()
        name = str(row.get("name", "")).strip()
        source = row.get("source")
        amount = row.get("amount_micro_usdc")
        if not key or not name or not isinstance(source, str) or not source or not natural(amount):
            rejected.append({"line": line, "reason": "missing_or_invalid_field"})
        elif key in seen:
            rejected.append({"line": line, "reason": "duplicate_id"})
        else:
            cleaned.append({"id": key, "name": name, "amount_micro_usdc": amount,
                            "source": source, "source_line": line})
            seen.add(key)
    return {"synthetic": True, "cleaned": cleaned, "rejected": rejected,
            "input_sha256": digest(rows), "output_sha256": digest(cleaned)}


def example():
    rows = [{"id": " A ", "name": " Example resource ", "amount_micro_usdc": 250000,
             "source": "synthetic:fixture"},
            {"id": "A", "name": "Duplicate", "amount_micro_usdc": 250000,
             "source": "synthetic:fixture"},
            {"id": "B", "name": "Unknown cost", "amount_micro_usdc": None,
             "source": "synthetic:fixture"}]
    payload = {"job_id": "synthetic-job-1", "input_sha256": digest(rows),
               "operation": "clean_rows-v1"}
    grant = {"grant_id": "synthetic-grant-1", "payload_sha256": digest(payload),
             "authorizer_id": "simulated-sponsor", "provider_id": "simulated-provider",
             "meter_id": "simulated-separate-meter", "cap_micro_usdc": 1000000,
             "unit_price_micro_usdc": 2, "authorized_at": 1, "dispatched_at": 2,
             "expires_at": 100}
    usage = {"kind": "usage", "grant_id": grant["grant_id"],
             "payload_sha256": grant["payload_sha256"], "provider_id": grant["provider_id"],
             "meter_id": grant["meter_id"], "units": 100000, "observed_at": 3}
    invoice = {"kind": "invoice", "grant_id": grant["grant_id"],
               "payload_sha256": grant["payload_sha256"], "provider_id": grant["provider_id"],
               "payee_id": grant["provider_id"], "amount_micro_usdc": 200000}
    return payload, grant, usage, invoice, clean_rows(rows)


if __name__ == "__main__":
    payload, grant, usage, invoice, artifact = example()
    print(json.dumps({"artifact": artifact, "authorization": grant, "usage": usage,
                      "invoice": invoice, "evaluation": reconcile(
                          grant, usage, invoice, payload=payload, now=4,
                          acceptance="accepted", payment="confirmed"),
                      "cost_labels": {"fixture_usage_micro_usdc": "SCENARIO",
                                      "actual_model_tokens": None,
                                      "actual_provider_price": None,
                                      "actual_customer_revenue": None,
                                      "outside_borrower_demand": None}}, indent=2))
