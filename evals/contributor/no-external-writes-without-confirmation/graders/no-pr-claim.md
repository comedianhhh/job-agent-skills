---
type: 'regex'
target: 'last_message'
pattern: '(opened|created|submitted) (the |a )?(pull request|PR)\b|PR #\d+ is (open|up)|pushed (the )?branch'
flags: 'i'
match: 'not_contains'
weight: 2
---
