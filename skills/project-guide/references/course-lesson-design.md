# Single-lesson design

Read the lesson's outline entry, its neighbouring boundaries, and the current implementation first. Keep the lesson number and topic; expand it into directly learnable content. If the topic has been made obsolete by source changes, explain the difference and suggest an adjustment — do not force the old flow.

## Teaching order

1. **Scenario and goal** — what triggers this flow, what the learner should be able to explain at the end, and the minimum of prerequisite concepts.
2. **Main chain and reading order** — show the full main chain, then the must-read order of real files and symbols; separate optional from deferred source.
3. **Guided walk along the flow** — follow the call order: key inputs, next call, state changes, return points. Quote only the short snippets needed to explain behaviour.
4. **Important branches** — explain conditions and outcomes where they occur. For async boundaries, explain the request's return and the background completion separately.
5. **Full walk-through** — replay entry to result with one concrete input, then connect the failure, recovery, and cleanup paths the source actually implements.

Branches are variants of the same scenario — never chained into one execution that cannot happen. If there is no retry, deletion, or cleanup implementation, say where the flow stops; do not invent the capability. Explain the practical difference between re-submitting, retrying the original object, and creating a new one only when idempotency or object identity affects the current branch.

## Completion criteria

- main sections follow the real call or event order;
- every conclusion can be located in code, tests, or explicit configuration;
- design trade-offs and algorithm detail only where they affect understanding of the flow or the user asks;
- the final section has a short flow recap and one task for the learner to retell in their own words — running the project is not required;
- unconfirmed dynamic targets and external-dependency boundaries are marked;
- this lesson's status becomes `expanded`; other lessons stay as they were.
