# NSE Signal Interpretation Guide

**Status:** PRODUCTION REFERENCE — adopted as RS-Stages v2 Action specification  
**Date:** 2026-08-24

This repository document is the adopted interpretation/action reference for the supplied **NSE Momentum Screener — Signal Interpretation Guide (Aug 2026)**. It supersedes the earlier project five-label Action overlay. The mathematical RS/Stage definitions are retained in `docs/LOCKED_SPEC.md`; this guide supplies the production interpretation rules now incorporated into that locked specification.

## 1. Source hierarchy

- **Stan Weinstein — Secrets for Profiting in Bull and Bear Markets:** stage structure, 30-week MA concept and volume/distribution interpretation.
- **William O'Neil — How to Make Money in Stocks:** Relative Strength leadership and breakout/entry principles.
- **Project specification:** the combined nine-label RS + Stage Action mapping is an explicit project decision adopted from this guide; it is not represented as a verbatim mechanical rule from either book.

## 2. Stage interpretation

- Stage 1 — Basing: price at/below 30W MA, MA rising.
- Stage 2 — Advancing: price above 30W MA, MA rising. Primary ownership/buy zone.
- Stage 3 — Topping: price above 30W MA, MA flat/falling. Exit/reduction zone.
- Stage 4 — Declining: price at/below 30W MA, MA flat/falling. Avoid/exit zone.

Stage has precedence when it conflicts with RS. High RS in Stage 4 is not a reason to hold.

## 3. RS interpretation

- **80–99:** leadership / eligible for strongest buy consideration.
- **50–79:** adequate but not leadership.
- **<50:** lagging.

The former production thresholds of RS 85 for BUY and RS 70 for HOLD are retired.

## 4. Volume interpretation

- Volume Ratio >1.5× = strong breakout-volume evidence.
- U/D >1.3 = accumulation confirmation.
- U/D <0.7 = distribution warning.
- U/D <0.6 = heavy distribution.

Volume modifies/confirm signals; it does not silently replace Stage or RS.

## 5. Nine-label production Action framework

| Stage | RS | Setup / timing | Action |
|---|---:|---|---|
| Stage 2 | ≥80 | confirmed breakout | BUY★ |
| Stage 2 | ≥80 | breakout without confirmation | BUY |
| Stage 2 | ≥80 | normal accumulating/holding | HOLD |
| Stage 2 | ≥80 | extended >20% | WAIT |
| Stage 2 | ≥80 | below 50DMA | WAIT |
| Stage 2 | ≥80 | distribution | REDUCE |
| Stage 2 | 50–79 | breakout/pullback without leadership | WAIT |
| Stage 2 | 50–79 | accumulating/holding | HOLD |
| Stage 2 | 50–79 | distribution | REDUCE |
| Stage 2 | <50 | any | WAIT |
| Stage 3 | <50 | any | SELL |
| Stage 3 | ≥50 | any | REDUCE |
| Stage 4 | any | any | SELL |
| Stage 1 | ≥80 | any | WATCH★ |
| Stage 1 | 50–79 | any | WATCH |
| Stage 1 | <50 | any | AVOID |

### Timing fields adopted by RS-Stages

- **Extended >20%:** Close >1.20 × 30W MA.
- **Below 50DMA:** Close below the 50 completed-session SMA.
- **Distribution:** U/D <0.7.

The guide mentions pullback + volume drying as a buy-timing condition, but the repository does not contain a sufficiently precise validated detector for that condition. RS-Stages therefore does not fabricate one.

## 6. Action precedence

1. Stage 4 → SELL.
2. Stage 3 → SELL when RS <50; otherwise REDUCE.
3. Stage 1 → WATCH★ / WATCH / AVOID by RS band.
4. Stage 2 → evaluate distribution, RS band, timing warnings and breakout state.

A BUY★ signal means the principal quantitative entry conditions are confirmed; it does not claim that the stock is at an ideal price for every investor.

## 7. Transparency requirement

Every stock page and screener Action must expose the evidence: Action, Stage, RS, 30W MA/slope, 52W proximity, Volume Ratio, U/D, Breakout, Breakout Confirmed, 50DMA, extension and an exact Action reason.

The Action is an interpretation layer over visible quantitative outputs. It must never hide the underlying mathematics.

## 8. Project adaptation

The supplied guide used a different research universe in its original context. RS-Stages continues to use the official **Nifty Total Market** universe and the project's calendar-based 3/6/9/12-month RS, 30-calendar-week MA, 10-session slope, 52-calendar-week high, prior-50-session volume baseline and 20-session U/D definitions. Those definitions are now locked in `docs/LOCKED_SPEC.md` v2.0.
