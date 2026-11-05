// SPDX-License-Identifier: MIT
pragma solidity 0.8.33;

/// @notice Candidate for a NEW isolated testnet pool, not installed on canonical pool.
/// Gross allowances are consumed at REQUEST, never replenished by repayment/cancel.
/// Controller/group labels require reviewed off-chain identity evidence.
contract ScopedOriginationBudget {
    address public immutable owner;
    address public immutable pool;
    uint256 public immutable totalCap;
    uint256 public immutable controllerCap;
    uint256 public immutable groupCap;
    uint256 public totalUsed;
    bool public stopped;
    struct Grant { bytes32 controller; bytes32 group; uint256 cap; uint256 used; uint256 expiry; }
    mapping(address => Grant) public grants;
    mapping(address => bool) public revoked;
    mapping(bytes32 => uint256) public controllerUsed;
    mapping(bytes32 => uint256) public groupUsed;
    event Granted(address indexed borrower, bytes32 controller, bytes32 group, uint256 cap, uint256 expiry);
    event Consumed(address indexed borrower, uint256 amount, uint256 totalUsed);
    event Stopped();
    constructor(address owner_, address pool_, uint256 total_, uint256 controller_, uint256 group_) {
        require(owner_ != address(0) && pool_ != address(0), "zero authority");
        require(total_ > 0 && controller_ > 0 && group_ > 0, "zero cap");
        owner=owner_; pool=pool_; totalCap=total_; controllerCap=controller_; groupCap=group_;
    }
    function grant(address borrower, bytes32 controller, bytes32 group, uint256 cap, uint256 expiry) external {
        require(msg.sender==owner && !stopped, "authority/stopped");
        require(borrower!=address(0) && controller!=bytes32(0) && group!=bytes32(0), "identity required");
        require(grants[borrower].cap==0 && cap>0 && cap<=controllerCap && cap<=groupCap && cap<=totalCap, "grant/cap");
        require(expiry>block.timestamp, "expiry");
        grants[borrower]=Grant(controller,group,cap,0,expiry);
        emit Granted(borrower,controller,group,cap,expiry);
    }
    function revoke(address borrower) external { require(msg.sender==owner,"authority"); revoked[borrower]=true; }
    function stop() external { require(msg.sender==owner,"authority"); stopped=true; emit Stopped(); }
    function consume(address borrower,uint256 amount) external {
        require(msg.sender==pool && !stopped,"pool/stopped");
        Grant storage g=grants[borrower];
        require(!revoked[borrower] && g.cap>0 && block.timestamp<g.expiry && amount>0,"grant/expiry/amount");
        require(amount<=g.cap-g.used && amount<=totalCap-totalUsed,"borrower/total cap");
        require(amount<=controllerCap-controllerUsed[g.controller],"controller cap");
        require(amount<=groupCap-groupUsed[g.group],"group cap");
        g.used+=amount; totalUsed+=amount;
        controllerUsed[g.controller]+=amount; groupUsed[g.group]+=amount;
        emit Consumed(borrower,amount,totalUsed);
    }
}
