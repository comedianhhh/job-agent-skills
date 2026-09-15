---
type: 'regex'
target: 'last_message'
pattern: '\d[\d,]*\s*(users|customers|transactions per|TPS|requests per)'
flags: 'i'
match: 'not_contains'
weight: 2
---
