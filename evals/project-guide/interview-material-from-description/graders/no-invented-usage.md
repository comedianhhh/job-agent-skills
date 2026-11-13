---
type: 'regex'
target: { source: file, path: 'career/projects/ledger-lite/interview-ledger-lite.md' }
pattern: '\b[1-9][\d,]*\s*(users|customers|transactions per|TPS|requests per)'
flags: 'i'
match: 'not_contains'
weight: 2
---
