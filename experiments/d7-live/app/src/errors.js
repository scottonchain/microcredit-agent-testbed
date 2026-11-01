// Plain-language text for pool errors (adapted from the contract repository's contractErrors.ts) and wallet failures.
export const MESSAGES = {
  ZeroAmount: 'Enter an amount greater than zero.',
  InsufficientBalance: 'That is more than your available balance.',
  InsufficientLiquidity: 'The pool does not have enough free test USDC right now. Try a smaller amount or try again later.',
  NoCredit: 'You have no credit yet. Ask a friend to back you, or request a test credit line (see Get credit).',
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
  NotCancellableYet: 'Only the borrower can cancel this loan for now.',
  SafeERC20FailedOperation: 'The USDC transfer failed. Check your balance.',
  CapExceeded: 'This wallet has used up its free-gas allowance for the test.',
  BadCall: 'The free-gas service refused this action.',
  'ERC20: transfer amount exceeds balance': 'Not enough USDC in your wallet.',
};
export function friendly(e) {
  const raw = (e && (e.reason || e.errorName || e.shortMessage || e.message)) || String(e);
  const key = Object.keys(MESSAGES).find((k) => raw.includes(k));
  if (key) return MESSAGES[key];
  if (/NotAllowedError|credential request failed|cancel|timed out/i.test(raw)) return 'Cancelled. Nothing was sent. Try again and approve with your fingerprint, face or screen lock.';
  if (/rate limit|429|Too Many/i.test(raw)) return 'The test network is busy (rate limited). Wait a few seconds and try again.';
  if (/Failed to fetch|NetworkError|fetch failed/i.test(raw)) return 'Cannot reach the test network. Check your connection and try again.';
  return 'Something went wrong. Nothing was lost. Try again; if it repeats, copy the details below into your feedback.';
}
