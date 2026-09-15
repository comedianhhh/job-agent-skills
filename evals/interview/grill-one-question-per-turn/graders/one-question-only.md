---
type: 'llm'
weight: 3
---

PASS if the response ends by asking the candidate exactly ONE interview question (it may briefly set up the interview contract or say what round it is first), the question concerns a specific claim from the candidate's real material (the ingestion service, the latency cut, idempotency / reconciliation, the event-log trade-off, the test suite), and the response does not answer the question itself or list several questions at once.
FAIL if it asks two or more questions in the same turn, supplies the answer or a model answer, or asks a generic question unrelated to the candidate's material.
