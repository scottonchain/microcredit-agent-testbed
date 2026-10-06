#!/usr/bin/env python3
"""Toy model of a create endpoint with a single-shot verifier (the Moltbook comment flow as merktop and pyclaw001 describe it
in public, post a925ab02), for case api-1. Stdlib, deterministic. Not Moltbook itself.

Two authorities that do not see each other's state:
  verifier  : POST create returns a pending object + a one-shot code; a wrong answer burns the code (400) and marks the
              object failed; reusing a consumed code gives 409; a right answer gives 200 and publishes the object.
  listing   : the canonical thread read returns published objects only.
A dedup layer on create keys on the content hash: a second create with the same content returns "existing" and the first
object's id, whatever that object's verification status is (merktop 3ad3360e: it returned a failed, invisible object).

Knobs reproduce the two public incidents and the converse hazard:
  publish_despite_failed  pyclaw001 f9f87236 / merktop 8d1e7e9d: verifier says failed, the object is readable in the thread
  lose_receipt            merktop 8d1e7e9d (converse): verifier says 200, the object is not readable (lost receipt)
"""
import hashlib


class CommentAPI:
    def __init__(self):
        self.objects = []          # {"id", "content_hash", "status": pending|failed|verified, "published": bool, "code", "code_consumed"}
        self.publish_despite_failed = False
        self.lose_receipt = False
        self.creates = 0
        self.verifies = 0

    @staticmethod
    def h(content):
        return hashlib.sha256(content.encode()).hexdigest()[:12]

    def create(self, content):
        self.creates += 1
        ch = self.h(content)
        for o in self.objects:
            if o["content_hash"] == ch:
                return {"existing": True, "id": o["id"], "verification_status": o["status"],
                        "message": "You already said this on this post!"}
        o = {"id": "c%d" % (len(self.objects) + 1), "content_hash": ch, "status": "pending", "published": False,
             "code": "code-%d" % (len(self.objects) + 1), "code_consumed": False}
        self.objects.append(o)
        return {"existing": False, "id": o["id"], "verification_code": o["code"]}

    def verify(self, code, answer_correct):
        self.verifies += 1
        o = next((o for o in self.objects if o["code"] == code), None)
        if o is None:
            return 404
        if o["code_consumed"]:
            return 409                               # code already consumed: another attempt with it is impermissible
        o["code_consumed"] = True
        if not answer_correct:
            o["status"] = "failed"
            o["published"] = bool(self.publish_despite_failed)
            return 400
        o["status"] = "verified"
        o["published"] = not self.lose_receipt
        return 200

    def listing(self):
        """The canonical read: published objects only."""
        return [o["id"] for o in self.objects if o["published"]]

    def listing_has(self, content):
        ch = self.h(content)
        return any(o["published"] and o["content_hash"] == ch for o in self.objects)


class Poster:
    """The retrying client. Reference (two_authorities=True): retry permitted iff the verifier allows a new attempt AND a
    fresh canonical-listing read shows the object absent; a 200 without a listing hit is 'reconcile', not 'delivered'; the
    create response's "existing" claim is never trusted without a listing read. Mutant (two_authorities=False): one
    authority stands in for the other: verifier 200 = delivered, verifier 400 = retry, create-response "existing" = present."""

    def __init__(self, api, two_authorities=True):
        self.api = api
        self.two_authorities = two_authorities
        self.log = []

    def post_once(self, content, answers=(True,), max_creates=3):
        """answers: the correctness of successive challenge answers (one per create). Returns the final disposition."""
        answers = list(answers)
        for attempt in range(max_creates):
            res = self.api.create(content)
            if res["existing"]:
                if self.two_authorities:
                    present = self.api.listing_has(content)
                    if present:
                        self.log.append("existing + listing present -> stop")
                        return "stop: object present"
                    self.log.append("existing claimed by create response but listing absent -> rewrite under a new identity")
                    content = content + " "              # the only way past a content-hash dedup: a new object identity
                    continue
                self.log.append("existing claimed by create response -> stop (trusted the response body)")
                return "stop: trusted create response"
            answer_ok = answers[attempt] if attempt < len(answers) else True
            code = self.api.verify(res["verification_code"], answer_ok)
            if self.two_authorities:
                present = self.api.listing_has(content)
                if code == 200:
                    if present:
                        self.log.append("200 + listing present -> delivered")
                        return "delivered"
                    self.log.append("200 but listing absent -> reconcile (lost receipt), no retry, no delivered claim")
                    return "reconcile: verifier success, object absent"
                # 400/409: the verifier forbids reuse of that code; a NEW create would give a new code, so the verifier half of
                # the predicate is satisfiable; the object half decides
                if present:
                    self.log.append("%d but listing present -> stop, object exists" % code)
                    return "stop: object present despite verifier %d" % code
                self.log.append("%d and listing absent -> retry with a new create" % code)
                continue
            # mutant: verifier state alone decides
            if code == 200:
                self.log.append("200 -> delivered (no listing read)")
                return "delivered"
            self.log.append("%d -> retry with a new create (no listing read)" % code)
        return "gave up after %d creates" % max_creates
