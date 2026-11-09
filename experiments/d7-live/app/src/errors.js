// Plain-language text for pool errors (adapted from the contract repository's contractErrors.ts) and wallet failures.
export const MESSAGES = {
  ZeroAmount: 'Enter an amount greater than zero.',
  InsufficientBalance: 'That is more than your available balance.',
  InsufficientLiquidity: 'The pool does not have enough free test USDC right now. Try a smaller amount or try again later.',
  NoCredit: 'You have no credit yet. Ask the credit desk in the app (an AI officer answers there), or ask a friend to back you.',
  BorrowLimitExceeded: 'That is more than your credit allows. Your limit is your own credit plus what friends back you with.',
  BorrowerInDefault: 'This wallet has a defaulted loan and cannot borrow.',
  UtilisationCapExceeded: 'The pool has lent out as much as it allows right now. Try a smaller amount or try later.',
  LoanNotRequested: 'This loan is not waiting to be paid out.',
  LoanNotActive: 'This loan is not active. It may already be repaid. Refresh to see its current state.',
  NothingToRepay: 'There is nothing left to repay.',
  SelfBacking: 'You cannot back yourself.',
  TooManyBackers: 'This borrower already has the maximum number of backers.',
  BackingTooSmall: 'Backing must be at least 1 USDC.',
  InsufficientCredit: 'You do not have that much free credit or stake to back with.',
  BackingInUse: 'That backing is covering money your friend still owes. You can lower it after they repay.',
  StakeCommitted: 'That stake is committed to backing someone.',
  InsufficientStake: 'That is more than you have staked.',
  LendingPaused: 'New lending is paused by the pool guardian. Repayments still work.',
  WrongBorrower: 'This loan belongs to a different wallet.',
  NotYetDefaultable: 'This loan is not overdue long enough to be marked defaulted yet.',
  NotCancellableYet: 'Only the borrower can cancel this loan for now.',
  SafeERC20FailedOperation: 'The USDC transfer failed. Check your balance.',
  CapExceeded: 'This wallet has used up its free-gas allowance for the test.',
  BadCall: 'The free-gas service refused this action.',
  'ERC20: transfer amount exceeds balance': 'Not enough USDC in your wallet.',
};
export function friendly(e) {
  // Read every field an error may carry: a passkey refusal arrives as a DOMException (name NotAllowedError, message
  // "The operation either timed out or was not allowed"), and a wrapped error keeps the cause in details or cause.
  const parts = e ? [e.reason, e.errorName, e.shortMessage, e.message, e.details, e.name, e.cause && e.cause.message, e.cause && e.cause.name] : [String(e)];
  const raw = parts.filter((x) => typeof x === 'string' && x).join(' | ') || String(e);
  // A failure while waiting for the result (phase 'submitted') cannot be a contract refusal (those come back as a mined result), so
  // it must never be shown as one: say it may still go through, whatever words the error text happens to contain.
  if (e && e.phase === 'submitted') return 'It was sent to the test network, but we have not seen it finish. It may still go through. Wait a minute and check your home screen before you try again.';
  const key = Object.keys(MESSAGES).find((k) => raw.includes(k));
  if (key) return MESSAGES[key];
  // What was sent depends on how far the attempt got (e.phase, set by core.send): 'approval' = the person had not yet
  // approved, so nothing was signed; 'approved' = approved but no acknowledgement came back; 'submitted' = handed to the
  // test network and the wait for the result failed. Never say "nothing was sent" unless that is true.
  if (e && e.phase === 'submitted') return 'It was sent to the test network, but we have not seen it finish. It may still go through. Wait a minute and check your home screen before you try again.';
  if (e && e.phase === 'approved') return 'You approved it, but we could not confirm that it reached the test network. Wait a minute and check your home screen before you try again.';
  if (/FocusError|document is not focused|not focused|page is not visible/i.test(raw)) return 'Your phone or browser paused the approval because this page was not in front. This attempt did not send anything. Keep this page open and in front, then tap the button again.';
  if (/NotAllowedError|credential request failed|cancel|timed out|not allowed|AbortError|user denied|rejected/i.test(raw)) return e && e.phase === 'approval' ? 'You cancelled, or the approval closed. This attempt did not send anything. Tap the button again if you still want to do it.' : 'Cancelled. Try again and approve with your fingerprint, face or screen lock.';
  if (/rate limit|429|Too Many/i.test(raw)) return 'The test network is busy (rate limited). Wait a few seconds and try again.';
  if (/Failed to fetch|NetworkError|fetch failed/i.test(raw)) return 'Cannot reach the test network. Check your connection and try again.';
  return 'Something went wrong. Nothing was lost. Try again; if it repeats, copy the details below into your feedback.';
}

// Title for the failure sheet. 'It did not go through' is only true when nothing was approved or sent (or the chain
// reverted it). When the outcome is unknown (approved or submitted), the title says so instead.
export function failureTitle(e) {
  return e && (e.phase === 'approved' || e.phase === 'submitted') ? 'Still checking this attempt' : 'It did not go through';
}
