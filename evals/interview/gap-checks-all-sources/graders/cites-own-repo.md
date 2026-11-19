---
type: 'regex'
target: 'last_message'
pattern: 'ledger-lite[\s\S]{0,400}Kafka|Kafka[\s\S]{0,400}ledger-lite'
flags: 'i'
match: 'contains'
---
