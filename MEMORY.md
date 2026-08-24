# RS-Stages — Project Memory / Engineering Operating Specification

## 1. Project Identity

- Repository: `Pareshking/RS-Stages`
- Primary branch: `main`
- Primary technology: Streamlit
- Project scope: development, quantitative research, mathematical validation, testing, auditing, continuous improvement, and professional presentation of the RS-Stages system.

This file is the persistent project memory and operating specification for RS-Stages. It should be kept current as the project evolves.

---

## 2. Core Mission

The objective is not merely to write code that runs. The objective is to demonstrate that the implementation is:

1. Mathematically correct.
2. Faithful to the definitions, formulas, assumptions, methodology, and intent in the authoritative book/material.
3. Correctly translated from mathematical definitions into code without hidden deviations.
4. Quantitatively validated against independent calculations wherever practical.
5. Robust against bugs, methodological inconsistencies, data-quality problems, look-ahead bias, survivorship bias, leakage, incorrect sampling, incorrect normalization, and implementation shortcuts.
6. Explainable and reproducible for every important quantitative result.

Plausible numbers, successful execution, or superficial green tests are never sufficient evidence of correctness.

---

## 3. Mandatory Engineering Loop

Continuously operate:

**INSPECT → UNDERSTAND → FORMULATE → IMPLEMENT → TEST → VALIDATE → AUDIT → FIX → RE-TEST → VERIFY → DOCUMENT → REPEAT**

After every meaningful change:

1. Inspect affected code.
2. Identify the mathematical definition being implemented.
3. State the expected mathematical formulation conceptually or explicitly.
4. Compare implementation with formulation.
5. Test edge cases.
6. Test numerical correctness.
7. Independently reproduce important calculations where feasible.
8. Check data leakage and look-ahead bias.
9. Check unintended effects elsewhere.
10. Re-run relevant tests.
11. Verify final outputs.
12. Document the change and validation evidence.

A failed test must be traced to root cause. Do not patch symptoms. Determine whether the cause is code, data, mathematics, methodology, interpretation, or test design, then fix the appropriate layer and repeat the relevant validation.

Never stop at the first green result.

---

## 4. Book / Methodology Fidelity

The referenced book/material is the authoritative quantitative reference.

For every major calculation use:

**BOOK DEFINITION → MATHEMATICAL FORMULA → DATA REQUIREMENTS → CODE IMPLEMENTATION → NUMERICAL TEST → OUTPUT VALIDATION**

Any ambiguity must be identified explicitly.

If multiple mathematical interpretations are possible:

- identify the alternatives;
- determine which is most faithful to the author's methodology;
- test the consequences where practical;
- document the chosen interpretation.

Never silently invent assumptions.

Never change methodology merely because an alternative produces better backtest performance.

Performance does not validate incorrect mathematics.

---

## 5. Quantitative Audit Standard

### Mathematical correctness

Audit at minimum:

- Formula definitions
- Numerators and denominators
- Units
- Scaling
- Normalization
- Weighting
- Ranking
- Aggregation
- Rolling calculations
- Window definitions
- Boundary conditions
- Missing observations
- Zero values
- Negative values
- NaN handling
- Numerical precision

### Time-series correctness

Audit:

- Observation dates
- Trading-day alignment
- Period boundaries
- Lookback windows
- Rebalancing dates
- Signal dates
- Execution dates
- Forward-looking contamination
- Look-ahead bias
- Survivorship bias
- Data snooping
- Historical calculations contaminated by future information

### Statistical correctness

Audit:

- Sample vs population statistics
- Standard-deviation methodology
- Regression methodology
- R² calculations
- Correlation
- Ranking methodology
- Outlier treatment
- Missing-data treatment
- Forward filling
- Interpolation
- Rolling-window behaviour

### Financial correctness

Audit:

- Returns
- Volatility
- Risk adjustment
- Momentum
- Relative strength
- Benchmark comparison
- Portfolio weighting
- Rebalancing
- Transaction assumptions
- Corporate actions
- Benchmark alignment

Where the methodology differs from conventional practice, follow the book unless there is explicit evidence that the implementation is intentionally different.

---

## 6. Independent Validation

Critical calculations must not be validated solely by inspecting the code that generated them.

Where practical use:

- Independent second implementations
- Manual calculations
- NumPy/Pandas reference calculations
- Small synthetic datasets
- Known mathematical identities
- Controlled test datasets

For every critical formula, ask:

> If the mathematically correct answer is already known, does the application produce that answer exactly?

Synthetic datasets should be deliberately constructed so expected results can be calculated independently.

---

## 7. Data Quality Audit

Data quality is part of quantitative correctness.

Investigate:

- Missing observations
- Duplicate observations
- Incorrect timestamps
- Non-trading days
- Corporate actions
- Adjusted vs unadjusted prices
- Volume anomalies
- Forward-filled values
- Stale prices
- Universe changes
- Delisted securities
- Symbol changes
- Benchmark data
- Frequency mismatches
- Market-holiday/calendar mismatches

Never silently fill, interpolate, transform, or discard data unless the methodology permits it or the transformation has a documented quantitative justification.

---

## 8. Testing Standard

Testing must extend beyond application startup.

### Unit tests
Test individual formulas and functions.

### Mathematical tests
Compare formulas with independently calculated expected values.

### Edge-case tests
At minimum consider:

- Empty datasets
- One observation
- Insufficient history
- Missing observations
- NaNs
- Zeros
- Extreme values
- Duplicate dates
- Market holidays
- Newly listed securities
- Delisted securities
- Unusual corporate actions

### Integration tests
Verify correct flow through the quantitative pipeline.

### Regression tests
Ensure fixes do not silently alter previously validated behaviour.

### End-to-end tests
Verify the complete path from data acquisition through calculation to Streamlit output.

---

## 9. Evidence Standard / No Blind Trust

Do not use claims such as:

- "It looks correct."
- "The numbers seem reasonable."
- "The code runs, therefore it works."
- "The backtest looks good, therefore the methodology is correct."

For important conclusions use:

**Claim → Evidence → Test → Result → Conclusion**

If something cannot be verified, state that explicitly. Never manufacture confidence.

---

## 10. Streamlit Product Standard

RS-Stages should be a professional quantitative research platform rather than a generic Streamlit demo.

Required design characteristics:

- Professional
- Clean
- Minimalist
- White/light background
- Excellent typography
- Appropriate modern fonts
- Restrained colour use
- Clear visual hierarchy
- Clean tables
- Minimal borders
- Consistent spacing
- Professional tabs
- Clear navigation
- Responsive layout
- Fast-loading where practical
- Understandable without sacrificing quantitative transparency

Avoid:

- Excessive colours
- Heavy borders
- Clutter
- Unnecessary cards
- Decorative elements without purpose
- Oversized headings
- Distracting dashboards
- Poor number formatting
- Inconsistent terminology

Visual quality must never hide quantitative methodology or uncertainty.

---

## 11. Homepage Standard

The homepage should clearly explain:

- What RS-Stages does
- The methodology it implements
- Major system components
- What the user can analyse
- Important methodological notes
- Relevant data limitations

Purpose should be immediately understandable without overwhelming the user.

---

## 12. Information Architecture

Use logical professional tabs with clearly defined purposes.

Avoid unnecessary duplication.

Place tables, charts, metrics, methodology explanations, and diagnostics where they are most useful.

Quantitative outputs must include enough context to understand what each number represents.

---

## 13. Numerical Traceability

Important displayed metrics should expose, where practical:

- Calculation period
- Input data
- Formula/methodology
- Parameters
- Benchmark
- Date
- Units
- Ranking methodology
- Exclusions and filters

Avoid black-box numbers.

---

## 14. Correctness Before Performance

Correctness is the first priority.

Do not sacrifice mathematical correctness for:

- Speed
- Visual simplicity
- Fewer lines of code
- Convenience
- Better-looking results

Only optimize after correctness is established.

If optimization changes numerical behaviour, quantify and document the difference.

Priority order:

**Correctness → Evidence → Reproducibility → Robustness → Clarity → Performance → Presentation**

---

## 15. Repository Discipline

Before modifying the repository:

1. Inspect current branch.
2. Inspect repository structure.
3. Read README and relevant documentation.
4. Understand existing architecture.
5. Identify current implementation.
6. Identify existing tests.
7. Determine what has already been validated.
8. Preserve correct existing work.
9. Avoid unnecessary redesign.
10. Change only what is necessary to improve correctness, reliability, functionality, or presentation.

This is a continuation project, not a reason to restart from scratch.

---

## 16. Change Discipline

Every modification requires a reason.

For every material change record:

- What was wrong?
- Why was it wrong?
- What is the correct behaviour?
- What changed?
- How was it tested?
- What could the change affect?
- Was regression testing performed?

Do not make speculative changes.

Do not modify methodology merely because another approach is personally preferred.

---

## 17. Issue Classification

Every significant issue should be classified as one or more of:

1. Code bug
2. Mathematical bug
3. Statistical/methodological bug
4. Data-quality problem
5. Implementation-vs-book discrepancy
6. UI/UX problem
7. Performance problem
8. Testing gap
9. Documentation gap

Fix the problem at the appropriate layer.

---

## 18. Completion Gate

Never declare a feature or milestone complete until checking, as applicable:

- Code correctness
- Mathematical correctness
- Book/methodology alignment
- Data integrity
- Time-series integrity
- Look-ahead bias
- Edge cases
- Independent numerical validation
- Regression tests
- Integration behaviour
- Streamlit UI behaviour
- Output formatting
- Performance
- Documentation

The final question is:

> Can I demonstrate that the implementation is mathematically faithful, quantitatively correct, robustly tested, reproducible, and professionally presented?

Only then declare completion.

---

## 19. Current Project State

As of the initial RS-Stages handover on 2026-08-24:

- Repository exists and is public.
- Default branch is `main`.
- Repository is currently empty; no README or application files were present at the time this memory file was created.
- This `MEMORY.md` is therefore the first project document and establishes the initial engineering operating specification.
- No quantitative implementation has yet been validated from the repository.
- No book/material source has yet been added to the repository or formally mapped to formulas.

Future project-state updates must be appended or revised here as evidence becomes available.

---

## 20. Working Rule

For all future RS-Stages work, continuously apply:

**INSPECT → UNDERSTAND → FORMULATE → IMPLEMENT → TEST → VALIDATE → AUDIT → FIX → RE-TEST → VERIFY → DOCUMENT → REPEAT**

Never stop at "code completed."

Never confuse a green test with proof of mathematical correctness.

Never confuse good backtest performance with methodological validity.

Never hide assumptions, data transformations, or uncertainty.

The system must earn confidence through evidence.
