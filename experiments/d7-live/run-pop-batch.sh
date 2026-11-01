#!/usr/bin/env bash
cd "$(dirname "$0")"
for seed in 11 12 13; do
  RPC_URL=http://127.0.0.1:8545 SEED=$seed ACTORS=36 DAYS=150 timeout 1500 node sim-population.mjs > results/population-seed$seed.log 2>&1; echo "seed $seed rc=$?" >> results/pop-batch.status
done
echo done >> results/pop-batch.status
