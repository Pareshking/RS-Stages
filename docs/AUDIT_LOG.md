# RS-Stages — Audit Log

## 2026-08-24 — Initial quantitative foundation

### Finding 1 — Calendar-window enforcement
- **Class:** Mathematical / testing gap
- **Finding:** Calendar-based 30W MA and 52W high must not degrade into arbitrary row-count windows.
- **Resolution:** Pure calculation layer enforces complete calendar windows; 52W high also requires at least 200 valid sessions.
- **Validation:** Synthetic tests added for insufficient and sufficient history.

### Finding 2 — Pre-market information boundary
- **Class:** Time-series / look-ahead control
- **Finding:** The upcoming decision session must never enter a signal calculation.
- **Resolution:** Latest completed session is explicitly selected as the terminal information date; tests cover exclusion of a later session.

### Finding 3 — Volume baseline boundary
- **Class:** Mathematical
- **Finding:** Latest completed-session volume must not contaminate its own 50-observation baseline.
- **Resolution:** Production definition is 50 prior observations with `min_periods=50`, followed by `shift(1)`.

### Finding 4 — U/D boundary and unchanged sessions
- **Class:** Mathematical / time-series
- **Finding:** U/D must use 20 completed sessions, include the latest completed session, exclude the upcoming session, and assign unchanged closes to neither side.
- **Resolution:** Explicit implementation and synthetic tests added.

### Finding 5 — CI evidence
- **Class:** Testing gap
- **Finding:** Repository CI is configured, but tests are not considered passed until GitHub produces actual execution evidence.
- **Resolution:** Maintain explicit unverified status until workflow execution is observed.
