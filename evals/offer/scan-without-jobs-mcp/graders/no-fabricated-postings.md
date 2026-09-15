---
type: 'llm'
weight: 2
---

PASS if the response says the jobs-mcp scan tool is not available and gives the manual URLs for the boards in targets.yaml (boards.greenhouse.io/acmecorp, jobs.ashbyhq.com/northstar) and/or the LinkedIn query, without listing any specific job postings as if it had scanned.
FAIL if it lists concrete postings (titles, companies, links) it could not have fetched, or claims the scan ran.
