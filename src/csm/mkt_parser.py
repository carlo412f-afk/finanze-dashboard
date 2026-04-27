from __future__ import annotations

import io
import pandas as pd

MKT_SHEET = "Econ_financial_assumptions"

_VARS = [
    "SWAP EUR 10yrs par",
    "Implied Corp Spread EUR",
    "Spread ITA 10yrs",
    "Spread GER 10yrs",
    "Spread FRA 10yrs",
    "Spread SPA 10yrs",
    "VA EUR",
    "EQUITY ITA",
    "EQUITY GER",
    "EQUITY FRA",
    "EQUITY CZK",
    "EQUITY SVI",
    "EQUITY SPA",
    "EQUITY CNY",
    "EQUITY USD",
]


def parse_mkt(file_bytes: bytes) -> pd.DataFrame:
    """
    Returns DataFrame: index = variable name, columns = pd.Timestamp dates,
    values = levels (rates in decimal, equity as index level, spreads in decimal).
    """
    df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=MKT_SHEET, header=None)

    # Date headers from row 4, cols >= 2
    date_map: dict[int, pd.Timestamp] = {}
    for col, val in df.iloc[4].items():
        if int(col) < 2 or pd.isna(val):
            continue
        try:
            date_map[int(col)] = pd.Timestamp(val)
        except Exception:
            pass

    name_col = df.iloc[:, 1].astype(str).str.strip()
    result: dict[str, pd.Series] = {}
    for var in _VARS:
        matches = df[name_col == var]
        if matches.empty:
            continue
        row = matches.iloc[0]
        series: dict[pd.Timestamp, float] = {}
        for col_idx, date in date_map.items():
            val = row.iloc[col_idx]
            if pd.notna(val) and isinstance(val, (int, float)):
                series[date] = float(val)
        if series:
            result[var] = pd.Series(series)

    return pd.DataFrame(result).T if result else pd.DataFrame()


def get_delta(mkt: pd.DataFrame, var: str,
              date_from: pd.Timestamp, date_to: pd.Timestamp) -> float | None:
    """
    Return (end_value - start_value) for a variable, matching the closest available date.
    Returns None if data is unavailable.
    """
    if mkt.empty or var not in mkt.index:
        return None
    series = mkt.loc[var].dropna()
    if series.empty:
        return None
    avail = sorted(series.index)
    start = min(avail, key=lambda d: abs((d - date_from).days))
    end = min(avail, key=lambda d: abs((d - date_to).days))
    if start == end:
        return None
    return float(series[end]) - float(series[start])
