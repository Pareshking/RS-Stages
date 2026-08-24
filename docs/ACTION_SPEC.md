# RS-Stages — Production Action Specification

**Status:** LOCKED — v2.0 action layer  
**Date:** 2026-08-24  
**Authority:** `docs/NSE_SIGNAL_INTERPRETATION_GUIDE.md`

The supplied NSE Signal Interpretation Guide is now the production specification for the interpretation/action layer. The earlier five-label Action overlay is retired.

## 1. Action vocabulary

The production vocabulary is:

`BUY★`, `BUY`, `HOLD`, `WAIT`, `WATCH★`, `WATCH`, `REDUCE`, `SELL`, `AVOID`.

The star means the strongest version of the corresponding setup; it is not a probability or performance claim.

## 2. Precedence

1. Stage 4 → `SELL`.
2. Stage 3 → `SELL` when RS < 50; otherwise `REDUCE`.
3. Stage 1 → `WATCH★` when RS ≥ 80; `WATCH` when RS 50–79; `AVOID` when RS < 50.
4. Stage 2 → evaluate distribution, RS band, timing warnings and breakout state.

Stage therefore has precedence over RS when the two conflict.

## 3. Stage 2 rules

For RS ≥ 80:

- Distribution (`U/D < 0.7`) → `REDUCE`.
- Extension >20% above the 30W MA → `WAIT`.
- Below 50DMA → `WAIT`.
- Confirmed breakout → `BUY★`.
- Breakout setup without confirmation → `BUY`.
- Otherwise → `HOLD`.

For RS 50–79:

- Distribution → `REDUCE`.
- Breakout/pullback without leadership → `WAIT`.
- Otherwise accumulating/holding → `HOLD`.

For RS < 50:

- `WAIT`.

## 4. Operational definitions

These definitions convert the guide's directly stated practical conditions into deterministic fields:

- **RS 80–99:** leadership band.
- **RS 50–79:** adequate but not leadership.
- **RS <50:** lagging.
- **Distribution:** U/D < 0.7.
- **Heavy distribution:** U/D < 0.6.
- **Extended >20%:** latest Close > 1.20 × latest 30-calendar-week MA.
- **50DMA:** 50 completed-session simple moving average of Close; `Below_50DMA` is Close < SMA50.
- **Breakout:** existing locked breakout field.
- **Breakout Confirmed:** existing locked confirmed-breakout field.

The project does not fabricate a pullback/volume-drying state unless a separately validated quantitative field exists. This prevents the Action layer from inventing evidence.

## 5. Transparency requirement

Every stock Action must expose:

- Action
- Stage
- RS Score and RS band
- 30W MA and slope
- 52W high/proximity
- Volume Ratio
- U/D and distribution state
- Breakout
- Breakout Confirmed
- 50DMA state
- Extension state
- exact Action reason
- source/design note

The Action is an interpretation layer. It never replaces or hides the underlying calculations.

## 6. Source attribution

- Stage structure and 30-week MA concept: Stan Weinstein.
- RS leadership and breakout principles: William O'Neil.
- The combined nine-label mechanical action mapping is a project specification adopted from the supplied guide; it is not represented as a verbatim rule from either book.
