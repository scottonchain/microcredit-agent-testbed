import { createHash } from "node:crypto";
import { describe, it } from "vitest";
import { generateKeypair, sign, toBase64 } from "../sdk-js/src/crypto/keys.js";
import { canonicalize } from "../sdk-js/src/crypto/canonical.js";
import { registerAgent } from "../src/services/agentService.js";
import { buildSignableContent, createDraft, countersign } from "../src/services/receiptService.js";
import { computeReputation } from "../src/services/reputationService.js";
import type { CreateDraftInput } from "../src/services/receiptService.js";

function signDraft(agentAId: string, bKey: Uint8Array, bId: string, input: Omit<CreateDraftInput, "signature" | "agentAId">) {
  const content = buildSignableContent(agentAId, bId, input);
  return toBase64(sign(new TextEncoder().encode(canonicalize({ ...content, dispute: undefined })), bKey));
}
function signCounter(r: ReturnType<typeof createDraft>, aKey: Uint8Array) {
  const content = { ...r, signatures: undefined, status: undefined, dispute: undefined, visibility: undefined };
  return toBase64(sign(new TextEncoder().encode(canonicalize(content)), aKey));
}
let n = 0;
function receipt(req: { did: string; privateKey: Uint8Array }, wrk: { did: string; privateKey: Uint8Array }) {
  const jobId = `ring_job_${n++}`;
  const now = new Date().toISOString();
  const h = (s: string) => `sha256:${createHash("sha256").update(s).digest("hex")}`;
  const input = {
    jobId,
    task: { capability: "translation.tr-en", specHash: h("spec" + jobId), createdAt: now },
    result: { outputHash: h("out" + jobId), completedAt: now },
    settlement: { amount: "1.00", currency: "USDC" },
    verification: { method: "payer_confirmation", outcome: "success" },
  } as Omit<CreateDraftInput, "signature" | "agentAId">;
  const sig = signDraft(req.did, wrk.privateKey, wrk.did, input);
  const d = createDraft(wrk.did, { ...input, agentAId: req.did, signature: sig });
  countersign(d.receiptId, req.did, signCounter(d, req.privateKey));
}
const show = (label: string, id: string) => {
  const r: any = computeReputation(id);
  console.log(label, JSON.stringify({ trust: r.trustScore, successRate: r.successRate, conf: r.components?.confidence ?? r.confidence, flags: r.flags, evidence: r.evidenceLevel, receipts: r.components?.finalizedReceipts }));
};

describe("closed zero-stake ring (attacker view)", () => {
  it("ring of 12 fresh identities, full mesh, 3 rounds", () => {
    const ring = Array.from({ length: 12 }, () => generateKeypair());
    ring.forEach((k) => registerAgent(k.did, { capabilities: ["job.posting", "translation.tr-en"] }));
    const lone = generateKeypair();
    registerAgent(lone.did, { capabilities: ["translation.tr-en"] });
    show("BASELINE fresh unstaked agent, 0 receipts:", lone.did);
    for (let round = 0; round < 3; round++)
      for (let i = 0; i < ring.length; i++) for (let j = 0; j < ring.length; j++) if (i !== j) receipt(ring[i], ring[j]);
    show("RING member after 3 full-mesh rounds (", ring[0].did);
    show("RING member #7:", ring[7].did);
    // hub-spoke variant: one hub, 30 sockpuppet spokes, one receipt each
    const hub = generateKeypair();
    registerAgent(hub.did, { capabilities: ["translation.tr-en"] });
    const spokes = Array.from({ length: 30 }, () => generateKeypair());
    spokes.forEach((k) => registerAgent(k.did, { capabilities: ["job.posting"] }));
    spokes.forEach((s) => receipt(s, hub));
    show("HUB of 30 sockpuppet spokes:", hub.did);
  });
});
