# Clustered Safety Events and the Effective Sample Size in AV Fleet Rate Estimation

> ### ⚠️ All results in this repository are produced on SYNTHETIC data.
> No real autonomous vehicle fleet data was used. Every design effect, coverage
> figure, and mileage number in the paper is generated from an assumed
> cluster-size distribution. Nothing here measures any real fleet's clustering.
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
   74% at D = 3 and 54% at D = 7.
2. **Required demonstration mileage is understated by exactly D.** A programme
   that computes its mileage target assuming independence stops with between a
   third and a seventh of the evidence it believes it has. The error is in the
   unsafe direction.
3. **Empirical-Bayes shrinkage weights `n/(n+k)` over-trust thin local data**,
   costing up to 7.8× in mean squared error here.

The correction substitutes an effective sample size `n_eff = n / D̂`, where `D̂`
is estimated from the logs themselves. It requires no new instrumentation.

## Honest positioning

The design effect is textbook survey statistics (Kish 1965, Cochran 1977), and
cluster-robust variance estimation is standard. **No new mathematics is claimed.**
The contribution is the transfer of that machinery into a literature that is not
using it, the quantification of what its absence costs in this regime, and the
observation that the correction is free.

## Files

| File | What it is |
|---|---|
| `paper.pdf` | The paper (10 pages) |
| `paper.tex` | LaTeX source |
| `references.bib` | Bibliography |
| `sim_clustered_av_rates.py` | Reproduces every number in Tables 1–3. numpy only. |
| `make_figure.py` | Reproduces Figure 1 from the simulation |
| `coverage_vs_deff.pdf` / `.png` | Figure 1 |
| `estimate_deff_from_dmv.py` | Estimates D̂ from California DMV disengagement CSVs (see below) |

## Reproducing

```bash
python3 sim_clustered_av_rates.py   # Tables 1-3
python3 make_figure.py              # Figure 1
```

Requires `numpy` (and `matplotlib` for the figure). Runs in well under a minute.

To rebuild the paper:

```bash
pdflatex paper && bibtex paper && pdflatex paper && pdflatex paper
```

## The open empirical step

The single most valuable extension is to replace the assumed design effects with
measured ones. `estimate_deff_from_dmv.py` is written for exactly that.

California DMV disengagement reports publish **one row per disengagement**, with
`DATE` and `VIN NUMBER` fields. A vehicle-day is a natural, conservative cluster
unit. Download a CSV from the
[CA DMV disengagement reports page](https://www.dmv.ca.gov/portal/vehicle-industry-services/autonomous-vehicles/disengagement-reports/)
and run:

```bash
python3 estimate_deff_from_dmv.py 2023-disengagement-reports.csv
```

**Read the caveats in that script's docstring before quoting any number it
prints.** Reporting practice varies by manufacturer and year, some filings
aggregate rather than enumerate, the vehicle-day is one cluster choice among
several, and safety-driver disengagements are not the same event class as
driverless safety events.

## Related work this builds on and distinguishes from

- **Fleet rate estimation that assumes independence:** Terres et al. (2023),
  Chen et al. (2026), Zhao et al. (2025). Two of the three explicitly flag
  dependence as out of scope.
- **Dependence-aware traffic conflict extremes:** Songchitruksa & Tarko (2006),
  Zheng & Sayed (2019), and more recent self-/cross-exciting conditional POT
  work. Section 2 of the paper argues why that machinery does not transfer
  directly — it models one densely observed site, while fleet dependence is
  nested across scene, drive, and software release.
- **Dependence corrections elsewhere:** Ferro & Segers (2003) on declustering,
  Kish (1965) and Cochran (1977) on design effects, Liang & Zeger (1986) on
  cluster-robust variance, López de Prado (2018) on overlapping labels.

## Citation

Archived via Zenodo; DOI badge to be added on first release.

## Acknowledgments

Portions of the literature review and drafting were assisted by Claude
(Anthropic); the research direction, modelling choices, and conclusions are the
author's own.
