---
type: 'regex'
target: 'last_message'
pattern: '^>[^\n]*(40\s?ms|p95)'
flags: 'im'
match: 'not_contains'
weight: 2
---
