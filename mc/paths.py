"""Joint weekly paths for BTC price, net mNAV, MSTR ADV and EUR/USD, generated one step at a time.

BTC: GBM, or a block bootstrap of historical weekly log returns standardized to mean 0 and sd 1 and rescaled to
btc_vol, so both models share drift and volatility and differ only in tails and clustering.
mNAV: exact OU step on log mNAV toward log(mnav_level) + mnav_dd_beta x log(P / P_ref). With mnav_link="start",
P_ref is the starting price (the static quarterly path's form, symmetric); with "peak" it is the running peak of the
path, so the premium compresses in every drawdown and only recovers at a new high.
ADV: OU on log ADV. EUR/USD: driftless in log terms. Shocks for mNAV, ADV and FX are correlated with the
standardized BTC shock through mnav_rho, adv_rho and fx_rho.
"""
from __future__ import annotations

import math

import numpy as np

from . import history
from .params import Params, half_life_to_b

DT = history.WEEK


def standardized_history(p: Params) -> np.ndarray:
    r = history.btc_weekly_log_returns(*p.btc_window)
    return (r - r.mean()) / r.std(ddof=1)


class Market:
    def __init__(self, p: Params, btc0: float, mnav0: float, adv0: float, fx0: float, rng: np.random.Generator,
                 n: int | None = None):
        self.p, self.rng = p, rng
        self.n = n or p.n_paths
        n = self.n
        self.log_p = np.full(n, math.log(btc0))
        self.peak = self.log_p.copy()
        self.log_p0 = math.log(btc0)
        self.x_m = np.full(n, math.log(mnav0))
        self.x_a = np.full(n, math.log(adv0))
        self.log_fx = np.full(n, math.log(fx0))
        self.k = 0
        self.b_m = half_life_to_b(p.mnav_half_life, DT)
        self.b_a = half_life_to_b(p.adv_half_life, DT)
        if p.model == "bootstrap":
            self.hist = standardized_history(p)
            self.block_start = np.zeros(n, dtype=np.int64)
        elif p.model != "gbm":
            raise ValueError(f"unknown model {p.model!r}")

    def _btc_shock(self) -> np.ndarray:
        if self.p.model == "gbm":
            return self.rng.standard_normal(self.n)
        L = len(self.hist)
        if self.k % self.p.block_weeks == 0:
            self.block_start = self.rng.integers(0, L, self.n)
        return self.hist[(self.block_start + self.k % self.p.block_weeks) % L]

    @staticmethod
    def _corr(z: np.ndarray, rho: float, e: np.ndarray) -> np.ndarray:
        return rho * z + math.sqrt(max(0.0, 1 - rho * rho)) * e

    def step(self) -> dict:
        p = self.p
        z = self._btc_shock()
        e = self.rng.standard_normal((3, self.n))
        self.log_p += p.btc_log_drift * DT + p.btc_vol * math.sqrt(DT) * z
        np.maximum(self.peak, self.log_p, out=self.peak)
        ref = self.peak if p.mnav_link == "peak" else self.log_p0
        target = math.log(p.mnav_level) + p.mnav_dd_beta * (self.log_p - ref)
        self.x_m = target + self.b_m * (self.x_m - target) + p.mnav_sd * math.sqrt(1 - self.b_m ** 2) * \
            self._corr(z, p.mnav_rho, e[0])
        la = math.log(p.adv_level)
        self.x_a = la + self.b_a * (self.x_a - la) + p.adv_sd * math.sqrt(1 - self.b_a ** 2) * \
            self._corr(z, p.adv_rho, e[1])
        self.log_fx += p.fx_vol * math.sqrt(DT) * self._corr(z, p.fx_rho, e[2])
        self.k += 1
        return {"btc": np.exp(self.log_p), "mnav": np.exp(self.x_m), "adv": np.exp(self.x_a), "fx": np.exp(self.log_fx),
                "drawdown": self.log_p - self.peak}
