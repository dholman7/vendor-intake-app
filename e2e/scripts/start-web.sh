#!/usr/bin/env bash
# Dev server locally; production standalone build in CI.
set -euo pipefail
cd "$(dirname "$0")/../../frontend"

if [[ -z "${CI:-}" ]]; then
  exec npm run dev
fi

npm run build
# The standalone server doesn't bundle static assets; copy them next to it.
cp -r .next/static .next/standalone/.next/static
[[ -d public ]] && cp -r public .next/standalone/public
PORT=3000 HOSTNAME=127.0.0.1 exec node .next/standalone/server.js
