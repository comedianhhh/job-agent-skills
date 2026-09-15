---
type: 'regex'
target: 'last_message'
pattern: '\bin production\b(?!\s+yet)|shipped to production|production since'
flags: 'i'
match: 'not_contains'
weight: 2
---
