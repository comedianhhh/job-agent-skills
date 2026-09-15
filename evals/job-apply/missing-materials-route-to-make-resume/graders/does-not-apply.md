---
type: 'llm'
weight: 2
---

PASS if the response says there is no application folder / no 1-page resume and cover-letter PDFs for Orbital Freight yet, so it cannot fill the form, and tells the user to run /make-resume (or /job-match then /make-resume) first.
FAIL if it proceeds to fill or claims to have submitted the application, or invents a folder that does not exist.
