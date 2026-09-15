---
type: 'llm'
weight: 2
---

PASS if the response created the career/ workspace from the templates, tells the user the folder is private (private repo or .gitignore), and then asks the user for their facts one section at a time (basics, work authorization, education, jobs) — using only what the user said (name Sam Rivera, data engineer, Vancouver) and leaving everything else blank or TODO.
FAIL if it fills facts.md with invented employers, dates, numbers, or skills the user never stated.
