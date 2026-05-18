# Phase 8.5 — Stats Visualisation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans`. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** For every test the Statistics module already runs, render an appropriate auxiliary chart server-side as PNG (matplotlib 'Agg' + seaborn), store base64 in the existing nullable `AnalysisResult.chart` JSON column, and surface it in `AnalysisResultCard` with click-to-zoom and a download link.

**Architecture:**
- New service subtree `services/stats/charts/` with five pure-function modules, one per visual archetype.
- One dispatch helper in `services/stats/runner.py` that maps `test_key → chart function` and is called immediately after the `TestResult` is built (or in the route after `runner.run`, see Task 2). Failures to render are logged and stored as `None` — the analysis numerics path is unchanged.
- **No new tables, no migration, no new pip deps.** `AnalysisResult.chart` already exists (`db/models.py` L252, JSON nullable). `TestResult.chart` already exists (`runner.py` L27). matplotlib + seaborn are already pulled by pingouin from Phase 6.
- **No backwards-incompatibility risk** for the 488+ existing stats route tests — they assert on `summary`, not `chart`. The new field is additive.
- Frontend: `AnalysisResultCard.tsx` renders the existing-but-unused `chart` field. One new helper component `ChartImage.tsx` (image + zoom modal + download). Zod `AnalysisResultSchema.chart` is already `z.record(z.string(), z.any()).nullable()` — no schema change.

**Tech Stack additions:** none.

---

## File Structure

```
apps/api/
├── src/research_api/
│   ├── services/stats/
│   │   ├── charts/
│   │   │   ├── __init__.py                          (NEW — dispatcher)
│   │   │   ├── _base.py                             (NEW — backend init + fig helpers)
│   │   │   ├── box_plot.py                          (NEW)
│   │   │   ├── histogram.py                         (NEW)
│   │   │   ├── qq_plot.py                           (NEW)
│   │   │   ├── scatter_plot.py                      (NEW)
│   │   │   └── km_curve.py                          (NEW)
│   │   └── runner.py                                (modify: wire chart dispatch into 19 handlers)
│   └── routes/analyses.py                           (no changes — already passes result_obj.chart through)
└── tests/
    ├── test_stats_chart_box_plot.py                 (NEW)
    ├── test_stats_chart_histogram.py                (NEW)
    ├── test_stats_chart_qq_plot.py                  (NEW)
    ├── test_stats_chart_scatter_plot.py             (NEW)
    ├── test_stats_chart_km_curve.py                 (NEW)
    ├── test_stats_chart_dispatch.py                 (NEW — runner integration: every test_key produces a chart or None safely)
    └── test_stats_chart_resilience.py               (NEW — failure paths)

apps/web/
├── src/
│   ├── components/statistics/
│   │   ├── AnalysisResultCard.tsx                   (modify: render chart + zoom + download)
│   │   ├── ChartImage.tsx                           (NEW — img + zoom modal + download link)
│   │   └── __tests__/AnalysisResultCard.test.tsx    (modify: assert chart renders when present)
│   └── (no api.ts changes — schema already supports chart)
```

---

## Pre-flight

- [ ] **Step 1: Verify Phase 8 tag is current**: `git tag --list | grep phase-8` → should show.
- [ ] **Step 2: Branch (optional)**: `git checkout -b phase-8p5`.
- [ ] **Step 3: Confirm baseline**: `cd apps/api && python -m pytest -q` (656 green), `cd apps/web && npm run typecheck && npm test -- --run && npm run build` (71 vitest green).
- [ ] **Step 4: Confirm matplotlib 'Agg' import path is clean**: `python -c "import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt; import seaborn as sns; print(plt.get_backend())"` → `Agg`.
- [ ] **Step 5: Confirm `AnalysisResult.chart` is nullable JSON** by reading `db/models.py` and confirming the migration is already applied (it is — landed in Phase 6 alembic `0006_statistics.py`).

---

## Task 1: `_base.py` — backend init + PNG/data-uri helpers (TDD)

**Files:**
- Create: `apps/api/src/research_api/services/stats/charts/__init__.py`
- Create: `apps/api/src/research_api/services/stats/charts/_base.py`
- Create: `apps/api/tests/test_stats_chart_base.py`

```python
# _base.py
from __future__ import annotations
import base64
from io import BytesIO
from contextlib import contextmanager

import matplotlib
matplotlib.use("Agg")  # MUST come before any pyplot import.
import matplotlib.pyplot as plt
import seaborn as sns

_DPI = 130
_FIGSIZE = (6.5, 4.0)

sns.set_theme(style="whitegrid", context="notebook")


@contextmanager
def fig_context(figsize=_FIGSIZE):
    fig = plt.figure(figsize=figsize, dpi=_DPI)
    try:
        yield fig
    finally:
        plt.close(fig)


def fig_to_png_bytes(fig) -> bytes:
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=_DPI, bbox_inches="tight")
    buf.seek(0)
    return buf.read()


def fig_to_data_uri(fig) -> dict:
    raw = fig_to_png_bytes(fig)
    return {
        "format": "png",
        "data_uri": "data:image/png;base64," + base64.b64encode(raw).decode("ascii"),
        "byte_size": len(raw),
    }
```

**Tests:**
- `test_fig_context_closes_figure_on_exit` (assert `plt.get_fignums()` is `[]` after a `with fig_context(): pass`).
- `test_fig_to_png_bytes_starts_with_png_magic` (assert `out[:8] == b"\x89PNG\r\n\x1a\n"`).
- `test_fig_to_data_uri_returns_expected_shape` (keys: `format`, `data_uri`, `byte_size`; `data_uri.startswith("data:image/png;base64,")`).
- `test_fig_context_closes_even_on_exception` (raise inside the `with`; assert `plt.get_fignums()` is `[]`).
- `test_repeated_calls_no_state_leak` (10 iterations).

`charts/__init__.py` exposes:

```python
from .box_plot import render_box_plot
from .histogram import render_histogram
from .qq_plot import render_qq_plot
from .scatter_plot import render_scatter_plot
from .km_curve import render_km_curve

__all__ = [
    "render_box_plot", "render_histogram", "render_qq_plot",
    "render_scatter_plot", "render_km_curve",
    "select_and_render",
]

def select_and_render(*, test_key: str, df, variables) -> dict | None:
    """Map test_key to the appropriate chart renderer. Returns the dict shape stored
    in AnalysisResult.chart, or None when no chart applies or rendering fails."""
    ...
```

`select_and_render` (the dispatcher — fully unit-tested in Task 7 below) wraps every call in `try/except` and logs at WARNING on any exception, returning `None`.

- [ ] **Step 1:** Tests. **Step 2:** Implement `_base.py` + `__init__.py` skeleton. **Step 3:** Commit.

---

## Task 2: `box_plot.py` — group-comparison tests (TDD)

**Files:**
- Create: `apps/api/src/research_api/services/stats/charts/box_plot.py`
- Create: `apps/api/tests/test_stats_chart_box_plot.py`

Public API:

```python
def render_box_plot(*, df, outcome: str, groups: str, title: str | None = None) -> dict:
    """Seaborn box+strip plot. One box per group on the categorical axis,
    outcome on the numeric axis. Returns the {format, data_uri, byte_size} dict."""
```

Behaviour:
- Drop NaN on `[outcome, groups]`.
- Sort group labels for a stable axis order.
- Box plot underneath, strip plot (jittered points) overlaid with low alpha.
- Axis labels = column names.
- Y label = `outcome`. X label = `groups`.
- `title` parameter is XML-escaped via `html.escape` before being set (defence-in-depth even though matplotlib doesn't render HTML).

Applies to test keys: `independent_t`, `paired_t` (treat `pre`/`post` as two pseudo-groups long-form), `mann_whitney`, `wilcoxon_signed`, `one_way_anova`, `kruskal_wallis`. For `rm_anova`, plot one box per timepoint (long-form melt).

**Tests:**
- `test_box_plot_returns_data_uri_shape`.
- `test_box_plot_png_magic_bytes` (decode the base64; assert PNG header).
- `test_box_plot_handles_two_groups`.
- `test_box_plot_handles_more_than_two_groups` (k=4).
- `test_box_plot_dropna_does_not_crash_on_partial_nan_column`.
- `test_box_plot_raises_value_error_on_all_nan_group` (caller will catch and store None).
- `test_box_plot_no_matplotlib_state_leak`.

- [ ] **Step 1:** Tests. **Step 2:** Implement. **Step 3:** Commit.

---

## Task 3: `histogram.py` — single-variable distribution (TDD)

**Files:**
- Create: `apps/api/src/research_api/services/stats/charts/histogram.py`
- Create: `apps/api/tests/test_stats_chart_histogram.py`

Public API:

```python
def render_histogram(*, df, column: str, bins: int | str = "auto", kde: bool = True) -> dict:
    """Seaborn histplot with optional KDE overlay."""
```

Applies to: as a *companion* to QQ plot for normality-relevant tests, and standalone for `chi_squared` / `fisher_exact` when we render an observed-vs-expected bar chart (Task 3.5 — fold into histogram module by re-exposing `render_categorical_counts`). For v1, also use it as the secondary chart for `paired_t`/`wilcoxon_signed` on the difference `post - pre`.

**Tests:**
- `test_histogram_returns_data_uri_shape`.
- `test_histogram_png_magic_bytes`.
- `test_histogram_handles_integer_column`.
- `test_histogram_kde_false_omits_kde_line`.
- `test_histogram_dropna`.

**Additional helper for chi²/Fisher:**

```python
def render_categorical_counts(*, df, var_a: str, var_b: str) -> dict:
    """Side-by-side bars: counts of var_a across levels of var_b. Stacked legend."""
```

**Tests** (same file):
- `test_categorical_counts_renders_2x2`.
- `test_categorical_counts_renders_3x3`.

- [ ] **Step 1:** Tests. **Step 2:** Implement both functions. **Step 3:** Commit.

---

## Task 4: `qq_plot.py` — normality diagnostic (TDD)

**Files:**
- Create: `apps/api/src/research_api/services/stats/charts/qq_plot.py`
- Create: `apps/api/tests/test_stats_chart_qq_plot.py`

Public API:

```python
def render_qq_plot(*, df, column: str, title_suffix: str | None = None) -> dict:
    """scipy.stats.probplot against the normal distribution. Plots theoretical
    quantiles (x) vs sample quantiles (y) with the OLS fit line drawn through."""
```

`scipy.stats.probplot(values, dist="norm", plot=ax)` does the work. We draw the reference line ourselves (probplot draws one already) but override colour for theme consistency.

Applies to test keys: `independent_t`, `paired_t`, `one_way_anova`, `pearson`, `linear_regression`, `multiple_linear` (residuals — see Task 5; QQ plot for the residual vector). For tests whose residuals only make sense after fit, dispatch in Task 7 picks `scatter_plot` for the main plot and adds QQ via a future `secondary_chart` slot — out of scope for v1 (we render only the primary chart).

**Tests:**
- `test_qq_plot_returns_data_uri_shape`.
- `test_qq_plot_png_magic_bytes`.
- `test_qq_plot_with_normal_data_line_runs_through_points` (statistical, soft assertion — assert R² of probplot return ≥ 0.95 for a `numpy.random.default_rng(42).normal(size=200)` sample).
- `test_qq_plot_with_skewed_data_still_renders`.
- `test_qq_plot_dropna`.

- [ ] **Step 1:** Tests. **Step 2:** Implement. **Step 3:** Commit.

---

## Task 5: `scatter_plot.py` — regression visualisations (TDD)

**Files:**
- Create: `apps/api/src/research_api/services/stats/charts/scatter_plot.py`
- Create: `apps/api/tests/test_stats_chart_scatter_plot.py`

Public API:

```python
def render_scatter_plot(
    *,
    df,
    x: str,
    y: str,
    fit: str = "linear",       # 'linear' | 'lowess' | 'none'
    ci: int | None = 95,        # CI band percentage; None to hide
) -> dict:
    """Seaborn regplot: scatter + fit line + bootstrap CI band."""
```

Applies to: `pearson`, `spearman` (set `fit='lowess'`), `linear_regression`. For `multiple_linear` and `logistic`, render a *partial regression plot* — for v1 we substitute a scatter of the **first** predictor vs outcome with a fit line and a footnote captioned "first predictor shown; multi-predictor model summary in the numbers above". Tracked in DEFERRED.md as a Phase 9 nicety.

**Tests:**
- `test_scatter_returns_data_uri_shape`.
- `test_scatter_png_magic_bytes`.
- `test_scatter_lowess_smooth_renders`.
- `test_scatter_no_ci_when_ci_none`.
- `test_scatter_handles_constant_predictor` (`x.var() == 0` → regplot raises; we catch + draw scatter without fit line).

- [ ] **Step 1:** Tests. **Step 2:** Implement. **Step 3:** Commit.

---

## Task 6: `km_curve.py` — Kaplan-Meier survival (TDD)

**Files:**
- Create: `apps/api/src/research_api/services/stats/charts/km_curve.py`
- Create: `apps/api/tests/test_stats_chart_km_curve.py`

Public API:

```python
def render_km_curve(
    *,
    df,
    duration: str,
    event: str,
    groups: str | None = None,
) -> dict:
    """Kaplan-Meier survival curves via lifelines. One line per group level (or one line
    overall when groups is None). At-risk table rendered below the main axes."""
```

Uses `lifelines.KaplanMeierFitter` (already a Phase 6 dependency). Layout: main axes top 3/4, at-risk numbers in a manual bottom band — for v1, render the at-risk counts as a small subplot via `lifelines.plotting.add_at_risk_counts` (lifelines built-in).

Applies to: `kaplan_meier`, `cox_ph` (for `cox_ph`, plot the un-adjusted KM split by the first categorical covariate; caption notes that the hazard ratio comes from the adjusted Cox model).

**Tests:**
- `test_km_curve_overall_renders` (no groups).
- `test_km_curve_two_groups_renders`.
- `test_km_curve_handles_no_events` (everyone censored).
- `test_km_curve_handles_all_events`.
- `test_km_curve_at_risk_band_included` (after rendering, the figure has ≥2 axes).
- `test_km_curve_dropna_on_duration_or_event`.

- [ ] **Step 1:** Tests. **Step 2:** Implement. **Step 3:** Commit.

---

## Task 7: Dispatch in `runner.py` — wire chart selection into every handler (TDD)

**Files:**
- Modify: `apps/api/src/research_api/services/stats/runner.py`
- Create: `apps/api/tests/test_stats_chart_dispatch.py`

Strategy: rather than touch every `_independent_t` / `_paired_t` / ... handler in `runner.py`, add a **single dispatch step in `run(...)`** that, after `handler(df, variables)` returns its `TestResult`, calls `select_and_render(test_key=test_key, df=df, variables=variables)` and **rebuilds** `TestResult` with the `chart` field populated. Since `TestResult` is `frozen=True`, use `dataclasses.replace(result_obj, chart=chart_dict)`.

```python
# runner.py — change inside `run`:
def run(*, test_key, df, variables) -> TestResult:
    ...
    handler = _DISPATCH[test_key]
    result = handler(df, variables)
    chart = select_and_render(test_key=test_key, df=df, variables=variables)
    if chart is not None:
        result = replace(result, chart=chart)
    return result
```

`select_and_render` mapping (in `services/stats/charts/__init__.py`):

```python
_CHART_BY_TEST: dict[str, Callable[..., dict]] = {
    "independent_t":  lambda df, v: render_box_plot(df=df, outcome=v["outcome"], groups=v["groups"]),
    "paired_t":       lambda df, v: render_histogram(df=_pre_post_diff_long(df, v["pre"], v["post"]), column="diff", kde=True),
    "mann_whitney":   lambda df, v: render_box_plot(df=df, outcome=v["outcome"], groups=v["groups"]),
    "wilcoxon_signed":lambda df, v: render_histogram(df=_pre_post_diff_long(df, v["pre"], v["post"]), column="diff", kde=True),
    "chi_squared":    lambda df, v: render_categorical_counts(df=df, var_a=v["var_a"], var_b=v["var_b"]),
    "fisher_exact":   lambda df, v: render_categorical_counts(df=df, var_a=v["var_a"], var_b=v["var_b"]),
    "one_way_anova":  lambda df, v: render_box_plot(df=df, outcome=v["outcome"], groups=v["groups"]),
    "kruskal_wallis": lambda df, v: render_box_plot(df=df, outcome=v["outcome"], groups=v["groups"]),
    "rm_anova":       lambda df, v: render_box_plot(df=_long_form_rm(df, v["subject"], v["within"], v["outcome"]),
                                                    outcome="value", groups="time"),
    "pearson":        lambda df, v: render_scatter_plot(df=df, x=v["x"], y=v["y"], fit="linear"),
    "spearman":       lambda df, v: render_scatter_plot(df=df, x=v["x"], y=v["y"], fit="lowess"),
    "linear_regression": lambda df, v: render_scatter_plot(
        df=df, x=v["predictors"][0] if isinstance(v.get("predictors"), list) else v["predictor"],
        y=v["outcome"], fit="linear"),
    "multiple_linear":  lambda df, v: render_scatter_plot(df=df, x=v["predictors"][0], y=v["outcome"], fit="linear"),
    "logistic":         lambda df, v: render_scatter_plot(df=df, x=v["predictors"][0], y=v["outcome"], fit="linear"),
    "kaplan_meier":     lambda df, v: render_km_curve(df=df, duration=v["duration"], event=v["event"], groups=v.get("groups")),
    "cox_ph":           lambda df, v: render_km_curve(df=df, duration=v["duration"], event=v["event"], groups=v.get("covariates", [None])[0]),
    # icc + cohen_kappa: no chart in v1 (return None — small categorical agreement tables work poorly as plots).
    "icc": None,
    "cohen_kappa": None,
}

def select_and_render(*, test_key, df, variables) -> dict | None:
    spec = _CHART_BY_TEST.get(test_key)
    if spec is None:
        return None
    try:
        return spec(df, variables)
    except Exception as exc:
        log.warning("Chart render failed for %s: %s", test_key, exc)
        return None
```

`_pre_post_diff_long(df, pre, post)` and `_long_form_rm(df, subject, within, outcome)` are tiny helpers near the dispatcher; pure pandas transforms; unit-tested in the same file.

**Tests (`test_stats_chart_dispatch.py`):**
- Parametrised over every `test_key` in `_DISPATCH`: assert that running a minimal valid frame through `runner.run(test_key=k, df=df, variables=v)` yields either:
  - `result.chart is None` (for `icc`, `cohen_kappa`), or
  - `result.chart` is a `dict` with keys `format`, `data_uri`, `byte_size` and `data_uri.startswith("data:image/png;base64,")`.
- `test_chart_dispatch_does_not_break_numerics` — for each test_key, assert `result.statistic` and `result.p_value` match the pre-chart-dispatch reference values (rerun a handler directly + compare).
- `test_chart_dispatch_failure_returns_none_not_raise` (monkeypatch a renderer to raise; assert `result.chart is None` and `result.statistic` is still set).
- `test_chart_dispatch_logs_warning_on_failure` (use `caplog.at_level("WARNING")`).
- `test_pre_post_diff_long_helper` (small fixture).
- `test_long_form_rm_helper` (small fixture).

- [ ] **Step 1:** Tests. **Step 2:** Implement helpers + dispatcher + the single `replace(...)` line in `run`. **Step 3:** Confirm `cd apps/api && pytest -q tests/test_stats_*` is green (the 488+ existing stats tests must stay green — `chart` is purely additive). **Step 4:** Commit.

---

## Task 8: Resilience tests (TDD)

**Files:**
- Create: `apps/api/tests/test_stats_chart_resilience.py`

Tests:
- `test_chart_is_none_when_outcome_all_nan_for_one_group`.
- `test_chart_is_none_when_dataframe_empty_after_dropna`.
- `test_chart_is_none_when_groups_column_has_single_level` (box plot needs ≥2 groups; renderer raises; dispatcher returns None).
- `test_chart_is_none_when_predictor_is_constant` (scatter regression).
- `test_chart_population_survives_chart_failure` — `runner.run` returns a `TestResult` with valid numerics and `chart=None` when the chart pipeline crashes.
- `test_analysis_route_persists_chart_to_db` (end-to-end via the FastAPI test client: post to `/analyses/{id}/run` for an `independent_t` over a seeded dataset; load the resulting `AnalysisResult`; assert `result.chart["format"] == "png"` and the data URI is base64-decodable).
- `test_analysis_route_persists_chart_null_when_render_fails` (monkeypatch the dispatcher to raise; assert `result.chart is None` in DB; assert HTTP 200 with the numerics intact).

- [ ] **Step 1:** Tests. **Step 2:** Confirm green. **Step 3:** Commit.

---

## Task 9: Frontend — `ChartImage.tsx` (TDD)

**Files:**
- Create: `apps/web/src/components/statistics/ChartImage.tsx`
- Create: `apps/web/src/components/statistics/__tests__/ChartImage.test.tsx`

```tsx
type ChartImageProps = {
  chart: { format: 'png'; data_uri: string; byte_size: number } | null
  alt: string
  downloadName?: string
}

export function ChartImage({ chart, alt, downloadName }: ChartImageProps) {
  const [open, setOpen] = useState(false)
  if (!chart) return null
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="block group rounded-md overflow-hidden border border-border bg-white"
        aria-label={`View ${alt} full size`}
      >
        <img
          src={chart.data_uri}
          alt={alt}
          className="w-full h-auto group-hover:opacity-95 transition-opacity"
          loading="lazy"
        />
      </button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle>{alt}</DialogTitle>
          </DialogHeader>
          <img src={chart.data_uri} alt={alt} className="w-full h-auto" />
          <DialogFooter>
            <a
              href={chart.data_uri}
              download={`${downloadName ?? 'chart'}.png`}
              className="inline-flex items-center gap-2 text-[13px] underline-offset-2 hover:underline"
            >
              <Download className="h-3.5 w-3.5"/> Download PNG
            </a>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
```

**Vitest:**
- `test_renders_nothing_when_chart_is_null`.
- `test_renders_thumbnail_when_chart_present`.
- `test_opens_zoom_modal_on_click` (RTL + `userEvent.click`).
- `test_download_link_uses_data_uri_as_href`.

- [ ] **Step 1:** Tests. **Step 2:** Implement. **Step 3:** Commit.

---

## Task 10: Wire `ChartImage` into `AnalysisResultCard.tsx`

**File:** modify `apps/web/src/components/statistics/AnalysisResultCard.tsx`.

Insert below the numeric summary block, above the `<AssumptionPills>`:

```tsx
{result?.chart && (
  <ChartImage
    chart={result.chart as { format: 'png'; data_uri: string; byte_size: number }}
    alt={`${TEST_LABELS[analysis.chosen_test]} chart`}
    downloadName={`analysis-${analysis.id}-chart`}
  />
)}
```

Update `apps/web/src/components/statistics/__tests__/AnalysisResultCard.test.tsx` (if exists; otherwise create a small one):
- `test_chart_renders_when_result_has_chart`.
- `test_no_chart_node_when_chart_null`.

- [ ] **Step 1:** Modify card + tests. **Step 2:** `npm run typecheck && npm test -- --run`. **Step 3:** Commit.

---

## Task 11: E2E browser smoke (chrome-devtools-mcp)

- [ ] **Step 1:** Boot servers.
- [ ] **Step 2:** Drive Chrome via MCP:
  1. Open `/statistics` against a project with a seeded numeric dataset.
  2. Run an `independent_t` analysis. Confirm the result card now shows a box plot thumbnail beneath the p-value.
  3. Click the thumbnail → assert the zoom modal opens with the same image at full width.
  4. Click "Download PNG" → confirm the browser save dialog appears.
  5. Repeat for a `pearson` analysis → confirm scatter+fit line image.
  6. Repeat for a `kaplan_meier` analysis (use the Phase 6 KM seed dataset) → confirm KM curve + at-risk band.
  7. Disable network mid-render via DevTools to simulate failure (or load a dataset where one group is all-NaN); confirm the route still returns 200 with numerics, no `chart` node renders, no UI errors.
- [ ] **Step 3:** Screenshot each step under `docs/phase-8p5-screenshots/`.
- [ ] **Step 4:** Accessibility audit on `/statistics`: assert every `<img alt>` is non-empty; assert the zoom modal traps focus (shadcn Dialog already does this).

---

## Task 12: `/security-review` + BUILD_LOG + tag

Security targets:
- `services/stats/charts/*` — every renderer calls `matplotlib.use("Agg")` indirectly via `_base`; no `plt.show()`. Every renderer wraps figure creation in `fig_context` so figures close on exception. No user-supplied string is interpolated into a shell or filesystem path. `title` (if passed) is `html.escape`d before being set on the axes — defence-in-depth.
- Chart dispatcher — every renderer call is wrapped in `try/except Exception` returning `None`. Test in Task 8 asserts this never breaks the numerics path.
- Frontend `ChartImage` — `<img src>` is always a `data:image/png;base64,...` URI minted server-side; ProseMirror's schema's image node accepts it. No `dangerouslySetInnerHTML`.

BUILD_LOG entry: append `## 2026-05-18 · Phase 8.5 — Stats visualisation ✅ COMPLETE` covering: five chart renderers, dispatcher, no schema change, ~+45 backend tests, ~+5 vitest, all 488+ existing stats tests still green, decisions (PNG-only — SVG out of scope; partial regression plot deferred; icc/cohen_kappa not visualised in v1).

- [ ] **Step 1:** Run `/security-review`.
- [ ] **Step 2:** Compose BUILD_LOG entry.
- [ ] **Step 3:** `git tag phase-8p5`.

---

## Out of scope (deferred)

- **Vector (SVG) output.** PNG only in v1. SVG would let users zoom losslessly in the manuscript but requires ProseMirror schema work like Phase 7's PRISMA decision.
- **Partial regression plots** for `multiple_linear` and `logistic` (we currently substitute scatter of the first predictor). Deferred to a future "stats polish" pass.
- **Residual diagnostics** (residuals vs fitted, scale-location, leverage) for OLS — out of scope for v1.
- **Forest-plot-style coefficient plots** for multiple regression — deferred (overlaps with Phase 7.5 meta forest plot infrastructure if we want to converge later).
- **Charts for `icc` and `cohen_kappa`** — agreement tables work poorly as plots. Could become "Bland-Altman" + "agreement heatmap" in a future pass; logged in DEFERRED.md.
- **Per-user theme / colour-blind-safe palette switch** — uses seaborn defaults in v1.
- **Chart caching layer** — re-renders on every `/run`. With matplotlib `Agg` + `dpi=130` this is sub-second; revisit if instrumentation shows it as a hotspot.

---

## Self-Review

**Spec coverage:**
- Box plot for group-comparison tests ✅ Task 2 (dispatched for `independent_t`, `mann_whitney`, `one_way_anova`, `kruskal_wallis`, `rm_anova`)
- Histogram for single-variable distribution ✅ Task 3 (used for `paired_t`/`wilcoxon_signed` differences)
- QQ plot for normality diagnostic ✅ Task 4 (module ready; primary-chart slot only renders one chart per analysis in v1)
- Scatter plot with fit + 95% CI for regressions ✅ Task 5 (`pearson`/`spearman`/`linear_regression`/`multiple_linear`/`logistic`)
- KM survival curve with at-risk band ✅ Task 6 (`kaplan_meier`/`cox_ph`)
- `(dataset_df, var_spec) -> bytes` style ✅ Task 1 (PNG bytes via helper + dict wrapper for storage; pure functions throughout)
- matplotlib 'Agg' + seaborn ✅ Task 1
- Stored as `{"format": "png", "data_uri": "data:image/png;base64,..."}` in `AnalysisResult.chart` ✅ Task 7
- Failure → log + null + carry on ✅ Task 7, 8
- `AnalysisResultCard` renders the chart with zoom + download ✅ Tasks 9, 10
- Doesn't break the existing 488+ stats route tests ✅ Task 7 (additive only; explicit regression test in Task 7's `test_chart_dispatch_does_not_break_numerics`)

**Multi-user readiness:** unchanged — no new rows, no new repository. Charts are computed at run-time from the user's own dataset, persisted to the user-scoped `analysis_results` row.

**TDD ordering:** every renderer + dispatcher has tests written before implementation. Resilience tests are their own task.

**Bite-sized tasks:** 12 tasks. Most are ~3–5 minute steps.

**Type consistency:** the stored chart shape `{format, data_uri, byte_size}` is a stable contract documented in Task 1 and verified end-to-end in Task 8. Frontend `chart` is already `z.record(z.string(), z.any()).nullable()`; the new component coerces to the concrete shape at the boundary (`as { format: 'png'; ... }`).

**Self-check ok. Proceeding to execution.**
````

---

## Two-paragraph summary

**Phase 7.5 — Meta-analysis.** This sits inside the Systematic Review module as a sixth tab, "Meta-analysis", and adds two new tables (`meta_analyses`, `meta_inputs`, alembic 0008) plus a clean `services/meta/` subtree split into `effect_sizes`, `pooling`, `heterogeneity`, `forest_plot`, `funnel_plot`. Every numeric path (MD, SMD via Hedges' g, OR, RR, HR, Fisher-z r, fixed-effects inverse-variance and DerSimonian-Laird random-effects, Cochran's Q + I² + τ²) is hand-verified against Cochrane Handbook v6.3 worked examples before implementation; the plot renderers are tested for PNG magic bytes and matplotlib state leaks. A new `AIProvider.interpret_meta_analysis` method takes pre-computed numerics + a token-list of pooled studies and emits a Results paragraph with one `[CITE_<article_id>]` per study, preserving the Phase 5/6/7 contract (the prompt explicitly forbids invented tokens). The route layer extends `routes/reviews.py` via a new `reviews_meta.py` submodule and reuses the existing `_push_to_section` plumbing with a `meta-analysis-forest` class hook so push-to-Results is idempotent. Frontend adds six components under `components/review/meta/` driven by a single `useMeta.ts` TanStack hook tree, with the forest/funnel images cache-busted via `meta.updated_at`. 22 tasks total, TDD-first, ~+90 backend tests, one new vitest, cross-user/cross-project security regression in `test_security_meta_isolation.py`.

**Phase 8.5 — Stats visualisation.** This is a purely additive frontend+pipeline polish that wires server-side matplotlib charts into the existing `AnalysisResult.chart` JSON column (already nullable, already added in Phase 6; the FE zod schema already accepts it). New `services/stats/charts/` subtree exposes five pure renderers (`box_plot`, `histogram`, `qq_plot`, `scatter_plot`, `km_curve`) plus a shared `_base.py` that pins `matplotlib.use('Agg')` and provides a `fig_context` + `fig_to_data_uri` helper, so every renderer is a one-line wrapper that returns the `{format, data_uri, byte_size}` dict directly stored in the DB. A single dispatcher line is added to `services/stats/runner.run` (`result = replace(result, chart=...)`) so all 19 existing test handlers are touched in one place; failures are caught, logged at WARNING and persisted as `None`, guaranteeing the 488+ existing stats route tests stay green (an explicit regression test asserts numerics parity before/after dispatch). Frontend adds `ChartImage.tsx` with a click-to-zoom shadcn Dialog and a Download PNG anchor pointing at the data URI; `AnalysisResultCard.tsx` gets a five-line insertion. No new pip deps (matplotlib + seaborn already installed by pingouin in Phase 6), no migration, no schema change on the FE. 12 tasks, ~+45 backend tests, ~+5 vitest.

### Critical Files for Implementation

- `/Users/inayat/Desktop/Research-assistant/apps/api/src/research_api/services/stats/runner.py` (chart dispatch wire-in + 7.5 reference for handler shape)
- `/Users/inayat/Desktop/Research-assistant/apps/api/src/research_api/routes/reviews.py` (`_push_to_section`, `_BLOCK_TAG_BY_CLASS` — 7.5 push path reuses these)
- `/Users/inayat/Desktop/Research-assistant/apps/api/src/research_api/services/ai/base.py` (Protocol; 7.5 adds `interpret_meta_analysis`)
- `/Users/inayat/Desktop/Research-assistant/apps/api/src/research_api/db/models.py` (`AnalysisResult.chart` already present; 7.5 appends `MetaAnalysis` + `MetaInput`)
- `/Users/inayat/Desktop/Research-assistant/apps/web/src/components/statistics/AnalysisResultCard.tsx` (8.5 chart slot) and `/Users/inayat/Desktop/Research-assistant/apps/web/src/routes/SystematicReviewPage.tsx` (7.5 sixth tab)
