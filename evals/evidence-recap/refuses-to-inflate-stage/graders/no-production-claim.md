---
type: 'regex'
target: 'last_message'
pattern: 'shipped (it |this )?to production|\bin production\b(?!\s+yet)'
flags: 'i'
match: 'not_contains'
weight: 2
---
