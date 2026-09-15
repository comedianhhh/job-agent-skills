# Practice question design

Read the corresponding lesson in `tutorial.md`. Questions test only flows and knowledge already taught. While a lesson is still `outline`, only reading-guidance questions are allowed; if the user asks for comprehension questions, say the lesson must be expanded first — untaught content is not "learned".

## Question structure

`practice.md` mirrors the lesson numbers and titles and notes the lesson's status. Each question has one independent answering goal, starts from a project scenario, and asks the learner to explain cause and effect with source evidence, for example:

- which entry an input starts from, which key calls it passes through, where it returns or changes state;
- when a taught branch fails, which operations have already completed and what the caller or user sees;
- when the lesson covered a recovery path, what conditions allow recovery and how it differs from re-submitting.

These are question *types*; the actual questions must come from the lesson. Details of the same flow become natural follow-ups; questions whose answers and main evidence overlap heavily are merged. Question count is set by independent goals, not a fixed number.

## Expression boundaries

- Questions and answer requirements only; no model answers unless the user asks.
- Test flow and responsibility understanding — not spelling of field names, and no implicit coding, test-design, or refactoring assignments.
- Architecture trade-off questions only if the lesson taught the design reasoning or the user asks.
- When the user submits answers, point out what was explained, what was missed, and what was wrong for that question and its source — never infer mastery of the whole project from one question.

## Partial update check

- new or updated lesson numbers and titles match `tutorial.md`;
- questions stay within the lesson's scope;
- other lessons, existing questions, and the user's answers are untouched;
- practice is re-ordered with the course only when the user asks to sync.
