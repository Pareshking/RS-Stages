# RS-Stages UI Specification

**Status:** LOCKED — v3.0

The UI is a quantitative research product.

**WealthStar (`https://wealthstar.bodhi.study/`) is the design source, not a loose inspiration.** Where the reference has a component that solves a problem well, replicate that component rather than inventing an alternative. What is replicated is the *visual and interaction system*:

- the design tokens (`--page`, `--card`, `--ink`, `--sub`, `--faint`, `--rule`, `--edge`, `--track`, `--up-bg`, `--down-bg`, `--blue-bg`, `--amber-bg`, `--slip-bg`, `--bar-bg`) and their values;
- the type scale, Plus Jakarta Sans, and tabular-numeral alignment on every figure;
- the dense table row: 30px avatar tile, symbol over industry, number-over-rank-bar, status dot with label, chip, right-aligned numerics, inline sparkline, 52-week range track;
- the shelf/card/stat-card language, the stacked segmented posture bar, the ranked industry row;
- the pill filter rows and the sticky pill navigation;
- the motion set: row hover-lift, bar grow-in, row fade-in, all disabled under `prefers-reduced-motion`.

What remains entirely ours: the universe, the NSE `Industry` classification, the Stage vocabulary, the RS bands, the nine-label Action framework, the column set, every guide condition and all terminology. The reference's "Setup" column maps to our **Action** column; its "Sector" tab maps to our **Industries** tab.

There is no F&O/Positioning tab: the repository has no derivatives data and `docs/LOCKED_SPEC.md` section 2 forbids F&O filtering. That tab is omitted rather than filled with an invented substitute.

## Non-negotiable principles

- No file-upload workflow for normal users.
- No manual decision-date entry for production use.
- Read the validated repository snapshot automatically.
- White/light canvas with subtle semantic colour accents.
- Strong typography hierarchy and compact professional density.
- No giant cards whose only purpose is displaying raw numbers.
- Percentages, multiples, INR values and RS scores are human-formatted.
- Mobile layout must remain usable.
- Stock pages use an actual interactive financial chart driven by repository-supplied data. TradingView Lightweight Charts is the library, used for the price/10W/30W panel and the breadth trend.
- Chart lines are recomputed in the UI from the published Close series using the locked quant functions. Moving averages are never read from a stored copy, so a drawn line cannot drift from the definition it claims to show.
- When a published artifact is absent, the affected section renders an explicit named notice saying what is missing and how to publish it. It never renders a zero, a placeholder or a flat line.
- Never use an Advanced Chart widget that silently substitutes an unsupported/default symbol.
- Every important number has context: date, unit, period or formula.
- Action is the final decision-support column and is visibly separated from the quantitative evidence.

## Navigation

Seven views, driven by a pill navigation and addressable by query parameter (`?view=Screener&industry=Banks`, `?view=Stock&symbol=TCS`) so every row, chip and industry name is a working link into the relevant view.

1. **Dashboard** — the briefing: regime, stage breadth, Action distribution, leading industries, what changed since the previous completed session, and where names sit today. Briefing and Screener are separate views; the briefing belongs to the Dashboard.
2. **Screener** — the full validated universe as a dense sortable table, with Industry, Stage, RS, setup evidence and Action as the final decision column. Filters for search, Industry, Stage, Action, RS band and liquidity; paginated.
3. **Industries** — ranked industry leadership by median RS, with participation share and median 3-month return. Industry is the NSE constituent field, never remapped.
4. **Market** — participation: regime band, share above the 30-week and 10-week lines, 52-week-high proximity, stage posture, and the participation trend from the published breadth history.
5. **Movers** — day-over-day structural transitions between the current and previous published snapshots, plus the largest RS rank changes. No fabricated daily-change series.
6. **Stock** — company header, Action with its exact reason, price chart with the 10- and 30-week lines, calendar-month returns, 52-week range, trend-health checklist, extension and structural risk, and the complete evidence table.
7. **Methodology** — formulas, source attribution, information boundary and the full nine-label Action framework.

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
