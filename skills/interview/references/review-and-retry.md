# Review and retry

Read this in Review or Retry mode.

## Review output

The review is based on the session ledger and the user's real answers:

```text
## Resume Mastery Review

### Scope
- Role / round: …
- Covered: …
- Not covered: …

### Verified
- Claim: …
  Evidence: the user explained …

### Partially verified
- Claim: …
  Evidence so far: …
  Gap: …

### Unverified or contradictory
- Claim: …
  Basis: …
  Fix: add fact / learn / tone down wording

### Before the interview
1. …

### Retry queue
1. Claim: …
   Next question type: variant / counterfactual / failure / metric definition
```

Never infer mastery of the whole resume from a handful of answers. Use `not covered` where there is no evidence, not a low score.

## Priority

Order the pre-interview actions:

1. JD-critical claims with a fabrication or contradiction risk;
2. strong Ownership, Metric, and Result claims;
3. technical-understanding gaps exposed during the mock;
4. delivery-structure problems;
5. low-relevance background knowledge.

## Retry rules

Retry only `partial`, `unverified`, and `contradictory` claims. Do not repeat the original question; prefer:

- variant — change an input or constraint;
- counterfactual — does the approach still hold if a condition changes;
- failure — give a symptom, ask the user to localise it;
- evidence — ask for code, data, logs, or the metric definition;
- compression — explain the same claim in 60 seconds.

Compare evidence before and after:

```text
Last gap:  could not state the metric baseline.
This time: stated the pre-optimisation definition, sample period, and data source.
Result:    partial → verified.
```

If the user only recites last time's advice but cannot handle the variant, do not upgrade to `verified`.

## Handling resume wording

For each high-risk claim offer three options:

1. **Keep** — fact, personal boundary, and evidence are all sufficient.
2. **Tone down** — the project is real but "led / architected / significantly improved" is under-evidenced.
3. **Hold** — a key fact cannot be confirmed or contradicts earlier material.

Help the user organise real answers; never generate work history, numbers, code detail, or business results that do not exist. Any change to `career/facts.md` or `career/stories.md` requires the user's explicit confirmation.
