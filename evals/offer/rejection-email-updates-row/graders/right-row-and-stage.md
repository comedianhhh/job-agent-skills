---
type: 'llm'
weight: 2
---

PASS if the response changes (or shows the change for) the Acme Corp — Backend Engineer, Payments row only, sets its status to REJECTED, and notes the stage at which it was rejected (after application / before any screen), and does not touch the Northstar or Maple Bank rows.
FAIL if it changes another row, sets a status other than REJECTED, or drops the row instead of keeping it with the stage noted.
