// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

// TESTNET ONLY. A rule-based gas sponsor for ERC-4337 EntryPoint v0.6 (Base Sepolia).
// It pays gas for Coinbase Smart Wallet user operations that only (a) create the wallet through the
// canonical factory and (b) call the Omnequa test pool or Circle test USDC with allow-listed functions
// and no ETH value. No server and no signature: the rules are the code. Each sender has a lifetime cap.
// It holds no user funds. The owner can change the cap, withdraw the ETH deposit and the stake.

struct UserOperation {
    address sender;
    uint256 nonce;
    bytes initCode;
    bytes callData;
    uint256 callGasLimit;
    uint256 verificationGasLimit;
    uint256 preVerificationGas;
    uint256 maxFeePerGas;
    uint256 maxPriorityFeePerGas;
    bytes paymasterAndData;
    bytes signature;
}

interface IEntryPoint06 {
    function depositTo(address account) external payable;
    function addStake(uint32 unstakeDelaySec) external payable;
    function unlockStake() external;
    function withdrawStake(address payable to) external;
    function withdrawTo(address payable to, uint256 amount) external;
    function balanceOf(address account) external view returns (uint256);
}

contract SponsorPaymaster {
    enum PostOpMode { opSucceeded, opReverted, postOpReverted }

    IEntryPoint06 public immutable entryPoint;
    address public immutable pool;
    address public immutable usdc;
    address public immutable walletFactory;
    address public owner;
    uint256 public capPerSender; // lifetime cap of sponsored gas cost (wei) per wallet
    mapping(address => uint256) public spent;

    mapping(bytes4 => bool) private poolAllowed;
    bytes4 private constant EXECUTE = 0xb61d27f6; // execute(address,uint256,bytes)
    bytes4 private constant EXECUTE_BATCH = 0x34fcd5be; // executeBatch((address,uint256,bytes)[])
    bytes4 private constant APPROVE = 0x095ea7b3; // approve(address,uint256)
    bytes4 private constant TRANSFER = 0xa9059cbb; // transfer(address,uint256)

    error NotEntryPoint();
    error NotOwner();
    error BadFactory();
    error BadCall();
    error CapExceeded();

    constructor(address _entryPoint, address _pool, address _usdc, address _factory, uint256 _cap) {
        entryPoint = IEntryPoint06(_entryPoint);
        pool = _pool;
        usdc = _usdc;
        walletFactory = _factory;
        capPerSender = _cap;
        owner = msg.sender;
        string[10] memory sigs = [
            "requestLoan(uint256)", "disburseLoan(uint256)", "cancelLoan(uint256)", "repayLoan(uint256,uint256)",
            "back(address,uint256)", "stake(uint256)", "unstake(uint256)", "depositFunds(uint256)",
            "withdrawFunds(uint256)", "setDisplayName(string)"
        ];
        for (uint256 i = 0; i < sigs.length; i++) poolAllowed[bytes4(keccak256(bytes(sigs[i])))] = true;
    }

    modifier onlyOwner() { if (msg.sender != owner) revert NotOwner(); _; }

    function validatePaymasterUserOp(UserOperation calldata op, bytes32, uint256 maxCost)
        external
        returns (bytes memory context, uint256 validationData)
    {
        if (msg.sender != address(entryPoint)) revert NotEntryPoint();
        if (op.initCode.length != 0 && address(bytes20(op.initCode[:20])) != walletFactory) revert BadFactory();
        _checkCallData(op.callData);
        if (spent[op.sender] + maxCost > capPerSender) revert CapExceeded();
        return (abi.encode(op.sender), 0);
    }

    function postOp(PostOpMode, bytes calldata context, uint256 actualGasCost) external {
        if (msg.sender != address(entryPoint)) revert NotEntryPoint();
        address sender = abi.decode(context, (address));
        spent[sender] += actualGasCost;
    }

    function _checkCallData(bytes calldata data) internal view {
        bytes4 sel = bytes4(data[:4]);
        if (sel == EXECUTE) {
            (address target, uint256 value, bytes memory inner) = abi.decode(data[4:], (address, uint256, bytes));
            _checkCall(target, value, inner);
        } else if (sel == EXECUTE_BATCH) {
            (address[] memory targets, uint256[] memory values, bytes[] memory inners) = _decodeBatch(data[4:]);
            if (targets.length == 0 || targets.length > 4) revert BadCall();
            for (uint256 i = 0; i < targets.length; i++) _checkCall(targets[i], values[i], inners[i]);
        } else {
            revert BadCall();
        }
    }

    struct Call { address target; uint256 value; bytes data; }

    function _decodeBatch(bytes calldata enc) internal pure returns (address[] memory t, uint256[] memory v, bytes[] memory d) {
        Call[] memory calls = abi.decode(enc, (Call[]));
        t = new address[](calls.length); v = new uint256[](calls.length); d = new bytes[](calls.length);
        for (uint256 i = 0; i < calls.length; i++) { t[i] = calls[i].target; v[i] = calls[i].value; d[i] = calls[i].data; }
    }

    function _checkCall(address target, uint256 value, bytes memory inner) internal view {
        if (value != 0 || inner.length < 4) revert BadCall();
        bytes4 sel;
        assembly { sel := mload(add(inner, 32)) }
        if (target == pool) {
            if (!poolAllowed[sel]) revert BadCall();
        } else if (target == usdc) {
            if (sel == APPROVE) {
                if (inner.length != 68) revert BadCall();
                address spender;
                assembly { spender := mload(add(inner, 36)) }
                if (spender != pool) revert BadCall();
            } else if (sel == TRANSFER) {
                if (inner.length != 68) revert BadCall();
            } else {
                revert BadCall();
            }
        } else {
            revert BadCall();
        }
    }

    // Owner functions: fund, stake, withdraw, tune.
    receive() external payable { entryPoint.depositTo{value: msg.value}(address(this)); }
    function addStake(uint32 delay) external payable onlyOwner { entryPoint.addStake{value: msg.value}(delay); }
    function unlockStake() external onlyOwner { entryPoint.unlockStake(); }
    function withdrawStake(address payable to) external onlyOwner { entryPoint.withdrawStake(to); }
    function withdrawDeposit(address payable to, uint256 amount) external onlyOwner { entryPoint.withdrawTo(to, amount); }
    function setCap(uint256 cap) external onlyOwner { capPerSender = cap; }
    function transferOwnership(address next) external onlyOwner { owner = next; }
}
