import json,urllib.request,datetime
u='https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources?type=http&limit=100'
d=json.load(urllib.request.urlopen(u,timeout=30))
items=d['items']
print('accessed',datetime.datetime.utcnow().isoformat()+'Z','items',len(items),'keys',list(d.keys()), d.get('pagination'))
prices=[]
for it in items:
    for a in it['accepts']:
        if a['scheme']=='exact':
            prices.append((int(a.get('amount') or a.get('maxAmountRequired')),a['network'],a['asset'][:8],it['resource'],it.get('quality',{}).get('l30DaysTotalCalls'),it.get('quality',{}).get('l30DaysUniquePayers'),it.get('quality',{}).get('lastCalledAt')))
            break
prices.sort()
amts=[p[0] for p in prices]
print('exact n',len(amts),'min',amts[0],'median',amts[len(amts)//2],'max',amts[-1])
from collections import Counter
print(Counter(p[1] for p in prices)); print(Counter(p[2] for p in prices))
for p in prices[:3]+prices[len(prices)//2:len(prices)//2+2]+prices[-2:]: print(p)
top=sorted([p for p in prices if p[4]],key=lambda p:-p[4])[:5]
print('top30d'); [print(p) for p in top]
print('with calls',sum(1 for p in prices if p[4]))
