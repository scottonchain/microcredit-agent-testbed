import json, urllib.request
d = json.load(open('/root/work/run_r14/r14_raw.json'))['summary']
x = d['dependent']
h = lambda s, i=0: int(s[2+64*i:2+64*(i+1)], 16)
earned = h(x['earned']); bal = h(x['balanceOf']); ts = h(x['totalSupply']); rr = h(x['rewardRate']); pf = h(x['periodFinish'])
now = d['block']['timestamp']
lh = int(d['static']['lastHarvest@0xede4dd'], 16)
fees = x['getFees']
tot = h(fees, 1) / 1e18; beefy = h(fees, 2) / 1e18; call = h(fees, 3) / 1e18; strat = h(fees, 4) / 1e18
call_frac_of_reward = tot * call
share = bal / ts
per_h_aero = rr / 1e18 * share * 3600
# r12 lens: callReward 1.4228507e12 wei at block 52316634, lastHarvest same, age 0.982h
r12_age_h = (1791421000 - lh) / 3600  # placeholder, replaced below
r12 = json.load(open('/root/work/run_r14/r12.json'))
v = [a for a in r12['vaults'] if a['id'] == 'aerodrome-usdc-aero'][0]
call_reward_r12 = int(v['lens']['res']['callReward']); l2cost = int(v['l2CostWei']); gas_est = int(v['estimateGas'])
r12_ts = None
# r12 block timestamp = r14 block ts - (blocks diff * 2s)
bdiff = d['block']['number'] - r12['block'] if isinstance(r12['block'], int) else None
print('r12 block field', r12['block'] if not isinstance(r12['block'], dict) else r12['block'])
out = {
    'block': d['block'],
    'strategy_share_pct': share * 100,
    'rewardRate_AERO_per_s_total': rr / 1e18,
    'strategy_AERO_per_h': per_h_aero,
    'earned_AERO_now': earned / 1e18,
    'implied_earned_check_AERO_at_age': per_h_aero * (now - lh) / 3600,
    'age_since_lastHarvest_h': (now - lh) / 3600,
    'periodFinish_utc': __import__('time').strftime('%FT%TZ', __import__('time').gmtime(pf)),
    'periodFinish_remaining_h': (pf - now) / 3600,
    'fees': {'total': tot, 'beefy_of_total': beefy, 'call_of_total': call, 'strategist_of_total': strat, 'call_frac_of_reward_value': call_frac_of_reward},
    'harvestOnDeposit': True,
    'paused': False,
}
# per-AERO call reward in wei, calibrated on r12 lens (earned at r12 time unknown precisely -> use accrual model from lastHarvest)
# r12 block ts: block 52316634 ; r14 block 52317212 ; 2 s blocks on Base
r12_ts = now - (d['block']['number'] - 52316634) * 2
age12 = (r12_ts - lh) / 3600
earned12 = per_h_aero * age12
wei_per_aero_call = call_reward_r12 / earned12
out['r12_age_h_model'] = age12
out['r12_earned_AERO_model'] = earned12
out['call_reward_wei_per_AERO'] = wei_per_aero_call
out['implied_AERO_value_wei'] = wei_per_aero_call / call_frac_of_reward
out['callReward_now_wei_model'] = wei_per_aero_call * earned / 1e18
out['l2_cost_harvest_only_wei_at_6e6'] = l2cost
out['estimateGas'] = gas_est
rows = []
for mult in (1.0, 1.5, 2.0, 3.0):
    C = l2cost * mult
    emin = C / wei_per_aero_call
    age_needed = emin / per_h_aero
    rows.append({'cost_multiple': mult, 'C_wei': C, 'E_min_AERO': emin, 'age_h_from_lastHarvest_at_constant_rate': age_needed,
                 'reachable_before_periodFinish': age_needed < (pf - lh) / 3600})
out['thresholds'] = rows
# spread at 21h (Cowllector default recency gate) at constant rate
for age in (3.25, 6, 12, 21):
    out['spread_at_age_%sh_wei_L2only' % age] = wei_per_aero_call * per_h_aero * age - l2cost
out['max_spread_wei_L2only_21h'] = out['spread_at_age_21h_wei_L2only']
# ETH price unknown: express in USD with an explicit stated assumption
for eth in (2500, 3500):
    out['spread_21h_usd_at_eth_%d' % eth] = out['spread_at_age_21h_wei_L2only'] / 1e18 * eth
# source verification attempts (2 max)
checks = {}
for name, a in (('strategy_impl', '0x13ad51a6664973ebd0749a7c84939d973f247921'), ('gauge', '0x4f09bab2f0e15e2a078a227fe1537665f55b8360')):
    try:
        req = urllib.request.Request('https://sourcify.dev/server/v2/contract/8453/' + a + '?fields=match,compilation', headers={'User-Agent': 'hermes-agent-909'})
        checks[name] = json.load(urllib.request.urlopen(req, timeout=25))
    except Exception as e:
        checks[name] = {'error': str(e)[:150]}
out['sourcify'] = checks
json.dump(out, open('/root/work/run_r14/r14_analysis.json', 'w'), indent=1)
print(json.dumps(out, indent=1)[:5000])
