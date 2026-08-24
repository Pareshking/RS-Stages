# Research Track — Weinstein Stage Fidelity

## Status

Research only. This branch does **not** alter the locked V1 production methodology.

Production V1 remains governed by `docs/LOCKED_SPEC.md` and `docs/FORMULAS.md`.

## Research question

How much of Stan Weinstein's four-stage market-structure concept is captured by the current quantitative operationalization based on:

- Close relative to the 30-calendar-week SMA;
- 10-session percentage slope of that MA.

## V1 control model

The locked V1 classifier is:

- Stage 1: Close <= 30W MA and slope > 0
- Stage 2: Close > 30W MA and slope > 0
- Stage 3: Close > 30W MA and slope <= 0
- Stage 4: Close <= 30W MA and slope <= 0

This must remain unchanged during the research experiment.

## Candidate research extensions

The research model may test, independently:

1. A slope-neutral band around zero rather than a hard zero boundary.
2. Price weaving/crossing frequency around the 30W MA.
3. Persistence of price/MA relationships rather than single-session classification.
4. Base/range detection for Stage 1.
5. Topping/range detection for Stage 3.
6. Breakout and breakdown events.
7. Volume confirmation around transitions.
8. Transition-state detection rather than treating stages as four static quadrants.

## Required methodology

Any candidate model must be evaluated against the V1 control using historical data without changing V1.

For each candidate:

- define the formula before coding;
- specify all parameters explicitly;
- avoid look-ahead information;
- use only information available at the decision date;
- test sensitivity to parameters;
- compare transition frequency and persistence;
- inspect false/early/late transitions;
- evaluate economic consequences separately from descriptive fidelity.

No candidate becomes production methodology merely because it improves returns.

## First experiment

Build a controlled comparison between the V1 classifier and a slope-neutral/weaving model. Start with synthetic sequences where the expected state is known, then evaluate on historical real-data observations.

The experiment must report where the two models disagree and why. No production code changes are permitted until a separate methodology decision is made.
