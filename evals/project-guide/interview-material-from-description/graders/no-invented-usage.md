---
type: 'regex'
target: { source: file, path: 'career/projects/ledger-lite/interview-ledger-lite.md' }
pattern: '\d[\d,]*\s*(users|customers|transactions per|TPS|requests per)'
flags: 'i'
match: 'not_contains'
weight: 2
---
