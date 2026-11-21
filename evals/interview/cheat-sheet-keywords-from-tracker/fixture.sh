#!/usr/bin/env bash
# Scaffold: copy the shared career/ fixture, then move the Acme row to TECH with an interview date
# that appears nowhere else, so the cheat sheet can only get it from tracker.md.
# Runs only with `claude plugin eval --scaffold`.
set -euo pipefail
case_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -R "$case_dir/resources/career" ./career
sed -i 's/| `APPLIED` | follow up on LinkedIn 2026-09-16 |/| `TECH` | hiring-manager technical 2026-09-24 14:00 ET (Priya Shah) |/' ./career/tracker.md
grep -q '2026-09-24 14:00 ET' ./career/tracker.md
