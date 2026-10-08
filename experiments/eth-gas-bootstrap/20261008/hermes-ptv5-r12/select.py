import json
r = json.load(open('/root/work/r12/registry.json')); t = json.load(open('/root/work/r12/tvl.json'))['8453']
tested = ['aerodrome-usdc-alusdb','aerodrome-bd-usdc','aerodrome-virtual-aero','aerodrome-msusd-frxusd','aerodrome-weth-edel','aerodrome-lcap-eusd','aerodrome-usdc-send','aerodrome-synd-weth']
def cow(x):
    return 'cow' in x['id'].lower() or x.get('type') == 'cowcentrated' or 'cow' in (x.get('tokenProviderId') or '').lower() or 'cow' in (x.get('token') or '').lower()
c = [x for x in r if x['status'] == 'active' and x.get('type') == 'standard' and not cow(x) and t.get(x['id'], 0) > 0 and x['id'] not in tested and not x.get('paused') and not x.get('retired')]
c.sort(key=lambda x: -t[x['id']])
sel = c[:16]
json.dump({'rule': 'status=active,type=standard,not cow (id/token/type contains cow), tvl>0, not tested8, top16 by tvl', 'eligible': len(c),
           'candidates': [{'id': x['id'], 'vault': x['earnContractAddress'], 'tvl': t[x['id']], 'strategyTypeId': x.get('strategyTypeId')} for x in sel]},
          open('/root/work/r12/selected.json', 'w'), indent=1)
for x in sel: print(x['id'], round(t[x['id']]), x['earnContractAddress'])
print(len(c))
