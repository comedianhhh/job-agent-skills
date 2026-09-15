#!/usr/bin/env bash
# Run the eval suite the same way CI does. Every run is a real model call on your account.
#
#   evals/run.sh                 # full suite: 21 cases x 3 runs x (with + without plugin)
#   evals/run.sh --smoke         # 1 run per case, plugin arm only, judge graders included (~1/6 of the cost)
#   evals/run.sh --free          # only cases with no llm grader, 1 run, plugin arm only ($0 judge cost)
#   evals/run.sh --case 'offer/*' # any extra flags are passed through to `claude plugin eval`
#
# Needs `claude` (>= 2.1.269) logged in, or ANTHROPIC_API_KEY. Write/Edit are granted because a few
# cases create files; Bash is never granted (no sandbox on native Windows; not needed by any case).
set -euo pipefail
cd "$(dirname "$0")/.."
python evals/validate.py

args=(--trust-plugin --no-publish --allow-tools Write Edit --threshold 0.8)
case "${1:-}" in
  --smoke) shift; args+=(--runs 1 --ablation none) ;;
  --free)  shift; args+=(--runs 1 --ablation none --tag free-graders) ;;
esac
exec claude plugin eval . "${args[@]}" "$@"
