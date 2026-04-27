from __future__ import annotations

import pandas as pd

IFRS17_SHEET = "SENS_IFRS17_VFA_YE25"
SII_SHEET = "SENS_SII_YE25"
IFRS17_METRIC = "CSM_SENS"
SII_METRIC = "PVFP_SENS"

_SCENARIO_MAP = {
    "CENTRAL": "CENTRAL",
    "IR+50":   "IR+50",
    "IR-50":   "IR-50",
    "GOV+50":  "GOV+50",
    "CORP+50": "CORP+50",
    "EQ+25":   "EQ+25",
    "EQ-25":   "EQ-25",
}


def _map_scenario(raw: str) -> str | None:
    s = str(raw).lower().strip()
    if s == "central":
        return "CENTRAL"
    if "interest" in s and "+50" in s:
        return "IR+50"
    if "interest" in s and "-50" in s:
        return "IR-50"
    if "government" in s and "+50" in s:
        return "GOV+50"
    if "corporate" in s and "+50" in s:
        return "CORP+50"
    if "*125%" in s and "listed" not in s:
        return "EQ+25"
    if "*75%" in s and "listed" not in s:
        return "EQ-25"
    return None


def parse_sens(file_bytes: bytes, sheet_name: str, metric: str) -> pd.DataFrame:
    """
    Parse a sensitivity sheet.
    Returns DataFrame: index = scenario key, columns = entity code,
    values = absolute metric level (EUR mln).
    """
    import io
    df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet_name, header=None)

    # Entity names: row 6, cols >= 5
    entity_row = df.iloc[6]
    entity_map: dict[int, str] = {
        int(col): str(val).strip()
        for col, val in entity_row.items()
        if pd.notna(val) and str(val).strip() and int(col) >= 5
    }

    # Rows where col 3 == metric
    metric_rows = df[df.iloc[:, 3].astype(str).str.strip() == metric]

    records: dict[str, dict[str, float]] = {}
    for _, row in metric_rows.iterrows():
        key = _map_scenario(str(row.iloc[2]))
        if key is None:
            continue
        entity_vals: dict[str, float] = {}
        for col_idx, entity in entity_map.items():
            val = row.iloc[col_idx]
            if pd.notna(val) and isinstance(val, (int, float)):
                entity_vals[entity] = float(val)
        records[key] = entity_vals

    if not records:
        return pd.DataFrame()

    out = pd.DataFrame(records).T  # scenarios × entities
    # Ensure canonical scenario order
    order = [k for k in _SCENARIO_MAP if k in out.index]
    return out.loc[order]


def load_both(file_bytes: bytes) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (ifrs17_sens, sii_sens)."""
    ifrs17 = parse_sens(file_bytes, IFRS17_SHEET, IFRS17_METRIC)
    sii = parse_sens(file_bytes, SII_SHEET, SII_METRIC)
    return ifrs17, sii
