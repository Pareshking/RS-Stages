# RS-Stages

RS-Stages is a Streamlit-based quantitative research platform for Relative Strength and market-stage analysis.

## Engineering Standard

This is not a black-box screener. The project is developed under the full **Strict Loop Engineering Prompt** stored in `MEMORY.md`.

Core loop:

**INSPECT → UNDERSTAND → FORMULATE → IMPLEMENT → TEST → VALIDATE → AUDIT → FIX → RE-TEST → VERIFY → DOCUMENT → REPEAT**

Correctness takes precedence over speed, presentation, and backtest performance.

## Source of Truth

- `MEMORY.md` — complete persistent engineering prompt and project memory.
- `docs/LOCKED_SPEC.md` — authoritative locked quantitative inputs.
- `docs/FORMULAS.md` — explicit mathematical formulations.
- `docs/DATA_SPEC.md` — data acquisition and integrity requirements.
- `docs/VALIDATION_PROTOCOL.md` — validation and testing protocol.
- `docs/DECISION_LOG.md` — project decisions.
- `docs/AUDIT_LOG.md` — audit findings and resolutions.

## Current Quantitative Foundation

The pure calculation layer is in `rs_stages/quant.py` and tests are in `tests/test_quant.py`.

Locked methodology includes calendar-date RS lookbacks, a 30-calendar-week MA, a 10-calendar-week MA, a 10-session MA slope, a 52-calendar-week high and low each requiring at least 200 valid sessions, a prior-50-session shifted volume baseline, and a 20-session Up/Down volume ratio.

## Architecture

| Layer | Module | Responsibility |
| --- | --- | --- |
| Calculation | `rs_stages/quant.py` | Pure locked primitives. No IO. |
| Acquisition | `rs_stages/data.py`, `rs_stages/pipeline.py` | Provider access and the pre-market information boundary. |
| Universe | `rs_stages/screener.py` | Per-symbol locked fields and the trend series. |
| Interpretation | `rs_stages/actions.py` | The nine-label guide Action mapping. |
| Aggregation | `rs_stages/market.py`, `rs_stages/movers.py` | Breadth counts and day-over-day set differences. |
| Presentation | `rs_stages/ui/`, `app_v7.py` | Design tokens, HTML components and the seven views. Reads published artifacts only. |
| Audit | `scripts/real_data_audit.py` | Independent reconciliation, then publishes the artifacts. |

## Published Artifacts

The Real Data Research Audit workflow publishes `data/latest_research.csv`,
`data/previous_research.csv` and `data/breadth_history.csv` to the repository,
and `price_panel.npz` as a rolling **release asset** on the `data-latest` tag.

The panel is not committed on purpose: it is a regenerated binary that Git
cannot delta, so committing it would add ~1.4 MB of permanent history per run.
Replacing a single release asset keeps exactly one copy and adds nothing to the
repository. The UI reads these artifacts and nothing else; when one is absent
the affected section says so explicitly rather than showing a substitute
value.

All signals respect the pre-market information boundary: the latest completed NSE session is the terminal information date for the upcoming decision session.

## Operations

### Schedule

| Workflow | Fires | Purpose |
| --- | --- | --- |
| `real_data_audit.yml` | 01:17 UTC / 6:47 IST, Tue-Sat | The morning after each Mon-Fri session. The non-zero minute avoids GitHub's documented top-of-hour scheduler load; workflow-file changes also trigger one controlled recovery run. |
| `audit_watchdog.yml` | 02:17 UTC / 7:47 IST, Tue-Sat | Checks the actual `price_panel.npz` release asset freshness and dispatches the audit with `GITHUB_TOKEN` when stale. It no longer depends on a PAT secret. |
| `update_nse_universe.yml` | 17:15 UTC, Fri | The constituent list. Lands well ahead of the next audit run (Saturday morning), never on the same calendar day. |

### One-time setup: Streamlit dispatch secret

The Dashboard's optional "Trigger audit now" control uses the Streamlit secret
`GITHUB_DISPATCH_TOKEN`. The deployed app needs that secret to show the control;
the public dashboard otherwise remains unchanged.

The automated watchdog no longer needs `WORKFLOW_TRIGGER_PAT`. GitHub permits a
workflow using `GITHUB_TOKEN` to create a `workflow_dispatch` run, so the
watchdog now uses the repository token directly for both freshness checks and
retriggering.

The button's rate limit (one trigger per `dispatch.COOLDOWN_MINUTES`, 20 by
default) is checked against the audit workflow's own run history on GitHub,
not against anything stored per-browser — it holds across every visitor at
once, since the site is public with no login.

### Provider ticker aliases

The NSE universe remains authoritative. Provider-specific ticker differences are
kept as explicit acquisition aliases. In particular, NSE currently identifies
HEG Advanced Materials as `HEGAM`, while Yahoo still serves its NSE history as
`HEG.NS`; the acquisition layer maps Yahoo's `HEG.NS` response back to the
analytical `HEGAM` symbol. The universe is not renamed or silently substituted.

## Validation Status

GitHub Actions CI is configured to execute the test suite. A test suite is only considered passed when actual CI execution evidence is available.

No quantitative milestone is declared complete merely because code runs or outputs appear plausible.
