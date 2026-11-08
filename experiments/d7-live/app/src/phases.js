// How far a signing attempt got, so a failure can be described truthfully:
//   'approval'  - the person had not approved yet: nothing was signed or sent;
//   'approved'  - approved, but no acknowledgement came back from the test network (outcome unknown);
//   'submitted' - handed to the test network (userOpHash known) and waiting for the result failed (it may still go through).
// `state.approved` is set by guardedGet (foreground.js) when the passkey call resolves.
export const tag = (e, phase, hash) => {
  if (e && typeof e === 'object') { try { e.phase = phase; if (hash) e.userOpHash = hash; } catch {} }
  return e;
};
export async function submitTracked(bundlerClient, account, calls, onStage, state, timeout = 120000) {
  state.approved = false;
  onStage?.('sign');
  let hash;
  try { hash = await bundlerClient.sendUserOperation({ account, calls }); }
  catch (e) { throw tag(e, state.approved ? 'approved' : 'approval'); }
  onStage?.('submit');
  try { return { hash, receipt: await bundlerClient.waitForUserOperationReceipt({ hash, timeout }) }; }
  catch (e) { throw tag(e, 'submitted', hash); }
}
