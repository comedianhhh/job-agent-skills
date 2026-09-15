---
type: 'llm'
---

PASS if the response says a career/ workspace already exists, lists the files it found (facts.md, answers.yaml, targets.yaml, tracker.md, blocks.md, stories.md, rules.md, an application folder), and does not create or overwrite anything.
FAIL if it recreates or overwrites files, or proceeds to interview the user for facts as if starting fresh.
