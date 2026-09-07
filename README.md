# Clustered Safety Events and the Effective Sample Size in AV Fleet Rate Estimation

[![DOI](https://zenodo.org/badge/1360381474.svg)](https://doi.org/10.5281/zenodo.22646556)

> ### ⚠️ Read this before quoting any number here
> The **simulation study is synthetic** — Tables 1–3 come from an assumed
> cluster-size distribution, not from fitted data.
> The **measured design effects (Table 4) are real**, computed from public
> California DMV disengagement filings. But those are *safety-driver
> disengagements*, which are a different event class from *driverless* safety
> events. Read them as evidence that substantial clustering occurs in real
> filings — not as values transferable to a driverless deployment.
> This is an independent preprint and **has not been peer reviewed**.

**Author:** Pouria Emami Tabrizi

---

## What this is

Autonomous vehicle fleet validation estimates rare-event rates per mile and
attaches confidence statements to them. The estimators in current use treat
logged events as independent Poisson arrivals. Real fleet events arrive in
clusters — one construction zone, one rain hour, one badly handled intersection
produces several correlated events.

This paper models the event stream as a compound Poisson (Neyman–Scott) process
and shows what ignoring the clustering costs:

1. **Confidence intervals under-cover.** A nominal 95% interval has asymptotic
   coverage `2Φ(z/√D) − 1`, where `D = E[K²]/E[K]` is the design effect. That is
   74% at D = 3 and 54% at D = 7. This is a closed-form result (Proposition 1),
   confirmed by simulation to within one percentage point.
2. **Required demonstration mileage is understated by exactly D.** A programme
   that sizes its mileage target under the independence assumption stops with
   between a third and a seventh of the evidence implied by its own confidence
   statement. The discrepancy runs in the less cautious direction.
3. **Empirical-Bayes shrinkage weights `n/(n+k)` over-trust thin local data**,
   costing up to 7.8× in mean squared error here.

The correction substitutes an effective sample size `n_eff = n / D̂`, where `D̂`
is estimated from the logs themselves. It requires no new instrumentation.

## The measured result

Computed over vehicle-day clusters in the CA DMV testing-with-a-driver filings:

| | 2023 | 2024 |
|---|---|---|
| Events / vehicle-days | 6,562 / 2,989 | 1,773 / 981 |
| **Pooled D̂** | **4.79** | **5.29** |
| Per-fleet D̂ range | 1.00 – 12.53 | 1.00 – 13.77 |

Two things matter here. The pooled value near 5 means a nominal 95% interval
covers roughly 62% and mileage targets are understated fivefold. More
importantly, **D̂ is not a constant** — Waymo, Nuro, Zoox and Woven by Toyota
report near-unclustered events (D̂ ≈ 1.0–1.2), while Aurora, Ghost Autonomy and
aiMotive exceed 8. Several fleets are stable year over year (aiMotive 8.02 →
8.31, Bosch 6.37 → 5.88, Waymo 1.04 → 1.19), suggesting D̂ captures something
persistent about how a programme operates and logs.

That spread is the paper's strongest argument for *measuring* D rather than
assuming any value — including the values used in our own simulation.

Full caveats are in Section 6.2 of the paper and in
`estimate_deff_from_dmv.py`'s docstring. The short version: event class,
reporting practice, choice of cluster unit, and limited coverage.

## Honest positioning

The design effect is textbook survey statistics (Kish 1965, Cochran 1977), and
cluster-robust variance estimation is standard. **No new mathematics is claimed.**
The contribution is to connect that machinery to a setting where it has not yet
been applied, to quantify what its absence costs in this regime, and to note that
the correction requires no new instrumentation.

## Files

| File | What it is |
|---|---|
| `paper.pdf` | The paper (11 pages) |
| `paper.tex`, `references.bib` | Source and bibliography |
| `sim_clustered_av_rates.py` | Reproduces Tables 1–3 and Proposition 1. numpy only. |
| `make_figure.py` | Reproduces Figure 1 |
| `coverage_vs_deff.pdf` / `.png` | Figure 1 |
| `empirical_deff.py` | Reproduces Table 4 from the DMV CSVs |
| `estimate_deff_from_dmv.py` | Single-file D̂ estimator, with the full caveat list |
| `data/` | The CA DMV CSVs used (public records) |

## Reproducing

```bash
python3 sim_clustered_av_rates.py                        # Tables 1-3
python3 make_figure.py                                   # Figure 1
python3 empirical_deff.py data/2023-*.csv data/2024-*.csv # Table 4
```

Requires `numpy` (and `matplotlib` for the figure). Everything runs in under a
minute.

Rebuild the paper with:

```bash
pdflatex paper && bibtex paper && pdflatex paper && pdflatex paper
```

## Data provenance

The CSVs in `data/` are the **testing-with-a-driver** disengagement reports from
the [CA DMV disengagement reports page](https://www.dmv.ca.gov/portal/vehicle-industry-services/autonomous-vehicles/disengagement-reports/),
for the 2023 and 2024 reporting years. They are California public records and are
included here so Table 4 is exactly reproducible.

Note that the DMV's separate **driverless** filings are far too sparse for this
purpose — the 2024 driverless file holds roughly 21 rows from one manufacturer.
Both files also contain large numbers of entirely blank trailing rows (an export
artefact); the scripts skip them and report how many, and no reported event is
discarded.

## Related work this builds on and distinguishes from

- **Fleet rate estimation under an independence assumption:** Terres et al.
  (2023), Chen et al. (2026), Zhao et al. (2025). Two of the three are explicit
  that dependence lies outside their scope — which is what makes this extension
  straightforward to state.
- **Dependence-aware traffic conflict extremes:** Songchitruksa & Tarko (2006),
  Zheng & Sayed (2019), and more recent self-/cross-exciting conditional POT
  work. Section 2 discusses why that machinery does not transfer directly — it
  describes one densely observed site, while fleet dependence is nested across
  scene, drive, and software release.
- **Dependence corrections elsewhere:** Ferro & Segers (2003) on declustering,
  Kish (1965) and Cochran (1977) on design effects, Liang & Zeger (1986) on
  cluster-robust variance, López de Prado (2018) on overlapping labels.

## Citation

Archived on Zenodo. Two DOIs exist and they mean different things:

- **Concept DOI — [10.5281/zenodo.22646556](https://doi.org/10.5281/zenodo.22646556)**
  always resolves to the latest release. Cite this one unless you need a fixed
  snapshot.
- **Version DOI — [10.5281/zenodo.22646557](https://doi.org/10.5281/zenodo.22646557)**
  is v1.0.0 specifically, frozen. Cite this one for exact reproducibility.

```bibtex
@software{emamitabrizi2026clustered,
  author    = {Emami Tabrizi, Pouria},
  title     = {Clustered Safety Events and the Effective Sample Size in
               Autonomous Vehicle Fleet Rate Estimation},
  year      = {2026},
  publisher = {Zenodo},
  version   = {v1.0.0},
  doi       = {10.5281/zenodo.22646557},
  url       = {https://doi.org/10.5281/zenodo.22646556}
}
```

## Acknowledgments

Portions of the literature review and drafting were assisted by Claude
(Anthropic); the research direction, modelling choices, and conclusions are the
author's own.
