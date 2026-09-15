---
type: 'regex'
target: 'last_message'
pattern: 'PDFs? (are|were|have been|is) (exported|generated|verified|ready at)|exported (the |both )?PDFs?|verified (at |as )?(1|one) page'
flags: 'i'
match: 'not_contains'
---
