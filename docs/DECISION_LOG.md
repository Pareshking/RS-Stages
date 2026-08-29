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

The two are separated and ordered: the refresh at 17:15 UTC (22:45 IST) and the
audit at 18:15 UTC (23:45 IST). Ordering matters beyond the collision itself:
the audit checks the repository out when it starts, so a universe published at
the same minute would not reach the audit until the following run, and Friday's
audit would analyse Thursday's constituent list. Landing an hour ahead means
Friday's audit analyses the universe published that evening.

The hour is sized against GitHub's scheduler, not against the jobs. Measured
per-step, the constituent CSV downloads in under a second and its whole job
takes 15 seconds, while the audit takes 170 seconds of which 126 are the
750-symbol price fetch. Runtime was never the constraint. `schedule:` is
best-effort and a run can start well behind its cron under load, so the gap
exists to absorb that jitter. The constituent list changes only on index
reconstitution, so moving the refresh earlier in the evening costs nothing in
freshness, which makes the margin close to free.

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

## 2026-08-25 — v2.2 decisions

### D-2.2.1 — A third source authority

The screen implemented two authorities: Weinstein for stage structure and
O'Neil for relative strength and breakout. Minervini is added as a third,
covering the trend template and the volatility contraction pattern.

This is not a cosmetic citation. It introduces 25 fields and changes what the
Coiling screen means, so it carries the same obligation as the first two: every
field traces to a stated definition, and where the source states a number the
number is used rather than a value tuned here.

Attribution was initially missed. Minervini drove 25 published fields while
being cited in no signal card, no methodology section and no stock page — the
two earlier authorities were named throughout. Corrected in `source_line()`,
which now cites him for the trend template and for the contraction setup, each
guarded on the evidence actually being present in the row so the card never
claims a criterion it did not test. Three tests pin this.

### D-2.2.2 — Trend-template thresholds ship flagged as provisional

Seven of the eight trend-template criteria are structural — price above the
150- and 200-session averages, the 150 above the 200, the 200 rising, and so
on — and transfer without interpretation. The remaining two are numeric
tolerances stated for a different market and a different era.

They are implemented at the source's stated values and labelled provisional
wherever they surface, rather than retuned against NSE history here. Retuning
would require a holdout of a size this project does not yet have, and inventing
replacement values would breach the rule against supplying a definition the
source does not give. The flag is the honest position until the history exists.

### D-2.2.3 — Session averages and calendar averages are different constructions

`MA_30W` is built on calendar weeks; `SMA_150` and `SMA_200` are built on
sessions. Thirty calendar weeks is not 150 sessions, and the two must not be
described or computed as though they were interchangeable.

A related defect was found and fixed in both implementations: the session
average was being taken over N-1 observations rather than N. The error was
small in value and structural in effect — it split the deepest and tightest
readings by base length, so short and long bases were being measured on
different definitions. Both the production path and the independent
reconciliation now average over N closes that exist.

### D-2.2.4 — The information boundary skips sessions with no close

The pre-market boundary selected the latest session strictly before the
decision date, including rows carrying no close. Every calendar window then
shifted by one session: `MA_30W` came back missing, `Stage` came back `None`,
and all seventeen reconciled fields disagreed with the independent
implementation.

The boundary now resolves against sessions that actually have a close. The
defect predates v2.2 and was found by the reconciliation, not by the test
suite — a case where the second implementation earned its cost.

### D-2.2.5 — The contraction setup is gated on Stage 2 and bounded on depth

`vcp_setup` tested contraction ratio and volume dry-up alone. Both conditions
are satisfied by a stock declining quietly, which is the opposite of the
pattern: the source describes a base forming after an advance, not a fade on
falling volume. 112 symbols were flagged, of which 33 were in decline.

Two conditions are added. The stock must be in Stage 2, and the base must not
be deeper than 35% peak to trough. Depth is measured across the base itself,
not from the 52-week high — a stock can sit far below a distant high while
building a shallow base, and the two readings answer different questions, so
`Base_Depth_Pct` is computed rather than reusing `Pct_From_52W_High`.

Both parameters are required arguments, not defaults. A default would have let
every existing call site keep the old behaviour silently, which is precisely
the failure being corrected.

### D-2.3.1 — The contraction count is specified but not published

The count of contractions within a base, and the footprint notation that
depends on it, are specified in LOCKED_SPEC §10.5.1 and are not implemented in
the published screen.

Four detector designs were built and measured against two of the source's own
worked examples. All four failed. Base duration, deepest correction and
tightest correction reproduce within tolerance; the count never has. The full
record, including what each attempt got wrong and why, is in §10.5.2.

The elements that validate are adopted — the adaptive base window, the depth
bounds, the pivot, the volume rule. The count is withheld. Publishing a
contraction count that cannot be reproduced against the charts the method's
author read would put a fabricated number behind a citation, which the project
does not permit regardless of how reasonable the number looks.

Two method notes are recorded because they generalise. Three of the four
attempts reached for a threshold where the source was describing a structural
property, and the fourth, which encoded the structure, was the only one that
failed safely. And every attempt passed the full local suite while being wrong:
fixtures written alongside a detector share its assumptions and can only confirm
them. Every real defect here was caught by the external check against real
prices, which is why that check runs in CI rather than being retired now that
the feature is shelved.

### D-2.2.6 — One unavailable symbol must not fail the audit, and an outage must not publish

A manually dispatched run on 25 Aug 2026 aborted with "No completed market
session exists before decision date". Three tickers timed out against the
provider and one returned no rows at all; the empty frame raised out of the
dict comprehension that built the snapshots and killed the whole 750-symbol
audit. Nothing was published, so the failure was loud and safe — but it was
also total, and the cause was a single delisted-looking symbol.

The comprehension is now a loop that records each unavailable symbol with its
reason and continues. That alone would be the wrong fix. `RS_Score` is a
cross-sectional percentile over the symbols actually analysed, so every dropped
symbol shifts the rank of every symbol that survives; a provider outage removing
a large slice of the universe would republish everything with quietly wrong
ranks and nothing in the output would look unusual. Skipping without a bound
converts a loud failure into a silent one, which is the worse trade.

So the skip is bounded. Above 2% of the universe the audit refuses to publish
and says why. The ceiling is an engineering guard, not a quantity from any
source, and is labelled as such at its definition, in the failure message and in
FORMULAS. A delisting or a stray timeout is expected and reported; an outage is
not something to publish through.

Both halves are pinned by tests, and the original failure was reproduced against
the exact comprehension that shipped before verifying the replacement survives
it.

### D-2.2.7 — Five v2.2 formulas were published with wrong numbers

The v2.2 section of FORMULAS.md, written hours earlier, misstated five
quantities. They were written from the locked spec and from memory rather than
read out of `quant.py`, and every one of them passed review here because the
prose was internally coherent.

| Documented | Actually implemented |
| --- | --- |
| `RS_Line_NH_Before_Price`: price below its 52-week high | price **5% or more** below it |
| `Volume_Dryup`: last 10 sessions over the last 50 | last 10 over the **50 preceding** them — disjoint |
| `Base_Depth_Pct`: "across the base" | the trailing **50 sessions** |
| `VCP_Pivot`: high of the final contraction | high of the **whole base** |
| `Stage1_Readiness`: 4 criteria on 0–4 | **5** criteria on **0–5**, four thresholds different |

Two were materially misleading rather than merely imprecise. A reader applying
the documented RS-divergence rule to the 24 Aug 2026 snapshot would expect 25
symbols; the published figure is 0, because all 25 sit within 4.23% of their own
price high and the real rule requires 5%. And `Stage1_Readiness` reached 4 in
that snapshot, which reads as full marks on the documented 0–4 scale and is one
short on the real 0–5 one.

The RS-divergence gap and all five readiness thresholds are ours, not the
source's, and were not labelled as such. They are now, next to the numbers
themselves.

`VCP_Pivot` is a known approximation rather than a mistake: the source puts the
pivot at the top of the final contraction, which needs the detector that failed
validation (§10.5.2). The docs now say so, and note the direction of the error —
where base high and final-contraction high differ the published pivot is too
high, so `Pct_To_Pivot` overstates the distance and is conservative.

`tests/test_docs_match_code.py` pins every documented threshold to the constant
the code uses and asserts the specific wrong forms are absent. Prose can drift
from code silently; a number cannot, once a test holds both ends. The general
lesson is the one already recorded in §10.5.2 from a different direction:
internal consistency is not evidence, and the check has to reach outside the
artefact being checked.

### D-2.3.2 — Attempt 5 asked the right question and still failed

Attempts 1-4 all asked how large a reversal must be to count as a contraction,
and answered with a threshold. Attempt 5 asked instead what event *ends* one:
price must retrace most of the decline before the next can begin, so the
counter-rallies inside a single decline cannot fragment it. That acts on the
segmentation itself rather than filtering its output, which is the flaw attempt
4 could not escape.

It worked, on the part that was ever in doubt. On a synthetic base built with
realistic recoveries and daily noise — the two properties the earlier fixtures
lacked — it reproduced the built count of three at every recovery fraction from
0.70 to 0.90. Stability across the parameter is the evidence that the structural
rule, not the parameter, is carrying the work.

It needs a 3% floor on what counts as a correction to get there. The source's
tightest reported contraction is 2%, and the tightest leg is the one that forms
the pivot, so a 3% floor makes the pivot invisible by construction. At the 1-2%
floors real contractions demand, the count fragments to between five and twelve.
That is attempt 2's wall reached from a new direction. It failed on synthetic
data and was never run against the worked examples.

**A reasoning error worth recording, because it was mine and it was confident.**
The pivot was argued here to be the more tractable half — locating one
contraction being a smaller problem than counting all of them. Smaller in scope,
yes, but the pivot sits at the top of the *final* contraction, which in this
pattern is the *tightest*: nearest the noise floor, where every detector built
here is weakest. The pivot is not the easy part of the count. It is the part
most exposed to the failure mode, and the argument for doing it first had the
difficulty exactly inverted.

Five attempts is enough. The count and the pivot refinement are both closed.
`vcp_pivot` continues to publish the base high, which is never below the final
contraction's high, so `Pct_To_Pivot` overstates the distance and errs toward
caution. A test asserts the recovery detector stays out of the published pivot,
and a second pins the failure so a sixth attempt starts from evidence rather
than from this prose.

### D-2.2.8 — A snapshot's date can split across the universe, and now says so

The header showed one "Validated snapshot" date, computed as the max of a
per-symbol `Date` column. That column is each symbol's own latest completed
session, not a shared clock, and the price provider updates its feed
asynchronously — larger, more liquid names first. The header's max silently
credited every symbol with the newest date present, whether or not that
symbol actually reflected it.

Found by direct request, not by routine checking: asked to manually re-run
the audit and check whether 25 Aug had arrived, the naive check (one row) said
no; the full distribution said 445 of 750 symbols had already moved to 25 Aug
while 305 had not, split cleanly along liquidity — the lagging group's median
20-session traded value was roughly a third of the leading group's. Five
specific lagging symbols (NETWEB, TVSMOTOR, GVT&D, GRASIM, NAVINFLUOR) were
verified by hand against the live provider before concluding this was the
provider's own lag rather than a defect in our fetch.

The fix is disclosure, not enforcement. Waiting for every symbol to agree
before publishing was considered and rejected: one thin, illiquid name could
then delay the other 749 indefinitely, and a stale-but-honest snapshot is
worse than a mostly-current one that says exactly which part is behind.
`Snapshot.date_coverage` computes the split; the header stamp and a Dashboard
card disclose it whenever it is not unanimous, naming every lagging symbol and
the session each is actually on. Each lagging row stays internally consistent
for its own date — nothing is fabricated to paper over the gap — but a
cross-sectional ranking comparing it to a same-day peer is comparing two
different sessions, and the disclosure says so rather than leaving that
inference to the reader.

Tests pin both directions: the disclosure appears exactly when the file on
disk is split, and never appears as a false alarm when it is not — computed
adaptively from whatever `data/latest_research.csv` currently holds, so the
test does not freeze one night's counts.

### D-2.2.9 — The Stock page scored the trend template but never itemized it

Weinstein's trend-health block on the Stock page has always shown its five
conditions individually, each with a pass/fail mark (`TREND_HEALTH_CONDITIONS`
in `screener.py`). The Minervini trend template — added later, in v2.2 —
carried the same eight-criterion structure but was only ever surfaced as one
collapsed number, "N of 8", inside the pivot evidence card. Asked directly
whether the page covered Minervini the way it covered the other two
authorities, checking the actual render found no per-criterion breakdown
anywhere: a stock scoring 4 of 8 gave no way to see which four passed.

`TREND_TEMPLATE_CONDITIONS` is added beside `TREND_HEALTH_CONDITIONS`, same
shape, driving the same `ui.checklist()` renderer the trend-health card
already uses — one code path for both authorities rather than a second,
divergent implementation. The Stock page gains a "Minervini trend-template
checklist" card with all eight items and their marks, placed beside the
existing evidence grid.

Building it surfaced a second, smaller defect in the same area: two footer
notes said "the trend-template thresholds are provisional" without
qualification, which reads as all eight when only TT6, TT7 and TT8 carry a
number invented for this project (the 52-week-low, 52-week-high and RS
cut-offs); TT1 through TT5 are structural comparisons with nothing to verify.
Both notes, on the Stock page and in Methodology, now say "three of the
eight" and name which five carry no invented number. This is the same
class of imprecision as D-2.2.7 — a true statement that overstates what it
covers — caught here before it was recorded as a defect rather than after.

UI_SPEC's Stock page requirements now name both checklists explicitly, so an
authority with a stated criteria list getting a collapsed score instead of an
itemized breakdown is a spec violation rather than something that has to be
noticed by inspection a second time.

Tests: three new tests drive the real Stock page against symbols picked
adaptively from whatever the live snapshot holds — a full pass, a partial
pass, and the footer wording — plus two new screener-level tests pinning the
eight field names and the three-of-eight provisional count.

### D-2.2.10 — Weinstein, O'Neil and Minervini each get their own box

Minervini's trend template had just been given an itemized checklist
(D-2.2.9). Asked whether Weinstein and O'Neil got the same treatment, they
did not: Weinstein's five conditions were already itemized, but O'Neil had no
box and no checklist at all — his evidence (RS leadership, volume
confirmation, U/D, the RS line) was scattered across a flat "Signal card" and
a flat "Every signal against its threshold" table that also carried
Weinstein's Stage and extension figures in the same list. A reader could not
see O'Neil's case for a stock in one place the way Minervini's or Weinstein's
could already be seen.

Checking where the RS-line evidence actually lived surfaced a second,
independent problem: `source_line()` has always attributed
`RS_Line_NH_Before_Price` to O'Neil ("the relative-strength line turning up
before price is the leading tell"), but the card displaying it sat inside the
Minervini v2.2 section. The citation text and the display disagreed with each
other. Reorganizing by author rather than by "when the field was added"
surfaced this on its own; it would not have been caught by inspecting either
side alone.

Three changes.

`signal_card.source_line()` — previously one function building one combined
sentence — is split into `weinstein_line`, `oneil_line` and `minervini_line`,
each returning only that author's fragment. `source_line` becomes their
concatenation, preserving its exact prior output so its five existing tests
needed no changes. A box's conclusion now calls only its own author's
function, which makes citing the wrong authority a type of bug the structure
itself prevents rather than one that has to be caught by review.

`oneil_checklist()` is new: three always-published threshold comparisons
(RS ≥ 80, volume ≥ 1.5×, U/D ≥ 1.3) using the exact constants
`signal_rows()` already applied — no new number is introduced, only a new
itemized presentation of an existing comparison — plus the two RS-line
conditions, included only when their v2.2 columns are actually present so an
older snapshot shows three items rather than five silently-failed ones.

The Stock page now shows three boxes — Weinstein beside the returns/range
card, O'Neil and Minervini below — each an itemized checklist plus that
authority's own conclusion sentence. The flat Signal Card and threshold
table are removed; `wait_note`, `conflict_note` and `caution_note` survive
under "Where the readings interact", since a Stage/RS conflict or a WAIT's
exact gap is a statement about two authorities disagreeing and belongs to
neither box alone. The numeric values the threshold table used to carry
(volume ratio, U/D, 30-week slope, the RS line and its 52-week high) are not
lost — they move into the Calculation-detail grid, in a new "Volume and
momentum" card and two added rows on "Trend structure", so removing the flat
table did not remove the numbers themselves.

Tests: 345 passing, 16 new — signal_card-level tests that each author's line
function names only that author, that `oneil_checklist` grows from three to
five items exactly when the v2.2 columns appear, and that its marks agree
with the same thresholds `signal_rows()` used; app-level tests driven against
the live snapshot confirming all three boxes render, the old flat sections
are gone, the RS-line evidence is no longer inside Minervini's section, the
interaction notes appear only when there is something to say, and a
five-symbol sample renders every box without exception.

### D-2.2.11 — A closing "Bottom line" card, and why it restates rather than recomputes

Asked for an overall conclusion card synthesizing the three author boxes —
described as "basically an action card." Two designs were on the table: a
new combined score (e.g. counting how many of the three authorities agree),
or restating the existing Action label as a closing summary once all three
boxes have been read.

The combined-score design was examined first because it was the one
initially chosen, and rejecting it surfaced something worth recording in its
own right: `action_for()` (`rs_stages/actions.py`) already synthesizes
Weinstein (Stage, as the gate) and O'Neil (RS, U/D, breakout, extension) —
Minervini reads nothing, by the design recorded when v2.2 shipped. A "3 of 3
agree" tally would therefore not be a new reading of the same evidence; it
would need an invented weight for how much Minervini's template or
contraction setup should count, which is exactly the kind of undefined
number this project refuses to introduce. Worse, it would sit on the page
as a second verdict that need not agree with the locked Action — Action
could read WAIT while a naive tally read "2 of 3 bullish" — which
reintroduces the confusion the whole three-box redesign (D-2.2.10) was
built to remove.

Separately, a live report of zero BUY/BUY★ across the entire 750-symbol
universe for two consecutive sessions was investigated in full before any
of this was built, in case the finding was itself evidence of a defect. It
is not. The funnel step-by-step: 410 Stage 2, 143 also RS >= 80, 133 also
clear of distribution, 31 also not extended — the point of collapse — 23
also above the 50-session average, 0 also breaking out today. Every RS>=80
stock currently breaking out is 22-44% above its 30-week line, meaning the
market's strongest performers have already made their move. PTCIL was
BUY* on 21 Aug at 18.2% extension; by 25 Aug, still breaking out with RS
improved 84->87, its extension crossed to 24.0% and Action correctly
flipped to WAIT — the extension gate (locked, predating this session)
working exactly as specified, not a defect.

The closing card restates rather than recomputes. It reuses
`row.get("Action")` and `row.get("Action_Reason")` verbatim, and quotes
`weinstein_line`, `oneil_line` and `minervini_line` — the same three
functions the boxes already call — omitting any authority with nothing to
say. Minervini's line is explicitly labelled context, not a vote. ABB is
the clean illustration on the live snapshot: Trend_Template_Score 8/8,
Action HOLD, both shown side by side without contradiction, because the
card never claims Minervini's evidence decided anything.

Tests: 349 passing, 4 new — the card is checked to reproduce the same
Action already shown at the top, ABB's 8/8-yet-HOLD case is pinned by
name, the "not a vote" wording is asserted present, and all three line
functions are confirmed to return empty strings together on a row with no
classifiable evidence at all.

### D-2.2.12 — The audit moves to the morning after each session

Three consecutive real trading-day transitions (24->25, 25->26, 26->27 Aug
2026) landed the audit one session behind: run at 23:45 IST the same evening,
the price provider still had not posted that day's close, even up to ten
hours after the 15:30 IST NSE close. The information boundary logic was never
wrong — it correctly refused to fabricate a session the provider had not
actually published, stepping back to the last one it had — but a same-evening
run gave the provider too little time to have posted in the first place.

The schedule moves to 01:00 UTC, 6:30 IST the *next* calendar day, roughly
doubling the buffer after close from about 8 hours to about 15. Day-of-week
shifts by one to match: a Monday session is now picked up Tuesday morning
through a Friday session picked up Saturday morning, so Mon-Fri sessions map
to Tue-Sat runs.

This moves the audit off Friday entirely in the old sense — its Friday-morning
slot now catches *Thursday's* close, and it is the *Saturday* run that lands
after the weekly universe refresh (Friday 17:15 UTC) with margin, not a
same-day Friday run. `tests/test_workflow_scheduling.py`'s ordering test is
rewritten to check "the very next audit run after the refresh, wrapping the
week if needed" rather than assuming they share a calendar day, so it states
the actual invariant rather than one specific schedule that happened to
satisfy it.

### D-2.2.13 — A watchdog, and a manual trigger, after the schedule silently skipped a day

Separately from the provider's lag, 27 Aug 2026's scheduled run did not fire
at all — not late, absent. The workflow showed `state: active`, and a manual
`workflow_dispatch` queued and completed normally seconds after being fired,
which rules out anything wrong with the pipeline, the token permissions, or
the workflow file itself. GitHub's own documentation states plainly that
`schedule:` triggers are best-effort and can be dropped outright, not merely
delayed — this is a platform characteristic to build around, not a defect to
root-cause further in this repository's own code.

Two additions, addressing the two different failure classes directly rather
than one mechanism trying to cover both.

`audit_watchdog.yml` runs an hour after the audit's own target time, on the
same days. It lists the audit workflow's recent runs (a read, needing only
the automatic token) and, finding none successful in the last 6 hours,
dispatches the audit itself using a personal access token stored as the
repository secret `WORKFLOW_TRIGGER_PAT` — the automatic `GITHUB_TOKEN`
cannot dispatch another workflow run by design, to prevent an Actions run
from spawning further Actions runs unbounded. If that secret is absent, the
watchdog fails loudly (`::error::`, non-zero exit) rather than silently
concluding there was nothing to do, since a watchdog that quietly no-ops
when unconfigured is worse than no watchdog: it looks like protection that
was never actually wired up.

A "Trigger audit now" control is added to the bottom of the Dashboard view
only, in `rs_stages/ui/dispatch.py`, for the case a human notices staleness
before either automated mechanism does. Two guards, because the site is
public with no login and this fires a real workflow run and a real git push:
the control needs a Streamlit secret (`GITHUB_DISPATCH_TOKEN`) that only the
site's owner can set, and is entirely absent from the Dashboard without it —
never a button that silently does nothing; and it is rate-limited by reading
the audit workflow's own run history from GitHub, not any per-browser or
per-session state, so the limit holds across every visitor combined rather
than being trivially defeated by opening a new browser session.

Both secrets are the same underlying token, stored twice because a GitHub
Actions secret and a Streamlit secret are different stores on different
platforms; README.md's new Operations section gives the exact one-time setup
steps, since generating a credential is a human action neither an agent nor a
workflow can perform on the owner's behalf.

Tests: 366 passing, 17 new — 7 pinning the watchdog's schedule relationship
to the audit and its loud-failure behaviour, 10 driving `dispatch.py`'s
decision logic (configured/unconfigured, cooldown active/clear, network
failure, a rejected token) directly against a mocked `urllib`, with no real
network call and no real token required to verify the logic.

### D-2.2.14 — The watchdog's own freshness check was wrong on its first day

Both new schedules missed their first real day. 28 Aug's audit target
(01:00 UTC) was 117 minutes late with nothing fired — past the ~110-minute
jitter ceiling observed before, a genuine second miss rather than normal
delay. The watchdog (target 02:00 UTC) never fired even once, zero runs
total.

Checking what the watchdog would have concluded even if it had fired
surfaced a real defect in its own logic, independent of whether GitHub's
scheduler cooperates. Its freshness check was `created since 6 hours ago`
— a rolling window. The most recent successful run at that point was a
manual dispatch from 23:05 UTC the evening before, sitting comfortably
inside that 6-hour window at a 02:00 UTC check. The watchdog would have
read that as "an audit succeeded recently" and done nothing, never
noticing that the run it found was yesterday's manual trigger, not
today's scheduled attempt.

The check is now anchored to today's own calendar date at the audit's
target time (`date -u +%Y-%m-%dT01:00:00Z`) rather than a rolling window
measured back from whenever the watchdog happens to run. A run from
before that boundary — however recent — no longer counts, closing the
exact gap a rolling window leaves open by construction.

This is tightly coupled to the audit's own cron hour and minute by
design, and now says so in a comment naming that coupling explicitly, so
a future change to one schedule is a visible prompt to check the other
rather than a silent divergence.

Tests: 367 passing, 1 new, asserting both that the literal "hours ago"
pattern is absent and that the anchor time is read from the audit
workflow's own cron rather than hardcoded a second time.

### D-2.2.14 — The audit moves to 02:30 UTC, and starts measuring whether that helped

D-2.2.12 moved the audit from the same evening to the next morning because
the provider had not posted the day's close by 23:45 IST. It fixed the
symptom it was aimed at — the run no longer falls back a whole session for
the entire universe — but it did not fix the underlying condition, and
nothing was measuring whether it had.

The 29 Aug 2026 snapshot, published by a 01:00 UTC / 06:30 IST run, carried
261 of 750 stocks on the latest session and 489 on the one before it. Two
thirds of the universe was a session behind. That matters more than a
staleness inconvenience: RS_Score is a cross-sectional percentile, so a
split universe means the ranking every Stage, breakout test and Action label
depends on is comparing two different trading sessions against each other.
The lagging group's median 20-session traded value was ₹44.8 Cr against
₹93.4 Cr for the current group, so the split follows liquidity — the same
gradient the loader's own docstring predicted.

The audit now fires at 02:30 UTC (08:00 IST) and the watchdog at 03:10 UTC,
keeping the 40-minute gap the watchdog tests require. The run takes about
three minutes and the NSE opens at 09:15 IST / 03:45 UTC, so publication
still lands around 08:20 IST with an hour of margin: the decision remains
pre-market for the upcoming session, which is the invariant that actually
constrains this schedule.

Ninety minutes is a guess about a third party's publishing curve, and this
is now the second schedule move made on such a guess. So the more important
half of this decision is that guessing stops here: `record_freshness()`
appends every run's split to `data/freshness_history.csv` and emits a
`::warning::` annotation when the lagging share exceeds
`MAX_LAGGING_SHARE_PCT` (15%). A third move will be argued from the recorded
curve.

Deliberately a warning and not a failure. Refusing to publish a split
snapshot would leave the site serving an *older* snapshot carrying the same
split, which is strictly worse, and the split is already disclosed on every
page. Recording is likewise non-fatal in both directions: it runs after the
artifacts are written and before the workflow commits them, so an unreadable
or unwritable history file prints a line and changes nothing else. A history
whose columns are not this file's columns starts a new one rather than
concatenating — a CSV parser returns a frame for plenty of files that are
not this file.

Tests: 387 passing, 8 new, covering the reported split, the warning
threshold in both directions, accumulation across runs, and that neither a
malformed nor an unwritable history can cost a run its snapshot.

### D-2.2.15 — Eight peer views collapse into four, and Action moves off the right edge

The site presented eight sections as equals in a pill bar: Dashboard, Setups,
Screener, Industries, Market, Movers, Stock, Methodology. Each was coherent on
its own. Together they asked a reader arriving before the open to know which
of five questions they had before the site would answer any of them, which is
why the material read as a filing cabinet rather than a decision surface.

They are now four, ordered by distance from acting rather than by subject.
**Today** absorbs Dashboard, Market and Movers — they were one question asked
at three levels of detail. **Find** absorbs Screener, Setups and Industries —
they were one table with different predicates and column sets, and keeping
them apart meant a filter built in one had to be rebuilt in the next.
**Stock** and **Method** stand.

Every retired name remains a valid `?view=` value and resolves to the section
carrying its content, with a test asserting each one lands where intended
rather than on the home page by accident. A silent fallback would have been
indistinguishable from a working link.

The largest addition is not structural. Every count the briefing carried was
already there; not one of them named a stock. Answering "what does the guide
say to do today" took a second navigation and two filters. Today now opens on
the names themselves — the entries the guide allows, the exits it requires,
the bases it is watching — with a link into Find carrying the Action labels as
repeated query parameters, so the link lands on the filtered list it promises.

**Action moves from the last column to the second.** UI_SPEC required it last
so the table read as evidence → decision. That reasoning holds on a wide
screen and fails outright on a narrow one: at 390px every column past the
third sits off the right edge behind a horizontal scroll inside a vertically
scrolling page, with no shadow, gradient or arrow suggesting it is there. The
one column the nine-label framework exists to produce was the column a phone
reader never saw. The reading order is now decision → evidence, matching the
Stock page since its own restructure; the requirement the rule protected —
Action visibly separated from the evidence, never replacing or hiding it —
is unchanged.

Retired with it: `app_v2.py` through `app_v6.py`, five superseded prototypes
and the source of the `var(--line)` token that `components.py` still
referenced and no stylesheet defined, so the evidence meters had been drawing
their filled slots with nothing behind them. The Signal Card's threshold table
— built, tested, and rendered by nothing — is now the Stock page's
value-against-threshold block, which is the one place the page put a value
beside the rule it has to clear.

Tests: 392 passing, 25 new, covering the legacy `?view=` aliases, the
decision-card links arriving as an applied filter, the treemap's area
conservation and its label contrast, and the freshness record.
