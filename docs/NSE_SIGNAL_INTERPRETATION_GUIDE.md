# NSE Signal Interpretation Guide

> Repository adaptation of the supplied **NSE Momentum Screener — Signal Interpretation Guide** (Aug 2026). The supplied guide is the reference for *interpretation/action design*; `docs/LOCKED_SPEC.md` remains authoritative for project-level mathematics and data definitions.

## 1. Source hierarchy

The guide distinguishes:
- **Stan Weinstein — Secrets for Profiting in Bull and Bear Markets (1988):** stage structure, 30-week MA concept, volume/distribution interpretation.
- **William O'Neil — How to Make Money in Stocks (1988):** Relative Strength leadership and breakout/entry principles.
- **System design decisions:** combined RS + Stage action labels are project-created, not claimed as rules explicitly defined by either book.

## 2. Core interpretation

### Stage

- **Stage 1 — Basing:** price at/below 30W MA, MA rising.
- **Stage 2 — Advancing:** price above 30W MA, MA rising. Primary ownership/buy zone.
- **Stage 3 — Topping:** price above 30W MA, MA flat/falling. Exit/reduction zone.
- **Stage 4 — Declining:** price at/below 30W MA, MA flat/falling. Avoid/exit zone.

Stage has precedence when it conflicts with RS. In particular, high RS in Stage 4 means relative leadership in a weak market, not a reason to hold.

### RS

The supplied guide uses these interpretation bands:
- **80–99:** leadership / eligible for strongest buy consideration.
- **50–79:** adequate but not leadership.
- **<50:** lagging.

The guide explicitly says neither book defines a combined RS+Stage mechanical action system.

### Volume

- Volume Ratio > 1.5× = strong breakout-volume evidence.
- U/D > 1.3 = accumulation confirmation.
- U/D < 0.7 = distribution warning.
- U/D < 0.6 = heavy distribution.

Volume is treated as a modifier/confirmation layer rather than silently replacing Stage or RS.

## 3. Nine-label action framework from the guide

| Stage | RS | Volume / setup | Guide label |
|---|---:|---|---|
| Stage 2 | >=80 | breakout confirmed | BUY★ |
| Stage 2 | >=80 | partial breakout confirmation | BUY |
| Stage 2 | >=80 | pullback + volume drying | BUY |
| Stage 2 | >=80 | accumulating / normal holding | HOLD |
| Stage 2 | >=80 | extended >20% | WAIT |
| Stage 2 | >=80 | slipping / below 50DMA | WAIT |
| Stage 2 | >=80 | distribution | REDUCE |
| Stage 2 | 50–79 | breakout/pullback | WAIT |
| Stage 2 | 50–79 | accumulating/holding | HOLD |
| Stage 2 | 50–79 | distribution | REDUCE |
| Stage 2 | <50 | any | WAIT |
| Stage 3 | any | normal/heavy distribution | REDUCE |
| Stage 3 | <50 | any | SELL |
| Stage 4 | any | any | SELL |
| Stage 1 | >=80 | any | WATCH★ |
| Stage 1 | 50–79 | any | WATCH |
| Stage 1 | <50 | any | AVOID |

## 4. Important practical rules

- **Stage 4 = SELL.** High RS does not override Stage 4.
- **Stage 3 = REDUCE** even when RS remains high; RS is lagging.
- **Stage 2 + distribution = REDUCE** before Stage 3 is confirmed.
- High-RS Stage 1 = **WATCH★**, not BUY; wait for Stage 2 breakout.
- A strong BUY/BUY★ signal can still be a poor *entry timing* signal if the stock is excessively extended above the MA.
- WAIT should identify the missing condition explicitly (for example, RS gap or missing breakout confirmation).
- BUY★ means all principal entry conditions are confirmed; it does not mean the price is necessarily at an ideal entry point.

## 5. Project adaptation required for RS-Stages

The supplied guide was written against a Nifty 500/yfinance research session. RS-Stages is locked to the **official Nifty Total Market constituent universe**, with calendar-based 3/6/9/12-month RS, a 30-calendar-week MA, 10-session slope, 52-calendar-week high, prior-50-session volume baseline, and 20-session U/D ratio. See `docs/LOCKED_SPEC.md`.

Therefore this guide must NOT silently change those mathematical definitions. It is an interpretation layer only.

## 6. Decisions still requiring explicit project lock

Before changing production Action logic, resolve these conflicts explicitly:

1. **RS buy threshold:** supplied guide says 80; current production UI logic has been using 85 for BUY and 70 for HOLD. This must be decided, not guessed.
2. **Action vocabulary:** supplied guide has 9 labels (BUY★, BUY, HOLD, WAIT, WATCH★, WATCH, REDUCE, SELL, AVOID); current UI has a smaller action vocabulary. Decide whether the full nine-label framework becomes production UX.
3. **Breakout semantics:** locked quantitative spec keeps `Breakout` and `Breakout_Confirmed` separate. The guide should use those existing fields rather than redefine them.
4. **Extension:** the guide uses extension as an entry-timing caution. It should remain separate from the core mathematical Stage classification unless explicitly locked otherwise.
5. **Market-regime filter:** the guide mentions broad-market condition for practical buy decisions, but the current locked quantitative spec does not yet define a market-regime gate. Do not add one implicitly.
6. **Purchase-price exits:** O'Neil's 7–8% purchase-price stop cannot be implemented from the current snapshot because RS-Stages does not track individual purchase prices. Do not fabricate this field.

## 7. Interpretation card

Every stock detail should expose, at minimum:

**Action → Stage → RS → Volume Ratio → U/D → Breakout → Breakout Confirmed → Extension → exact reason/wait note → source/design note.**

The action is a transparent interpretation layer over the quantitative outputs. It must never hide the underlying numbers.

---

**Source document:** `NSE_Signal_Interpretation_Guide.pdf`, supplied Aug 2026.
**Project authority:** `docs/LOCKED_SPEC.md`.
