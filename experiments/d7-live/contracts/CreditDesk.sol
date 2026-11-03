// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

// TESTNET ONLY. The credit desk: an on-chain conversation between an applicant and an AI credit officer,
// and the stake that officer backs applicants with. The applicant writes with say(); the officer (an AI
// agent holding the officer key) answers with reply(), which may set the desk's backing of the applicant
// in the Omnequa test pool. The desk contract itself is the backer: anyone may fund() it with test USDC,
// which it stakes in the pool; a default by an applicant is charged to that stake, never to a person.
// No personal data belongs here: everything written is public on the test network.

interface IPool {
    function stake(uint256 amount) external;
    function unstake(uint256 amount) external;
    function back(address borrower, uint256 amount) external;
    function getBacking(address backer, address borrower) external view returns (uint256 secured, uint256 unsecured);
    function getFreeCredit(address backer) external view returns (uint256 credit, uint256 staked);
}

interface IERC20 {
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function approve(address spender, uint256 amount) external returns (bool);
    function transfer(address to, uint256 amount) external returns (bool);
}

contract CreditDesk {
    struct Msg { uint8 from; uint40 at; string text; } // from: 0 applicant, 1 desk

    IPool public immutable pool;
    IERC20 public immutable usdc;
    address public owner;
    address public officer;
    uint256 public maxLine; // the most the officer may back one applicant with (USDC base units)
    uint256 public constant MAX_TEXT = 1000;
    uint256 public constant MAX_MSGS = 80;
    uint256 public constant MAX_UNANSWERED = 3;

    address[] private applicants;
    mapping(address => uint256) public index1; // 1-based position in applicants, 0 = never wrote
    mapping(address => Msg[]) private threads;
    mapping(address => uint256) public unanswered; // applicant messages since the desk last replied

    event Said(address indexed applicant, uint256 index, string text);
    event Replied(address indexed applicant, uint256 index, string text, uint256 backing);
    event Funded(address indexed from, uint256 amount);

    error NotOwner();
    error NotOfficer();
    error EmptyText();
    error TextTooLong();
    error ThreadFull();
    error WaitForReply();
    error UnknownApplicant();
    error AboveMaxLine();

    modifier onlyOwner() { if (msg.sender != owner) revert NotOwner(); _; }
    modifier onlyOfficer() { if (msg.sender != officer) revert NotOfficer(); _; }

    constructor(address _pool, address _usdc, address _officer, uint256 _maxLine) {
        pool = IPool(_pool); usdc = IERC20(_usdc); owner = msg.sender; officer = _officer; maxLine = _maxLine;
    }

    // ---- applicant ----
    function say(string calldata text) external {
        uint256 n = bytes(text).length;
        if (n == 0) revert EmptyText();
        if (n > MAX_TEXT) revert TextTooLong();
        Msg[] storage t = threads[msg.sender];
        if (t.length >= MAX_MSGS) revert ThreadFull();
        if (unanswered[msg.sender] >= MAX_UNANSWERED) revert WaitForReply();
        if (index1[msg.sender] == 0) { applicants.push(msg.sender); index1[msg.sender] = applicants.length; }
        t.push(Msg(0, uint40(block.timestamp), text));
        unanswered[msg.sender] += 1;
        emit Said(msg.sender, t.length - 1, text);
    }

    // ---- officer ----
    function reply(address applicant, string calldata text, uint256 backingTotal) external onlyOfficer {
        if (index1[applicant] == 0) revert UnknownApplicant();
        if (bytes(text).length > MAX_TEXT) revert TextTooLong();
        Msg[] storage t = threads[applicant];
        if (t.length >= MAX_MSGS) revert ThreadFull();
        t.push(Msg(1, uint40(block.timestamp), text));
        unanswered[applicant] = 0;
        (uint256 s, uint256 u) = pool.getBacking(address(this), applicant);
        if (backingTotal != s + u) {
            if (backingTotal > maxLine) revert AboveMaxLine();
            pool.back(applicant, backingTotal);
        }
        emit Replied(applicant, t.length - 1, text, backingTotal);
    }

    // ---- funding ----
    function fund(uint256 amount) external {
        usdc.transferFrom(msg.sender, address(this), amount);
        usdc.approve(address(pool), amount);
        pool.stake(amount);
        emit Funded(msg.sender, amount);
    }
    function withdraw(uint256 amount, address to) external onlyOwner { pool.unstake(amount); usdc.transfer(to, amount); }
    function setOfficer(address next) external onlyOwner { officer = next; }
    function setMaxLine(uint256 next) external onlyOwner { maxLine = next; }
    function transferOwnership(address next) external onlyOwner { owner = next; }

    // ---- views ----
    function thread(address applicant) external view returns (Msg[] memory) { return threads[applicant]; }
    function applicantCount() external view returns (uint256) { return applicants.length; }
    function applicantAt(uint256 i) external view returns (address) { return applicants[i]; }
    function pending() external view returns (address[] memory out) {
        uint256 k;
        for (uint256 i = 0; i < applicants.length; i++) if (unanswered[applicants[i]] > 0) k++;
        out = new address[](k); k = 0;
        for (uint256 i = 0; i < applicants.length; i++) if (unanswered[applicants[i]] > 0) out[k++] = applicants[i];
    }
    function backingOf(address applicant) external view returns (uint256) { (uint256 s, uint256 u) = pool.getBacking(address(this), applicant); return s + u; }
    function freeStake() external view returns (uint256) { (, uint256 st) = pool.getFreeCredit(address(this)); return st; }
}
