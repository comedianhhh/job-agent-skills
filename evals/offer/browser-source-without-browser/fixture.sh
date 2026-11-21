#!/usr/bin/env bash
# Scaffold: copy the shared career/ fixture, then add a Wellfound browser source to targets.yaml,
# so the scan has a signed-in-only site to search and no browser to search it with.
# Runs only with `claude plugin eval --scaffold`.
set -euo pipefail
case_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -R "$case_dir/resources/career" ./career
sed -i 's/^filters:/browser_sources:\n  - { name: wellfound, url: "https:\/\/wellfound.com\/jobs", max_results: 30 }\n\nfilters:/' ./career/targets.yaml
grep -q 'name: wellfound' ./career/targets.yaml
