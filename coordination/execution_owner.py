#!/usr/bin/env python3
"""Execution-owner toggle: which AI lane (openai or claude) runs heavy project work.

When one lane is low on tokens, the other takes the compute-intensive work. Heavy work
means scheduled dispatches and any other compute-intensive execution; lightweight review,
verification and access-bridge work stays open to both lanes. The configuration lives in
`execution-owner.json` on the default branch. Standard library only.

This module decides and records; it does not run, schedule or hold credentials. A runner
calls `check` before it dispatches heavy work. A switch is a four-step handover so two
lanes never run heavy work at once:

    request (stable -> draining)     either lane, with a reason and a drain deadline
    accept                           the destination lane, fresh after the request
    drained (draining -> handover)   the source lane: nothing in flight, lease released
    complete (handover -> stable)    the destination lane, naming the lease head it acquired

While a switch is in progress nobody may start new heavy work. `cancel` returns an
unfinished switch to stable. The default owner never silently overrides the current owner:
switching back is the same four steps. No budget telemetry is read or invented; a reason
is a stated declaration.
"""
import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

LANES = ("openai", "claude")
HEAVY_KINDS = ("scheduled", "other")
LIGHT_KINDS = ("review", "verification", "access_bridge")
STATES = ("stable", "draining", "handover")
SCHEMA_VERSION = 1
CONFIG_PATH = Path(__file__).with_name("execution-owner.json")
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
RECEIPT = re.compile(r"^(gh:(ctr|tb|th|vis|site)#\d+(c\d+)?|sha:(ctr|tb|th|vis|site)@[0-9a-f]{7,40}|https://\S+)$")
EXIT_ALLOWED, EXIT_INVALID, EXIT_SUPPRESSED, EXIT_TRANSITION = 0, 2, 3, 4


class ConfigError(ValueError):
    pass


def utc(value=None):
    if value is None:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if not isinstance(value, str) or not ISO.fullmatch(value):
        raise ConfigError("time must be UTC like 2026-11-01T17:29:00Z")
    return value


def other(lane):
    if lane not in LANES:
        raise ConfigError("lane must be openai or claude")
    return LANES[1] if lane == LANES[0] else LANES[0]


def _timestamp_ok(value, field, errors, allow_none=True):
    if value is None:
        if not allow_none:
            errors.append(field + " is required")
    elif not isinstance(value, str) or not ISO.fullmatch(value):
        errors.append(field + " must be a UTC time like 2026-11-01T17:29:00Z")


def validate(cfg):
    """Return a list of problems; an empty list means the configuration is usable."""
    errors = []
    if not isinstance(cfg, dict):
        return ["configuration must be an object"]
    if cfg.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version must be %d" % SCHEMA_VERSION)
    version = cfg.get("config_version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        errors.append("config_version must be a positive integer")
    for field in ("owner", "default_owner"):
        if cfg.get(field) not in LANES:
            errors.append(field + " must be openai or claude")
    override = cfg.get("override")
    if not isinstance(override, dict):
        errors.append("override must be an object")
    else:
        if override.get("owner") != cfg.get("owner"):
            errors.append("override.owner must equal owner")
        if override.get("declared_by") not in LANES:
            errors.append("override.declared_by must be openai or claude")
        if not isinstance(override.get("reason"), str) or not override["reason"].strip():
            errors.append("override.reason is required")
        _timestamp_ok(override.get("effective_at_utc"), "override.effective_at_utc", errors, allow_none=False)
    transition = cfg.get("transition")
    if not isinstance(transition, dict) or transition.get("state") not in STATES:
        errors.append("transition.state must be one of " + ", ".join(STATES))
    else:
        if transition["state"] == "stable":
            for field in ("from", "to", "requested_by", "requested_at_utc", "reason", "drain_deadline_utc"):
                if transition.get(field) is not None:
                    errors.append("transition.%s must be null while stable" % field)
        else:
            if transition.get("from") != cfg.get("owner"):
                errors.append("transition.from must equal owner during a switch")
            if transition.get("to") not in LANES or transition.get("to") == transition.get("from"):
                errors.append("transition.to must be the other lane")
            if transition.get("requested_by") not in LANES:
                errors.append("transition.requested_by must be openai or claude")
            _timestamp_ok(transition.get("requested_at_utc"), "transition.requested_at_utc", errors, allow_none=False)
            _timestamp_ok(transition.get("drain_deadline_utc"), "transition.drain_deadline_utc", errors, allow_none=False)
            if not isinstance(transition.get("reason"), str) or not transition["reason"].strip():
                errors.append("transition.reason is required during a switch")
    acceptance = cfg.get("acceptance")
    if not isinstance(acceptance, dict) or set(acceptance) != set(LANES):
        errors.append("acceptance must hold exactly openai and claude")
    else:
        for lane in LANES:
            entry = acceptance[lane]
            if not isinstance(entry, dict):
                errors.append("acceptance.%s must be an object" % lane)
                continue
            _timestamp_ok(entry.get("accepted_at_utc"), "acceptance.%s.accepted_at_utc" % lane, errors)
            receipt = entry.get("receipt")
            if (entry.get("accepted_at_utc") is None) != (receipt is None):
                errors.append("acceptance.%s needs both a time and a receipt, or neither" % lane)
            elif receipt is not None and not RECEIPT.fullmatch(receipt):
                errors.append("acceptance.%s.receipt must be a gh:, sha: or https reference" % lane)
    lease = cfg.get("lease_owner")
    if lease is not None and lease not in LANES:
        errors.append("lease_owner must be null, openai or claude")
    if not isinstance(cfg.get("history"), list):
        errors.append("history must be a list")
    return errors


def require_valid(cfg):
    problems = validate(cfg)
    if problems:
        raise ConfigError("; ".join(problems))


def decide(cfg, runner, kind):
    """May `runner` start `kind` of work now? Returns {allowed, state, reason, exit_code}."""
    require_valid(cfg)
    if runner not in LANES:
        raise ConfigError("runner must be openai or claude")
    if kind not in HEAVY_KINDS + LIGHT_KINDS + ("drain",):
        raise ConfigError("kind must be one of " + ", ".join(HEAVY_KINDS + LIGHT_KINDS + ("drain",)))
    state = cfg["transition"]["state"]
    base = {"runner": runner, "kind": kind, "owner": cfg["owner"], "state": state,
            "config_version": cfg["config_version"]}
    if kind in LIGHT_KINDS:
        return dict(base, allowed=True, exit_code=EXIT_ALLOWED,
                    reason="lightweight work stays open to both lanes")
    if kind == "drain":
        if state == "draining" and runner == cfg["transition"]["from"]:
            return dict(base, allowed=True, exit_code=EXIT_ALLOWED,
                        reason="the source lane may finish and checkpoint in-flight work")
        return dict(base, allowed=False, exit_code=EXIT_SUPPRESSED, reason="no drain is open for this lane")
    if state != "stable":
        return dict(base, allowed=False, exit_code=EXIT_TRANSITION,
                    reason="a switch to %s is in progress (%s); no lane starts new heavy work" %
                           (cfg["transition"]["to"], state))
    if runner == cfg["owner"]:
        return dict(base, allowed=True, exit_code=EXIT_ALLOWED, reason="runner is the execution owner")
    return dict(base, allowed=False, exit_code=EXIT_SUPPRESSED,
                reason="heavy %s work belongs to %s; this lane does lightweight work only" % (kind, cfg["owner"]))


def _bump(cfg, event, by, now, detail):
    new = json.loads(json.dumps(cfg))
    new["config_version"] = cfg["config_version"] + 1
    new["history"] = list(cfg["history"]) + [
        {"config_version": new["config_version"], "event": event, "by": by, "at_utc": now, "detail": detail}]
    return new


def request_switch(cfg, *, to, by, reason, drain_deadline_utc, now=None):
    """stable -> draining. Idempotent for an identical open request (deduplication)."""
    require_valid(cfg)
    now = utc(now)
    drain_deadline_utc = utc(drain_deadline_utc)
    other(to)
    if by not in LANES:
        raise ConfigError("by must be openai or claude")
    if not isinstance(reason, str) or not reason.strip():
        raise ConfigError("a reason is required (a stated declaration, not telemetry)")
    transition = cfg["transition"]
    if transition["state"] != "stable":
        if transition["to"] == to and transition["requested_by"] == by:
            return cfg  # the same request again changes nothing
        raise ConfigError("a switch is already in progress; cancel it first")
    if to == cfg["owner"]:
        raise ConfigError("%s already owns heavy work" % to)
    if drain_deadline_utc <= now:
        raise ConfigError("the drain deadline must be after the request")
    new = _bump(cfg, "request", by, now, "to=%s reason=%s" % (to, reason.strip()))
    new["transition"] = {"state": "draining", "from": cfg["owner"], "to": to, "requested_by": by,
                         "requested_at_utc": now, "reason": reason.strip(), "drain_deadline_utc": drain_deadline_utc}
    return new


def accept(cfg, *, by, receipt, now=None):
    """Record that a lane accepts the role. Needed fresh from the destination for a switch."""
    require_valid(cfg)
    now = utc(now)
    other(by)
    if not isinstance(receipt, str) or not RECEIPT.fullmatch(receipt):
        raise ConfigError("receipt must be a gh:, sha: or https reference to the acceptance")
    new = _bump(cfg, "accept", by, now, "receipt=" + receipt)
    new["acceptance"][by] = {"accepted_at_utc": now, "receipt": receipt}
    return new


def drained(cfg, *, by, in_flight, lease_released, now=None):
    """draining -> handover. The source lane attests nothing is in flight and its lease is released."""
    require_valid(cfg)
    now = utc(now)
    transition = cfg["transition"]
    if transition["state"] != "draining":
        raise ConfigError("no switch is draining")
    if by != transition["from"]:
        raise ConfigError("only the source lane can report that it has drained")
    if in_flight != 0:
        raise ConfigError("work is still in flight; checkpoint it first")
    if lease_released is not True:
        raise ConfigError("the source lane must release the lease first")
    new = _bump(cfg, "drained", by, now, "in_flight=0 lease_released=true")
    new["transition"]["state"] = "handover"
    new["lease_owner"] = None
    return new


def complete(cfg, *, by, lease_head, now=None):
    """handover -> stable. Only the destination lane, with a fresh acceptance and the lease head it acquired."""
    require_valid(cfg)
    now = utc(now)
    transition = cfg["transition"]
    if transition["state"] != "handover":
        raise ConfigError("the source lane has not reported a drain")
    if by != transition["to"]:
        raise ConfigError("only the destination lane can complete the switch")
    entry = cfg["acceptance"][by]
    if entry["accepted_at_utc"] is None or entry["accepted_at_utc"] < transition["requested_at_utc"]:
        raise ConfigError("the destination lane has not accepted since this request; "
                          "an earlier acceptance does not carry over")
    if not isinstance(lease_head, str) or not re.fullmatch(r"[0-9a-f]{7,40}", lease_head):
        raise ConfigError("name the lease head the destination lane acquired")
    new = _bump(cfg, "complete", by, now, "from=%s to=%s lease_head=%s" % (transition["from"], by, lease_head))
    new["owner"] = by
    new["override"] = {"owner": by, "effective_at_utc": now, "reason": transition["reason"],
                       "declared_by": transition["requested_by"]}
    new["transition"] = {"state": "stable", "from": None, "to": None, "requested_by": None,
                         "requested_at_utc": None, "reason": None, "drain_deadline_utc": None}
    new["lease_owner"] = by
    return new


def cancel(cfg, *, by, now=None):
    """Return an unfinished switch to stable with the owner unchanged."""
    require_valid(cfg)
    now = utc(now)
    other(by)
    if cfg["transition"]["state"] == "stable":
        return cfg
    new = _bump(cfg, "cancel", by, now, "switch to %s cancelled in state %s" %
                (cfg["transition"]["to"], cfg["transition"]["state"]))
    new["transition"] = {"state": "stable", "from": None, "to": None, "requested_by": None,
                         "requested_at_utc": None, "reason": None, "drain_deadline_utc": None}
    return new


def status(cfg, now=None):
    require_valid(cfg)
    now = utc(now)
    transition = cfg["transition"]
    stale = transition["state"] != "stable" and transition["drain_deadline_utc"] < now
    return {
        "owner": cfg["owner"], "default_owner": cfg["default_owner"], "state": transition["state"],
        "config_version": cfg["config_version"], "override": cfg["override"],
        "lease_owner": cfg["lease_owner"], "switch_past_deadline": stale,
        "heavy_work": {lane: decide(cfg, lane, "scheduled")["allowed"] for lane in LANES},
    }


def load(path=CONFIG_PATH):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def save(cfg, path=CONFIG_PATH):
    """Atomic write; the caller commits through the normal reviewed or leased path."""
    require_valid(cfg)
    path = Path(path)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".execution-owner-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(cfg, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--now", default=None, help="UTC time override for tests")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("status")
    check = sub.add_parser("check", help="exit 0 allowed, 3 suppressed, 4 switch in progress, 2 invalid")
    check.add_argument("--runner", required=True, choices=LANES)
    check.add_argument("--kind", required=True, choices=HEAVY_KINDS + LIGHT_KINDS + ("drain",))
    req = sub.add_parser("request")
    req.add_argument("--to", required=True, choices=LANES)
    req.add_argument("--by", required=True, choices=LANES)
    req.add_argument("--reason", required=True)
    req.add_argument("--drain-deadline", required=True)
    acc = sub.add_parser("accept")
    acc.add_argument("--by", required=True, choices=LANES)
    acc.add_argument("--receipt", required=True)
    dr = sub.add_parser("drained")
    dr.add_argument("--by", required=True, choices=LANES)
    dr.add_argument("--in-flight", type=int, required=True)
    dr.add_argument("--lease-released", action="store_true")
    co = sub.add_parser("complete")
    co.add_argument("--by", required=True, choices=LANES)
    co.add_argument("--lease-head", required=True)
    ca = sub.add_parser("cancel")
    ca.add_argument("--by", required=True, choices=LANES)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        cfg = load(args.config)
        if args.action == "status":
            print(json.dumps(status(cfg, args.now), indent=2))
            return EXIT_ALLOWED
        if args.action == "check":
            result = decide(cfg, args.runner, args.kind)
            print(json.dumps(result))
            return result["exit_code"]
        if args.action == "request":
            new = request_switch(cfg, to=args.to, by=args.by, reason=args.reason,
                                 drain_deadline_utc=args.drain_deadline, now=args.now)
        elif args.action == "accept":
            new = accept(cfg, by=args.by, receipt=args.receipt, now=args.now)
        elif args.action == "drained":
            new = drained(cfg, by=args.by, in_flight=args.in_flight, lease_released=args.lease_released, now=args.now)
        elif args.action == "complete":
            new = complete(cfg, by=args.by, lease_head=args.lease_head, now=args.now)
        else:
            new = cancel(cfg, by=args.by, now=args.now)
        if new is not cfg:
            save(new, args.config)
        print(json.dumps(status(new, args.now), indent=2))
        return EXIT_ALLOWED
    except (ConfigError, OSError, ValueError) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return EXIT_INVALID


if __name__ == "__main__":
    sys.exit(main())
