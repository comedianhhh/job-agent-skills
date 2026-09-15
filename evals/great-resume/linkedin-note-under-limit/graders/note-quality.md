---
type: 'llm'
weight: 2
---

PASS if the response contains a connection note that is at most 300 characters long (count only the note itself, not any surrounding explanation), names who Jordan is in one clause, includes one concrete verifiable result from their work (e.g. the ingestion service, the latency cut from ~15 minutes to under 30 seconds, or zero duplicate incidents), and ends with a specific ask (a short chat, a question about the role).
FAIL if the note is over 300 characters, contains no concrete result, uses filler like "passionate" or "team player", mentions salary or visa status, or invents a result not in the candidate's facts.
