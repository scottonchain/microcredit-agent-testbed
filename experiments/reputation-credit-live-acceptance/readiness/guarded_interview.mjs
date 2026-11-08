// Candidate shadow adapter; no signer, network or grant capability.
// Integration must pass independently obtained facts, never applicant JSON.
// The callback must be pinned/reviewed and side-effect-free. This wrapper is
// not a sandbox and cannot undo effects performed inside a malicious callback.
export function guardedInterview(decide, input) {
  const hold=reason=>({mode:'SHADOW_ONLY',outcome:'review',backing:0,pd:null,
    reason,reply:'This shadow assessment does not approve or issue credit.'});
  if(!input || typeof input!=='object' || Array.isArray(input) || typeof decide!=='function')
    return hold('INPUT_INVALID');
  const {thread, facts, maxLine}=input;
  if (!facts || typeof facts!=='object' || Array.isArray(facts)) return hold('FACTS_REQUIRED');
  const keys=['backing','deskBacks','repaid','open','defaulted'];
  if(keys.some(k=>!Object.hasOwn(facts,k))) return hold('FACTS_REQUIRED');
  if(typeof facts.deskBacks!=='boolean' || typeof facts.defaulted!=='boolean' ||
     !Number.isFinite(facts.backing) || facts.backing<0 ||
     !Number.isSafeInteger(facts.repaid) || facts.repaid<0 ||
     !Number.isSafeInteger(facts.open) || facts.open<0) return hold('FACTS_INVALID');
  if(!Number.isSafeInteger(maxLine) || maxLine<=0) return hold('CAP_UNAVAILABLE');
  if(!Array.isArray(thread) || thread.length>100 || thread.some(m=>
      !m || !Number.isInteger(m.from) || ![0,1].includes(m.from) ||
      typeof m.text!=='string' || m.text.length>2000)) return hold('INPUT_INVALID');
  // The old interview's narrative score is kept only for diagnostics. It cannot
  // become an action or a statement that a loan/backing has already occurred.
  const safeFacts=Object.fromEntries(keys.map(k=>[k,facts[k]]));
  const safeThread=thread.map(m=>({from:m.from,text:m.text}));
  let r;
  try { r=decide({thread:safeThread,facts:safeFacts,maxLine}); }
  catch { return hold('EXTRACTOR_UNAVAILABLE'); }
  if(!r || typeof r!=='object' || Array.isArray(r) ||
     !Number.isSafeInteger(r.backing) || r.backing<0 || r.backing>maxLine ||
     r.version!=='interview-0.2' || !['grant','counter','decline','ask'].includes(r.outcome) ||
     !['none','stated'].includes(r.dossier?.repayment_source?.tag)) return hold('OUTPUT_INVALID');
  return {...hold('INDEPENDENT_VERIFICATION_REQUIRED'),
    diagnostic:{version:r.version,recommendation:r.outcome,proposedBacking:r.backing,
                sourceClaim:r.dossier?.repayment_source?.tag??'none'}};
}
