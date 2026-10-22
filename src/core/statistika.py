"""Statistika proti nafouknutym vysledkum (R-049, architektura-v2, faze 2): pravdepodobnost skutecneho Sharpeova
pomeru (PSR), jeho korekce na vicenasobne testovani (DSR) a pravdepodobnost preuceni (PBO, CSCV).

Zdroje (primarni):
* Bailey, D. H., Lopez de Prado, M. (2014): The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting
  and Non-Normality. Journal of Portfolio Management 40(5). Vzorce (PSR, ocekavane maximum SR ze N pokusu, DSR).
* Bailey, D. H., Borwein, J., Lopez de Prado, M., Zhu, Q. J. (2017): The Probability of Backtest Overfitting. Journal of
  Computational Finance 20(4). Algoritmus CSCV (combinatorially symmetric cross-validation).

Vsechno se pocita z vykonnosti za JEDNO pozorovani (u nas mesic), ne rocne. Sharpe = prumer / smerodatna odchylka
(ddof = 1), bezrizikova sazba 0 (vynosy uctu jsou uz po nakladech a swapu; peníze na uctu bez obchodu nic nenesou).
Zadna funkce nezavisi na datech ani na scipy (jen math, statistics, numpy).
"""

from __future__ import annotations

from itertools import combinations
from math import e, sqrt
from statistics import NormalDist

import numpy as np

EULER_GAMMA = 0.5772156649015329
_N01 = NormalDist()


def sharpe(x) -> float:
    """Sharpe ratio per observation: mean / sample standard deviation."""
    x = np.asarray(x, float)
    sd = x.std(ddof=1)
    return float(x.mean() / sd) if sd > 0 else 0.0


def skew_kurt(x) -> tuple[float, float]:
    """Skewness and (non-excess) kurtosis of the returns, the moments the PSR / DSR formulas use (normal: 0 and 3)."""
    x = np.asarray(x, float)
    d = x - x.mean()
    s2 = float(np.mean(d ** 2))
    if s2 <= 0:
        return 0.0, 3.0
    return float(np.mean(d ** 3) / s2 ** 1.5), float(np.mean(d ** 4) / s2 ** 2)


def psr(sr_hat: float, sr_star: float, t: int, skew: float, kurt: float) -> float:
    """Probabilistic Sharpe ratio: the probability that the TRUE Sharpe ratio exceeds `sr_star`, given the estimate
    `sr_hat` from `t` observations with the returns' skewness and kurtosis (Bailey, Lopez de Prado 2014, eq. 2)."""
    denom = 1.0 - skew * sr_hat + (kurt - 1.0) / 4.0 * sr_hat ** 2
    if denom <= 0 or t < 2:
        return float("nan")
    return _N01.cdf((sr_hat - sr_star) * sqrt(t - 1) / sqrt(denom))


def expected_max_sr(n_trials: int, var_sr: float) -> float:
    """Expected maximum of the Sharpe ratios of `n_trials` independent trials whose TRUE Sharpe ratio is zero and whose
    estimates have variance `var_sr` (Bailey, Lopez de Prado 2014, eq. 6): the bar a single best-of-N result has to clear."""
    if n_trials <= 1:
        return 0.0
    return sqrt(var_sr) * ((1.0 - EULER_GAMMA) * _N01.inv_cdf(1.0 - 1.0 / n_trials)
                           + EULER_GAMMA * _N01.inv_cdf(1.0 - 1.0 / (n_trials * e)))


def dsr(sr_hat: float, t: int, skew: float, kurt: float, n_trials: int, var_sr: float | None = None) -> float:
    """Deflated Sharpe ratio = PSR against the expected best-of-`n_trials` Sharpe ratio of pure noise. With
    `var_sr = None` the trials' Sharpe estimates are assumed to vary only by sampling error, var = 1 / (t - 1) (the
    value for trials with zero true Sharpe; an optimistic bar if the trials were more dispersed)."""
    v = 1.0 / (t - 1) if var_sr is None else var_sr
    return psr(sr_hat, expected_max_sr(n_trials, v), t, skew, kurt)


def dsr_of_series(returns, n_trials: int, var_sr: float | None = None) -> dict:
    """DSR of one return series (per observation) for `n_trials` trials; everything the report needs."""
    r = np.asarray(returns, float)
    t = len(r)
    sr = sharpe(r)
    sk, ku = skew_kurt(r)
    v = 1.0 / (t - 1) if var_sr is None else var_sr
    sr0 = expected_max_sr(n_trials, v)
    return {"t": t, "sr": sr, "skew": sk, "kurt": ku, "n_trials": n_trials, "sr0": sr0, "psr0": psr(sr, 0.0, t, sk, ku),
            "dsr": psr(sr, sr0, t, sk, ku)}


def pbo_cscv(m, s: int = 16) -> dict:
    """Probability of backtest overfitting by CSCV. `m` is a (T x N) matrix: T observations (time order) of N
    strategies / trials. The T rows are cut into `s` equal blocks; for every choice of s/2 blocks as the in-sample
    part (the other half is out-of-sample) the in-sample best strategy by Sharpe ratio is looked up and its relative
    rank among all strategies out-of-sample is taken. PBO = the share of choices where that rank is at or below the
    median (the in-sample winner is no better than an average strategy out-of-sample). Bailey et al. 2017."""
    m = np.asarray(m, float)
    t, n = m.shape
    if s % 2 or s < 4 or n < 2:
        raise ValueError("s must be even, >= 4, and at least 2 strategies are needed")
    size = t // s
    if size < 2:
        raise ValueError("too few observations for this number of blocks")
    blocks = m[:size * s].reshape(s, size, n)
    cnt = np.full((s, 1), size, float)
    sums = blocks.sum(axis=1)                                   # (s, n)
    sq = (blocks ** 2).sum(axis=1)
    logits = []
    for ins in combinations(range(s), s // 2):
        oos = [b for b in range(s) if b not in ins]
        r_in, r_out = _sharpe_from(sums[list(ins)], sq[list(ins)], cnt[list(ins)]), _sharpe_from(sums[oos], sq[oos], cnt[oos])
        best = int(np.argmax(r_in))
        rank = (np.sum(r_out < r_out[best]) + 0.5 * np.sum(r_out == r_out[best])) / n   # relative rank in (0, 1)
        rank = min(max(rank, 1e-9), 1 - 1e-9)
        logits.append(float(np.log(rank / (1.0 - rank))))
    logits = np.array(logits)
    return {"pbo": float(np.mean(logits <= 0)), "n_comb": len(logits), "median_logit": float(np.median(logits)),
            "n_strategies": n, "t_used": size * s, "s": s}


def _sharpe_from(sums, sqs, counts) -> np.ndarray:
    """Sharpe ratio (ddof = 1) of each column from block sums, sums of squares and counts."""
    n = counts.sum()
    mean = sums.sum(axis=0) / n
    var = (sqs.sum(axis=0) - n * mean ** 2) / (n - 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where(var > 0, mean / np.sqrt(np.maximum(var, 1e-300)), 0.0)
    return out
