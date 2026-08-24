# RS-Stages — Decision Log

## 2026-08-24 — Initial quantitative lock

1. Use calendar dates for RS lookbacks: 3/6/9/12 calendar months.
2. Use 30-calendar-week **30W MA**, calculated as the simple mean of all valid NSE sessions in the calendar window; not a conventional weighted moving average and not a fixed 150-row approximation.
3. Use calendar dates for the 52-week high.
4. Require at least 200 valid sessions inside the 52-calendar-week window.
5. Production volume baseline: 50 prior observations, `min_periods=50`, then `.shift(1)`.
6. Breakout setup is separate from Breakout Confirmed; confirmation requires U/D > 1.3.
7. Universe/symbols and Industry come directly from the NSE constituent CSV; no F&O filtering and no WealthStar remapping.
8. Use 20 completed sessions for U/D.
9. Use yfinance with `auto_adjust=True`, adjusted Close/High, and raw Volume.
10. Fetch sufficient calendar history; fixed row counts are implementation buffers only.
11. ₹5 crore liquidity rule is an optional UI/screener filter applied after calculations.
12. Remove arbitrary `+1` from U/D denominator and handle zero denominator explicitly.
13. v1 RS Line uses current download window only.
14. **Pre-market information boundary:** decisions are made before the upcoming session opens; all calculations terminate at the latest completed NSE session. The upcoming/incomplete session can never enter a signal.
15. 10-trading-session MA slope is locked as `(MA_today / MA_10_sessions_ago - 1) × 100`.

## 2026-08-24 — Guide v2 supersedes early Action/UI specifications

1. The supplied NSE Signal Interpretation Guide is adopted as the production interpretation/action reference.
2. RS interpretation bands are now 80–99 leadership, 50–79 adequate, and <50 lagging. The former UI thresholds RS 85/70 are retired.
3. Production Action vocabulary is now `BUY★`, `BUY`, `HOLD`, `WAIT`, `WATCH★`, `WATCH`, `REDUCE`, `SELL`, `AVOID`.
4. Stage takes precedence over RS in conflicts: Stage 4 = SELL; Stage 3 = SELL when RS <50 otherwise REDUCE; Stage 1 maps to WATCH★/WATCH/AVOID by RS band.
5. Stage 2 uses the guide's RS bands, distribution warning, >20% extension timing warning, below-50DMA timing warning, breakout and confirmed-breakout states.
6. Extension is operationalized as Close > 1.20 × 30W MA; 50DMA is the 50-session simple moving average of Close.
7. Pullback/volume-drying is not fabricated without a validated quantitative definition.
8. Action logic is implemented in `rs_stages/actions.py`, separated from the quantitative engine.
9. The UI is upgraded to a six-area research platform: Dashboard, Screener, Industries, Movers, Stock, Methodology, with subtle semantic colours and TradingView Lightweight Charts driven by repository data.
10. The Action column is the final decision column in the screener and stock pages expose the underlying evidence and exact Action reason.

Locked decisions may only be changed through a new documented decision/audit item supported by evidence.

## 2026-08-24 — v2.1 decisions

### D-2.1.1 — Snapshot was stale relative to the pipeline

**Problem.** `data/latest_research.csv` predated the commit that added the guide
timing fields to `analyze_universe`. `rs_stages/actions.py` reads
`Extended_20Pct` and `Below_50DMA` with `row.get(field, False)`, so both
evaluated `False` for all 750 stocks and the two WAIT rules in the Stage 2 /
RS ≥ 80 branch could never fire.

**Classification.** Data-quality problem with a decision-layer consequence.

**Measured impact after republishing the snapshot:** of the 137 stocks in that
branch, **111** correctly become WAIT, and **7 of the 8 previous `BUY★` labels
were wrong** — they were extended beyond 20% above the 30-week line or below
their 50-session average. One genuine `BUY★` remained.

**Resolution.** Republished via the Real Data Research Audit workflow. The
snapshot now carries `SMA_50`, `Below_50DMA`, `Extended_20Pct`, `Distribution`
and `Heavy_Distribution`.

**Prevention.** `tests/test_research_artifacts.py` asserts the timing fields are
present in the published snapshot and that Action is reproducible from the
published columns.

### D-2.1.2 — 10-week line: calendar weeks, not 50 sessions

Adopting the reference terminal's shorter trend line required a definition the
locked spec did not have. Two candidates: a 10-calendar-week SMA, or reuse of
the 50-session `SMA_50` already computed for the below-50DMA condition.

**Chosen:** the 10-calendar-week SMA, because it uses the identical construction
to the locked 30-week line and the two are therefore directly comparable. Mixing
a trading-day average with a calendar-week average on one chart would make the
pair meaningless. `SMA_50` is unchanged and still serves its own condition.

`MA_10W` does not reclassify Stage and no locked signal depends on it.

### D-2.1.3 — Calendar MA generalised, proven bit-identical

`ma_30w`/`ma_30w_series` now delegate to a shared calendar-window
implementation, and the series builder resolves window boundaries by position
instead of re-sorting per session. `tests/test_ma_calendar_independent.py`
asserts the fast builder is **bit-identical** (`np.array_equal`) to a
per-session loop over the definition, including on gapped history. Performance
was not permitted to change a numerical result.

### D-2.1.4 — Price panel stores Close only

The panel could have stored the moving averages alongside Close. It does not:
the UI recomputes them for the single symbol it draws, using the locked
functions. A stored average could silently diverge from the definition after a
later spec change; a recomputed one cannot. It also bounds repository growth,
which is the known cost of committing price history on every run.

### D-2.1.5 — Participation derived from Stage when the field is absent

`breadth_snapshot` originally counted a missing `Above_MA_30W` column as zero,
which rendered a live market as "Narrow, 0% above the 30-week line" — a
fabricated reading of exactly the kind section 3 forbids.

`Above_MA_30W` is now read from Stage when the explicit field is absent. This is
not an inference: the locked classification defines Stage 2 and Stage 3 as
exactly `Close > MA_30W`, and Stage 1 and Stage 4 as exactly `Close <= MA_30W`.
Stocks whose Stage could not be classified are excluded from the numerator *and*
the denominator. `Above_MA_10W` has no such identity and is reported as
unavailable rather than derived.

### D-2.1.6 — No Positioning tab

The reference terminal's fifth view is entirely F&O (open interest, basis,
implied volatility, put/call, max pain). The repository has no derivatives data
and locked-spec section 2 forbids F&O filtering. The view is omitted. No
substitute was invented to fill the slot.

### D-2.1.7 — The local sources watcher is disabled in the deployed app

The deployment log carried `KeyError: 'rs_stages'`. Streamlit 1.62's
`LocalSourcesWatcher` responds to a source change by evicting the watched
package and every one of its submodules from `sys.modules`, so the next script
run re-imports them. CPython's `importlib._bootstrap._load` ends with an
unguarded `module = sys.modules.pop(spec.name)`; an eviction landing between the
loader's own `sys.modules[spec.name] = module` and that pop raises `KeyError`
with the bare package name in the importing thread.

This is a race, which is why it surfaced once at boot and the app then served
normally. It was reproduced deterministically rather than reasoned about: a
package evicted while another thread executes its body raises `KeyError` with
that package's name.

`rs_stages` is a PEP 420 namespace package, the case Streamlit's own eviction
comment identifies as leaving orphaned children in `sys.modules`.

The deployed source cannot change while the process is running — a new commit
rebuilds the container — so the watcher has nothing to gain. `fileWatcherType`
is set to `none`, which leaves `_watched_modules` empty, which leaves the
eviction set empty. The race becomes unreachable rather than merely unlikely.

### D-2.1.8 — Charts render through `st.iframe`

Both charts embedded through `st.components.v1.html`, which Streamlit scheduled
for removal after 2026-06-01. The app was one dependency upgrade away from
losing the price chart and the participation trend at the same time, and the
charts are how Stage and participation are read. `st.iframe` is the supported
replacement and takes the same self-contained HTML string, so the vendored
charting library and the dual-axis configuration are unaffected.

### D-2.1.9 — The two publishing workflows are staggered, and neither push can lose a race

Both scheduled workflows commit to `main`: the research audit on weekdays and
the universe refresh on Fridays. Both were set to fire at 18:00 UTC, and the
audit's own schedule comment recorded that as a deliberate match. It was a
defect.

Measured from the run history, the refresh completes in about twenty seconds
and the audit takes about three minutes. On any Friday where the constituent
list changed, the refresh would therefore land first and the audit's `git push`
would be rejected non-fast-forward — at the audit's final step, after it had
already replaced `price_panel.npz` on the `data-latest` release. The published
panel would then sit one session ahead of the committed snapshot, which is
exactly the disagreement `panel_matches` refuses to draw through: the live
terminal would withhold every chart and sparkline until someone re-ran the
audit by hand. A weekly, silent loss of the price history.

Two changes, because the collision and the fragility are separate faults.

The refresh moves to 17:30 UTC. Ordering matters beyond the collision: the
audit checks the repository out when it starts, so a universe published at the
same minute would not reach the audit until the following run, and Friday's
audit would analyse Thursday's constituent list. Landing half an hour ahead
means Friday's audit analyses the universe published that evening.

Both pushes now rebase and retry rather than failing. Staggering removes the
scheduled collision but not an unscheduled one — a commit pushed by hand while
a three-minute audit is running would still discard the run. The audit writes
only the three research CSVs and the refresh writes only the constituent list,
so the two can never rebase into a conflict. Both checkouts move to
`fetch-depth: 0`, since rebasing needs a merge base and the default depth-1
clone has none.

`tests/test_workflow_scheduling.py` pins both properties: the schedules are
ordered with margin and share no fire minute, and every workflow that pushes
does so through a retry with a rebase and enough history to perform it. Each
guard was verified to fail against the configuration it replaced.
