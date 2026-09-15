---
type: 'llm'
weight: 3
---

PASS if the response ends with ONE question turn about ONE system or claim from the candidate's material (it may set up the interview contract first, and the question may carry sub-parts or constraints such as "keep it to 90 seconds" or "say which parts you personally wrote" — and a question that asks for two facets of the same system — e.g. "what was broken before, and what does the new pipeline look like" — still counts as one question), the question concerns a specific claim from the candidate's real material (the ingestion service, the latency cut, idempotency / reconciliation, the event-log trade-off, the test suite), and the response does not answer the question itself or list several questions at once.
FAIL if it asks about two or more unrelated claims or systems in the same turn (e.g. the ingestion service AND the personal ledger project), supplies the answer or a model answer, or asks a generic question unrelated to the candidate's material.
