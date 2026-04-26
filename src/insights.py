from __future__ import annotations

import pandas as pd


def opportunity_cost(amount_eur: float, monthly_return: float = 0.07 / 12) -> float:
    """Naive future value of a lump sum if invested today, compounded monthly for 1y."""
    if amount_eur <= 0:
        return 0.0
    return amount_eur * (1 + monthly_return) ** 12


def category_ytd(eu_long: pd.DataFrame, category: str, year: int | None = None) -> float:
    if eu_long.empty:
        return 0.0
    df = eu_long[eu_long["category"].str.lower() == category.lower()].copy()
    if df.empty:
        return 0.0
    if year is not None and "month_dt" in df.columns:
        df = df[df["month_dt"].dt.year == year]
    return float(df["amount"].sum())


def total_savings_ytd(eu_long: pd.DataFrame, year: int | None = None) -> dict[str, float]:
    if eu_long.empty:
        return {"entrate": 0.0, "uscite": 0.0, "risparmio": 0.0, "pct": 0.0}
    df = eu_long.copy()
    if year is not None and "month_dt" in df.columns:
        df = df[df["month_dt"].dt.year == year]
    entrate = float(df[df["is_income"]]["amount"].sum())
    uscite = float(df[~df["is_income"]]["amount"].sum())
    risparmio = entrate + uscite
    pct = risparmio / entrate if entrate else 0.0
    return {"entrate": entrate, "uscite": uscite, "risparmio": risparmio, "pct": pct}
