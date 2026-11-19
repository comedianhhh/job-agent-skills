#!/usr/bin/env bash
# Scaffold: copy the case's read-only resources into the run workspace: ./career plus a local clone
# of the user's own repo (./ledger-lite) that holds evidence facts.md never mentions (Kafka).
# Runs only with `claude plugin eval --scaffold`.
set -euo pipefail
case_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -R "$case_dir/resources/career" ./career
cp -R "$case_dir/resources/ledger-lite" ./ledger-lite
