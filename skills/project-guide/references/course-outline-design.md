# Course outline design

Inspect entry points, main features, and module dependencies first; build the whole-project picture from one representative end-to-end flow, then place other independent behaviours into lessons. Lesson count comes from real learning goals, not from counting files, classes, or topics.

Each lesson answers one concrete project question — how one request is handled, how a background job goes from submission to terminal state, how one frame's AI tick is scheduled. Helpers, config, and state fields belong to the flow they serve; adjacent lessons that need the same main evidence to answer the same question are merged. Complex flows may be layered: the public interface first, then a later lesson for a sub-flow that can be learned on its own.

## `tutorial.md` structure

File header:

- project purpose and this course's learning goal;
- source version and any local changes that affect conclusions;
- prerequisite knowledge;
- coverage this time and modules not yet covered.

Each lesson must contain:

1. a stable number, title, and the question the reader can answer afterwards;
2. the main chain `trigger → entry → key calls or events → important branches → result`;
3. numbered must-read paths and symbols, each with input, next step, and output;
4. optional evidence for verifying behaviour;
5. adjacent implementation deferred, and which lesson owns it;
6. status `outline`, to distinguish from expanded lessons.

Pure configuration or declarative projects are organised as load → parse → rules take effect → visible result, with the boundary of accessible source stated. Never invent lifecycle stages to fill the template, and never present a directory or an unordered file list as a reading route.

## Outline check

- every main feature has a clear owner lesson;
- lessons are ordered by learning dependency;
- a learner can find the real source by following the route;
- adjacent lessons do not repeat the same core flow;
- uncovered modules and uncertain boundaries are listed;
- already-expanded lessons keep their text unless the user asks for a rewrite.
