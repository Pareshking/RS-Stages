# RS-Stages UI Specification

**Status:** LOCKED — v2.0

The UI is a quantitative research product. The visual benchmark is WealthStar's information architecture and density, adapted to RS-Stages' Nifty Total Market methodology and a clean white/light canvas.

## Non-negotiable principles

- No file-upload workflow for normal users.
- No manual decision-date entry for production use.
- Read the validated repository snapshot automatically.
- White/light canvas with subtle semantic colour accents.
- Strong typography hierarchy and compact professional density.
- No giant cards whose only purpose is displaying raw numbers.
- Percentages, multiples, INR values and RS scores are human-formatted.
- Mobile layout must remain usable.
- Stock pages use an actual interactive financial chart driven by repository-supplied data. TradingView Lightweight Charts is the preferred library.
- Never use an Advanced Chart widget that silently substitutes an unsupported/default symbol.
- Every important number has context: date, unit, period or formula.
- Action is the final decision-support column and is visibly separated from the quantitative evidence.

## Navigation

1. **Dashboard** — market snapshot, stage breadth, Action distribution, leadership and strongest setups.
2. **Screener** — full-universe table with Industry, Stage, RS, setup evidence and Action as the final column.
3. **Industries** — industry leadership, breadth and Action concentration.
4. **Movers** — available quantitative movers/setups; no fabricated daily-change series.
5. **Stock** — company header, Action, evidence strip, interactive price/30W MA chart, checklist and calculation detail.
6. **Methodology** — formulas, source material, information boundary and the full nine-label Action framework.

## Action framework

The previous five-label UI is retired. Production uses:

`BUY★`, `BUY`, `HOLD`, `WAIT`, `WATCH★`, `WATCH`, `REDUCE`, `SELL`, `AVOID`.

The detailed deterministic rules live in `docs/ACTION_SPEC.md` and `rs_stages/actions.py`.

The screener's **Action column must be the final column** so the table reads as evidence → decision.

## Stock page requirements

The stock page must present, in order:

1. Symbol/company/industry.
2. Large semantic Action treatment and exact reason.
3. Stage + RS + RS band.
4. Breakout/confirmation and timing warnings.
5. Price + 30W MA interactive chart.
6. Evidence checklist.
7. Calculation detail with properly formatted values.
8. Method/source note.

## Visual language

Use subtle semantic accents:

- Green: BUY / BUY★ and positive confirmation.
- Blue: HOLD / neutral leadership.
- Amber: WAIT / WATCH.
- Orange: REDUCE.
- Red: SELL / AVOID.

Accents should be restrained; the page must remain predominantly white/light neutral.

## Quantitative integrity

UI filters are presentation-only and must never recompute the RS ranking universe. The Action layer consumes validated outputs and cannot fabricate missing quantitative evidence.
