---
type: regex
target: last_message
pattern: '\b\d{1,3}\s?%\s*(match|fit)|\b(match|fit)[^.\n]{0,20}\b\d{1,3}\s?%'
flags: i
match: not_contains
---
