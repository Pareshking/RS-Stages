# RS-Stages — Validation Protocol

**Status:** Initial protocol  
**Purpose:** Define how RS-Stages mathematics and implementation will be independently validated.

## 1. Validation Principle

A calculation is not considered correct because the application runs or because its output appears plausible.

Evidence must follow:

**Claim → Independent Calculation/Test → Result → Conclusion**

Critical formulas must be validated independently of the production implementation wherever practical.

## 2. Information Boundary

All signal calculations are evaluated using only information available before the upcoming NSE session opens.

The latest completed NSE session is the terminal observation. The upcoming decision/execution session must never enter a signal calculation.

Tests must explicitly include this boundary.

## 3. Synthetic Formula Tests

Create controlled datasets with manually known answers for:

1. Calendar-month reference dates.
2. RS returns.
3. 40/20/20/20 weighted blend.
4. Percentile ranking, including ties.
5. 30-calendar-week MA.
6. 10-session slope.
7. 52-calendar-week high.
8. ≥200 valid-session requirement.
9. 3% near-high test.
10. Prior-50-session volume baseline and shift.
11. Up/down volume classification.
12. 20-session U/D ratio.
13. Zero denominator cases.
14. Breakout and Breakout Confirmed precedence.
15. Liquidity filter isolation.

## 4. Independent Implementations

For critical formulas, the reference test should use a method sufficiently independent from production code to detect shared implementation mistakes.

Examples:

- direct Python arithmetic for hand-checkable formulas;
- NumPy/Pandas reference calculations;
- explicit loops versus vectorized production calculations;
- manually constructed expected outputs.

The independent implementation must not simply call the production function and compare its result to itself.

## 5. Calendar-Date Tests

Tests must verify that:

- calendar months are not replaced by fixed trading-day counts;
- calendar weeks are not replaced by fixed row counts;
- non-trading target dates resolve to the last available session on or before the target date;
- missing observations do not silently change the intended calendar window;
- the latest completed session is used for pre-market decisions.

## 6. Edge Cases

At minimum test:

- empty input;
- insufficient history;
- exactly sufficient history;
- one observation;
- missing observations;
- NaNs;
- duplicate dates;
- unsorted dates;
- unchanged closes;
- zero volume;
- zero down volume;
- extreme values;
- market holidays;
- newly listed stocks;
- incomplete latest session.

## 7. Look-Ahead and Leakage Tests

Explicitly prove that:

- future sessions cannot affect historical signals;
- the upcoming execution session is excluded;
- the volume baseline excludes the latest session's volume;
- universe ranking uses only data available at the decision date;
- liquidity filtering does not alter the underlying RS ranking;
- no future corporate information is injected into historical calculations.

## 8. Regression Testing

After every quantitative change:

1. Re-run formula tests.
2. Re-run relevant edge-case tests.
3. Re-run integration tests.
4. Compare outputs against previously validated fixtures.
5. Investigate every unexpected numerical change.

A changed output is not automatically a regression or automatically correct; its cause must be established.

## 9. Completion Standard

A quantitative component is complete only when:

- its formula is documented;
- its source/methodology interpretation is documented;
- an independent expected result exists;
- critical edge cases are tested;
- the pre-market boundary is tested;
- regression coverage exists;
- implementation output matches the independent calculation.

Only after these conditions are satisfied may the component be considered mathematically validated.

## 10. Validation Evidence

Validation results should record:

- test name;
- mathematical claim;
- input dataset;
- expected result;
- production result;
- independent result;
- tolerance, if any;
- pass/fail;
- interpretation;
- relevant commit.

For exact arithmetic or deterministic discrete classifications, prefer exact equality rather than loose tolerances.
