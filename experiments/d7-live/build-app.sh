#!/usr/bin/env bash
cd "$(dirname "$0")" && npx esbuild app/src/main.js --bundle --minify --format=esm --target=es2022 --loader:.json=json --define:process.env.NODE_ENV='"production"' --outfile=app/dist/app.js 2>&1 | tail -5
