# RS-Stages UI Specification

**Status:** Project UI contract

The UI is a research product, not a generic Streamlit demo. The visual benchmark is WealthStar's information architecture and density, adapted to RS-Stages' locked Nifty Total Market methodology and a white/light canvas.

## Non-negotiable principles

- No file upload workflow for normal users.
- No manual date entry for the production decision session.
- Read the validated repository snapshot automatically.
- White/light, restrained, professional visual language.
- Compact typography and high information density without clutter.
- Numbers must be formatted for humans: percentages, multiples, ₹ crore/lakh, integer RS scores; never raw floating-point dumps.
- Mobile layout must remain usable: two-column metric grid, horizontally scrollable navigation/tables where necessary, no giant stacked cards for every field.
- Individual stock pages must use a real interactive financial chart. Prefer TradingView Lightweight Charts with repository-supplied data; do not use an Advanced Chart widget that silently substitutes an unsupported/default symbol.
- Every important number must have context: date, unit, period or formula.
- Action is the final decision-support column in research tables and must remain visibly separate from the locked quantitative engine.

## Information architecture

1. **Dashboard** — market-at-a-glance metrics, stage breadth, leadership board, action board, strongest candidates.
2. **Screener** — full-universe ranking with Industry, Stage, Action, minimum RS, liquidity and symbol/company filters.
3. **Industries** — industry breadth and leadership using the exact NSE CSV Industry field.
4. **Movers** — available quantitative movers/setups, clearly labelled according to the data actually available; never invent daily change data.
5. **Stock** — individual company header, Action, RS/stage/returns, interactive price + 30W MA chart, checklist, calculation detail.
6. **Methodology** — locked formulas, information boundary, data source and transparent Action overlay.

## Action overlay

- BUY = Stage 2 + RS >= 85 + confirmed breakout.
- HOLD = Stage 2 + RS >= 70 without BUY condition.
- REDUCE = Stage 3.
- SELL = Stage 4.
- WAIT = everything else.

These are project-level interpretation rules, not claims that Stan Weinstein or the source books specified an RS=85 threshold.

## Quantitative integrity

The UI must never modify or recompute the locked mathematical universe through optional filters. Filtering is presentation-only. The authoritative definitions remain in `docs/LOCKED_SPEC.md` and `docs/FORMULAS.md`.
