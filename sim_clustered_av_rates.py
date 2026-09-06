"""
Clustered safety events in AV fleet rate estimation.

Question: AV evaluation papers estimate rare-event rates (per mile) treating
logged events as independent Poisson arrivals. Real fleet events arrive in
CLUSTERS -- one construction zone, one rain hour, one bad unprotected left
generates several correlated near-misses. What does ignoring that cost?

Generating process (Neyman-Scott / compound Poisson):
  cluster centers ~ Poisson(lambda_c * m) over m miles
  cluster size K   ~ Geometric(p) on {1,2,...}, mean 1/p
  N = sum of K_i

  theta = lambda_c * E[K]                (true events per mile)
  Var(N) = lambda_c * m * E[K^2]
  DEFF  = E[K^2]/E[K] = (2-p)/p          (design effect / variance inflation)

Naive analyst: N ~ Poisson(theta*m), CI = theta_hat +/- 1.96*sqrt(N)/m
Corrected:     CI = theta_hat +/- 1.96*sqrt(N*DEFF_hat)/m
               with DEFF_hat = sum(K_i^2)/sum(K_i) estimated from the logs,
               which is available in practice because every logged event
               carries a scene / drive-segment id.

ALL DATA SYNTHETIC. No real fleet data is used anywhere in this script.
"""

import numpy as np

RNG = np.random.default_rng(20260905)
Z = 1.959963984540054  # 95% normal quantile


def deff_true(p):
    """Design effect for Geometric(p) cluster sizes on {1,2,...}."""
    return (2.0 - p) / p


def analytic_coverage(deff, z=Z):
    """
    Proposition 1. The naive interval uses SE sqrt(theta/m) when the true SE is
    sqrt(theta*DEFF/m), so it is too narrow by a factor sqrt(DEFF) and its
    asymptotic coverage is

        2 * Phi(z / sqrt(DEFF)) - 1

    Implemented with math.erf so the script keeps its numpy-only dependency.
    """
    from math import erf, sqrt
    x = z / sqrt(deff)
    phi = 0.5 * (1.0 + erf(x / sqrt(2.0)))
    return 2.0 * phi - 1.0


def simulate_fleet(lambda_c, p, miles, rng):
    """One fleet-deployment replication. Returns (N, DEFF_hat, n_clusters)."""
    n_clusters = rng.poisson(lambda_c * miles)
    if n_clusters == 0:
        return 0, np.nan, 0
    K = rng.geometric(p, size=n_clusters)  # numpy geometric is on {1,2,...}
    N = int(K.sum())
    deff_hat = float((K ** 2).sum() / K.sum())
    return N, deff_hat, n_clusters


def coverage_study(theta_true, p, miles, n_rep=20000, rng=RNG):
    """Actual coverage of nominal 95% CIs, naive vs corrected."""
    D = deff_true(p)
    mean_K = 1.0 / p
    lambda_c = theta_true / mean_K

    hit_naive = 0
    hit_corr = 0
    width_naive = []
    width_corr = []
    usable = 0

    for _ in range(n_rep):
        N, deff_hat, nc = simulate_fleet(lambda_c, p, miles, rng)
        if N == 0:
            continue
        usable += 1
        theta_hat = N / miles

        half_naive = Z * np.sqrt(N) / miles
        half_corr = Z * np.sqrt(N * deff_hat) / miles

        if abs(theta_hat - theta_true) <= half_naive:
            hit_naive += 1
        if abs(theta_hat - theta_true) <= half_corr:
            hit_corr += 1

        width_naive.append(2 * half_naive)
        width_corr.append(2 * half_corr)

    return {
        "p": p,
        "DEFF_true": D,
        "mean_cluster_size": mean_K,
        "coverage_naive": hit_naive / usable,
        "coverage_corrected": hit_corr / usable,
        "mean_width_naive": float(np.mean(width_naive)),
        "mean_width_corrected": float(np.mean(width_corr)),
        "reps_used": usable,
    }


def miles_to_demonstrate(theta_true, theta_target, p):
    """
    Miles needed for the 95% upper confidence limit on theta to fall below a
    safety target theta_target. Analytic, from the normal approximation:
        theta + Z*sqrt(theta*DEFF/m) = theta_target
        m = Z^2 * theta * DEFF / (theta_target - theta)^2
    """
    D = deff_true(p)
    gap = theta_target - theta_true
    m_naive = (Z ** 2) * theta_true / (gap ** 2)
    m_corr = m_naive * D
    return m_naive, m_corr, D


def shrinkage_study(theta_true, p, miles, k=15, n_rep=20000, rng=RNG):
    """
    The empirical-Bayes tie-in: a per-segment rate is blended toward a fleet
    prior with weight w = n/(n+k). Using the NOMINAL event count n inflates w,
    so the estimator leans on a noisier local estimate than the evidence
    supports. Compare MSE using nominal n vs effective n.
    """
    D = deff_true(p)
    mean_K = 1.0 / p
    lambda_c = theta_true / mean_K
    prior = theta_true  # unbiased fleet-level prior, so any MSE gap is variance

    se_nominal, se_effective = [], []
    for _ in range(n_rep):
        N, deff_hat, nc = simulate_fleet(lambda_c, p, miles, rng)
        if N == 0:
            continue
        theta_hat = N / miles

        w_nom = N / (N + k)
        n_eff = N / deff_hat
        w_eff = n_eff / (n_eff + k)

        est_nom = w_nom * theta_hat + (1 - w_nom) * prior
        est_eff = w_eff * theta_hat + (1 - w_eff) * prior

        se_nominal.append((est_nom - theta_true) ** 2)
        se_effective.append((est_eff - theta_true) ** 2)

    mse_nom = float(np.mean(se_nominal))
    mse_eff = float(np.mean(se_effective))
    return {
        "p": p,
        "DEFF_true": D,
        "mse_nominal_n": mse_nom,
        "mse_effective_n": mse_eff,
        "mse_ratio": mse_nom / mse_eff,
    }


if __name__ == "__main__":
    THETA = 1e-4        # 1 safety-relevant event per 10,000 miles
    MILES = 5_000_000   # 5M mile deployment
    P_GRID = [1.0, 0.75, 0.5, 0.35, 0.25]

    print("=" * 78)
    print("PART 1 - Coverage of a nominal 95% CI for the event rate")
    print(f"true rate = {THETA:g}/mile, fleet miles = {MILES:,}, 20,000 reps")
    print("=" * 78)
    print(f"{'mean K':>7} {'DEFF':>6} {'naive sim':>10} {'naive thy':>10} "
          f"{'corrected':>10} {'width ratio':>12}")
    for p in P_GRID:
        r = coverage_study(THETA, p, MILES)
        print(f"{r['mean_cluster_size']:>7.2f} {r['DEFF_true']:>6.2f} "
              f"{r['coverage_naive']:>9.1%} "
              f"{analytic_coverage(r['DEFF_true']):>9.1%} "
              f"{r['coverage_corrected']:>9.1%} "
              f"{r['mean_width_corrected']/r['mean_width_naive']:>12.2f}x")

    print()
    print("=" * 78)
    print("PART 2 - Miles required to demonstrate the rate is below a target")
    print(f"true rate = {THETA:g}/mile, target = {1.5*THETA:g}/mile (1.5x true)")
    print("=" * 78)
    print(f"{'mean K':>7} {'DEFF':>6} {'miles naive':>14} {'miles corrected':>17} "
          f"{'extra':>8}")
    for p in P_GRID:
        m_n, m_c, D = miles_to_demonstrate(THETA, 1.5 * THETA, p)
        print(f"{1/p:>7.2f} {D:>6.2f} {m_n:>14,.0f} {m_c:>17,.0f} {D:>7.2f}x")

    print()
    print("=" * 78)
    print("PART 3 - Empirical-Bayes shrinkage weight w = n/(n+k), k=15")
    print("MSE of the blended per-segment rate: nominal n vs effective n")
    print("=" * 78)
    print(f"{'mean K':>7} {'DEFF':>6} {'MSE nominal':>14} {'MSE effective':>15} "
          f"{'ratio':>8}")
    for p in P_GRID:
        r = shrinkage_study(THETA, p, miles=200_000)
        print(f"{1/p:>7.2f} {r['DEFF_true']:>6.2f} {r['mse_nominal_n']:>14.3e} "
              f"{r['mse_effective_n']:>15.3e} {r['mse_ratio']:>7.2f}x")
