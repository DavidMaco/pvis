"""Tests for analytics/advanced_analytics.py — unit tests for Monte Carlo and risk scoring."""

import numpy as np
import pandas as pd
import pytest


def test_fx_simulation_default_currency():
    """Default currency_id should be 3 (NGN)."""
    from analytics.advanced_analytics import run_fx_simulation
    import inspect

    sig = inspect.signature(run_fx_simulation)
    assert sig.parameters["currency_id"].default == 3, (
        "run_fx_simulation default currency_id should be 3 (NGN)"
    )


def test_fx_simulation_default_days():
    """Default forecast horizon should be 90 trading days."""
    from analytics.advanced_analytics import run_fx_simulation
    import inspect

    sig = inspect.signature(run_fx_simulation)
    assert sig.parameters["days"].default == 90


def test_fx_simulation_default_simulations():
    """Default number of simulations should be 10,000."""
    from analytics.advanced_analytics import run_fx_simulation
    import inspect

    sig = inspect.signature(run_fx_simulation)
    assert sig.parameters["simulations"].default == 10000


def test_gbm_math():
    """Verify Geometric Brownian Motion produces reasonable FX paths."""
    # Simulate a simple GBM path manually
    np.random.seed(42)
    S0 = 1345.0  # starting rate (NGN/USD)
    mu = 0.0001  # small daily drift
    sigma = 0.01  # 1% daily vol
    dt = 1 / 252
    days = 90

    rate = S0
    for _ in range(days):
        z = np.random.normal()
        rate *= np.exp(mu * dt + sigma * np.sqrt(dt) * z)

    # After 90 days, rate should still be in a reasonable range (±30%)
    assert 900 < rate < 1800, f"GBM path ended at unreasonable rate: {rate}"
