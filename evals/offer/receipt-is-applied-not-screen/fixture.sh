#!/usr/bin/env bash
# Scaffold: copy the case's read-only resources/career into the run workspace as ./career
# so skills find the files where they expect them. Runs only with `claude plugin eval --scaffold`.
set -euo pipefail
case_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -R "$case_dir/resources/career" ./career
