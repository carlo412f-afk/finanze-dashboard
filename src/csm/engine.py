from __future__ import annotations

import pandas as pd

# Sensitivity shock sizes (in decimal: 50bps = 0.005, 25% = 0.25)
SHOCK_IR = 0.005
SHOCK_SPREAD = 0.005
SHOCK_EQ = 0.25


def _safe(sens: pd.DataFrame, key: str, entity: str) -> float:
    if key not in sens.index or entity not in sens.columns:
        return float("nan")
    v = sens.at[key, entity]
    return float(v) if pd.notna(v) else float("nan")


def compute_ec_var(
    sens: pd.DataFrame,
    delta_ir: float,        # actual IR move in decimal (e.g. +0.0037 for +37bps)
    delta_gov: float,       # actual gov spread move in decimal
    delta_corp: float,      # actual corp spread move in decimal
    delta_eq: float,        # actual equity move as fraction (e.g. +0.10 for +10%)
) -> pd.DataFrame:
    """
    Compute economic variance on CSM (IFRS17) or PVFP (SII) per entity.

    Methodology (from Note sheet):
    - IR: duration + convexity implied from IR+50 / IR-50 sensitivities
    - Gov / Corp: linear scaling of UGL-only sensitivity  (UGL+VA not yet in scope)
    - Equity: linear scaling, direction-dependent (EQ+25 if delta>0, EQ-25 if delta<0)

    Returns DataFrame: index = entity, columns = [RF, S_Gov, S_Corp, EQ, Ec_Var]
    Values in EUR mln.
    """
    if sens.empty:
        return pd.DataFrame()

    central = sens.loc["CENTRAL"] if "CENTRAL" in sens.index else pd.Series(dtype=float)
    entities = sens.columns.tolist()

    rows = []
    for entity in entities:
        c = _safe(sens, "CENTRAL", entity)
        if pd.isna(c):
            continue

        # ── IR: duration + convexity ──────────────────────────────────────
        d_plus  = _safe(sens, "IR+50", entity) - c
        d_minus = _safe(sens, "IR-50", entity) - c
        if pd.isna(d_plus) or pd.isna(d_minus):
            rf_impact = float("nan")
        else:
            D = (d_plus - d_minus) / (2 * SHOCK_IR)
            C = (d_plus + d_minus) / (SHOCK_IR ** 2)
            rf_impact = D * delta_ir + 0.5 * C * delta_ir ** 2

        # ── Gov spread: linear ────────────────────────────────────────────
        d_gov = _safe(sens, "GOV+50", entity) - c
        gov_impact = (d_gov * delta_gov / SHOCK_SPREAD) if not pd.isna(d_gov) else float("nan")

        # ── Corp spread: linear ───────────────────────────────────────────
        d_corp = _safe(sens, "CORP+50", entity) - c
        corp_impact = (d_corp * delta_corp / SHOCK_SPREAD) if not pd.isna(d_corp) else float("nan")

        # ── Equity: direction-dependent linear ────────────────────────────
        if delta_eq >= 0:
            d_eq = _safe(sens, "EQ+25", entity) - c
        else:
            d_eq = _safe(sens, "EQ-25", entity) - c
        eq_impact = (d_eq * abs(delta_eq) / SHOCK_EQ) if not pd.isna(d_eq) else float("nan")

        ec_var = sum(
            v for v in [rf_impact, gov_impact, corp_impact, eq_impact]
            if not pd.isna(v)
        )

        rows.append({
            "Entity":  entity,
            "RF":      rf_impact,
            "S_Gov":   gov_impact,
            "S_Corp":  corp_impact,
            "EQ":      eq_impact,
            "Ec. Var.": ec_var,
        })

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).set_index("Entity")
