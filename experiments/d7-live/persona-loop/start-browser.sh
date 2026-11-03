#!/usr/bin/env bash
# start-browser.sh N PORT : launch the phone browser for persona N (device, colour scheme and font scale from scenarios.json)
P="$(cd "$(dirname "$0")" && pwd)"
N=$1; PORT=$2; ID=$(printf "p%03d" $N)
read -r DEV SCHEME FONT < <(python3 -c "
import json; s=json.load(open('$P/scenarios.json'))[$N-1]; print(s['device'].replace(' ','_'), s['scheme'], s['fontscale'])")
DEV=${DEV//_/ }
rm -rf $P/results/$ID; mkdir -p $P/results/$ID
W=${3:-1}; case $W in 2) WEBP=4174; CTRLP=4181;; 3) WEBP=4175; CTRLP=4182;; *) WEBP=4173; CTRLP=4180;; esac
cd $P && exec node browser-server.mjs --port $PORT --id $ID --device "$DEV" --scheme $SCHEME --fontscale $FONT --base http://localhost:$WEBP --world http://127.0.0.1:$CTRLP --out $P/results/$ID >> $P/results/$ID.server.log 2>&1
