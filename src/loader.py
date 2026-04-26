from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Tuple

import pandas as pd
import streamlit as st

from src.parser import EUData, parse_eu, parse_log, parse_patrimonio


SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


class Loader(ABC):
    @abstractmethod
    def load_eu(self) -> Tuple[pd.DataFrame, pd.DataFrame]: ...

    @abstractmethod
    def load_log(self) -> pd.DataFrame: ...

    @abstractmethod
    def load_patrimonio(self) -> pd.DataFrame: ...


def _normalize_private_key(pk: str) -> str:
    """Reconstruct a valid PEM from whatever format arrives via Streamlit secrets."""
    import re

    pk = pk.replace("\\n", "\n").replace("\r\n", "\n").replace("\r", "\n")
    pk = pk.strip()

    m = re.search(r"-----BEGIN PRIVATE KEY-----(.+?)-----END PRIVATE KEY-----", pk, re.DOTALL)
    if m:
        body = re.sub(r"\s+", "", m.group(1))
        chunks = [body[i : i + 64] for i in range(0, len(body), 64)]
        return "-----BEGIN PRIVATE KEY-----\n" + "\n".join(chunks) + "\n-----END PRIVATE KEY-----\n"

    lines = [ln.strip() for ln in pk.split("\n") if ln.strip()]
    return "\n".join(lines) + "\n"


@st.cache_resource(show_spinner=False)
def _gspread_client():
    import gspread
    from google.oauth2.service_account import Credentials

    creds_dict = dict(st.secrets["gcp_service_account"])
    if "private_key" in creds_dict:
        creds_dict["private_key"] = _normalize_private_key(creds_dict["private_key"])

    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


@st.cache_data(ttl=300, show_spinner="📥 Carico dati da Google Sheets…")
def _read_sheet(sheet_id: str, sheet_name: str) -> pd.DataFrame:
    client = _gspread_client()
    ws = client.open_by_key(sheet_id).worksheet(sheet_name)
    values = ws.get_all_values()
    if not values:
        return pd.DataFrame()
    header_idx = 0
    for i, row in enumerate(values[:5]):
        non_empty = sum(1 for x in row if str(x).strip())
        if non_empty >= 3:
            header_idx = i
            break
    headers = values[header_idx]
    headers = [h if h else f"col_{i}" for i, h in enumerate(headers)]
    rows = values[header_idx + 1:]
    return pd.DataFrame(rows, columns=headers)


class GoogleSheetsLoader(Loader):
    def __init__(self, sheet_id: str):
        self.sheet_id = sheet_id

    def load_eu(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        raw = _read_sheet(self.sheet_id, "E/U")
        data = parse_eu(raw)
        return data.long, data.summary

    def load_log(self) -> pd.DataFrame:
        raw = _read_sheet(self.sheet_id, "LOG_Entrate_Uscite")
        return parse_log(raw)

    def load_patrimonio(self) -> pd.DataFrame:
        raw = _read_sheet(self.sheet_id, "Patrimonio")
        return parse_patrimonio(raw)


class MockLoader(Loader):
    """Synthetic data mirroring the structure of Carlo's real Sheet."""

    MONTHS = ["2025-set", "2025-ott", "2025-nov", "2025-dic",
              "2026-gen", "2026-feb", "2026-mar", "2026-apr"]

    CATEGORIES = {
        "Stipendio":            [2505,  1544,  1719,  3736,  2186,  1769,  2647,  0],
        "Trasporto pubblico":   [   0,     0,     0,     0,     0,    -6,   -85,  -44],
        "Cura / Benessere":     [   0,   -25,     0,   -25,     0,     0,   -25, -115],
        "Cultura":              [   0,     0,   -33,     0,  -158,     0,     0,    0],
        "Altro":                [   0,  -108,     0,   -28,   -58,   -67,    -6,    0],
        "Regali":               [   0,   -20,   -62,  -129,   -55,   -43,   -61,    0],
        "Sport":                [ -20,   -50,   -20,   -20,  -281,   -20,   -22,  -99],
        "Salute":               [ -34,   -82,   -31,   -52,   -74,   -73, -216,    -8],
        "Scommesse":            [ -50,  -232,  -248,   -16,   -85,   -30,    60,    0],
        "Silvia":               [   0,     0,     0,  -182,     0,  -100,  -143, -184],
        "Abbonamenti":          [ -94,  -161,   -69,   -24,   -87,   -40,  -173,  -98],
        "Supermercato":         [ -87,   -58,  -167,  -135,   -96,   -57,  -184, -121],
        "Abbigliamento":        [   0,  -436,     0,     0,   -48,  -355,     0,  -80],
        "Auto":                 [ -25,   -44,  -448,   -41,  -196,   -40,  -273,  -26],
        "Divertimento":         [-152,  -319,  -112,  -105,   -30,   -69,  -198, -293],
        "Tecnologia":           [   0,     0,     0, -1256,     0,     0,  -118,    0],
        "Cibo fuori / Bevute":  [ -77,  -181,  -250,  -258,  -101,  -216,  -313, -392],
        "Viaggi":               [-306,  -110,   -52,   -66,  -490, -1011,     0, -608],
        "Casa":                 [-372,  -465,  -377,  -331,  -352,  -449,  -378,  -55],
    }

    def load_eu(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        rows = []
        for cat, values in self.CATEGORIES.items():
            for m, v in zip(self.MONTHS, values):
                rows.append({"category": cat, "month": m, "amount": float(v)})
        long = pd.DataFrame(rows)
        long["month_dt"] = pd.to_datetime(
            long["month"].str.replace("set", "sep").str.replace("ott", "oct").str.replace("dic", "dec"),
            format="%Y-%b", errors="coerce",
        )
        long["is_income"] = long["amount"] > 0

        sum_rows = []
        for m in self.MONTHS:
            month_data = long[long["month"] == m]
            entrate = month_data[month_data["is_income"]]["amount"].sum()
            uscite = month_data[~month_data["is_income"]]["amount"].sum()
            saving_pct = (entrate + uscite) / entrate if entrate else 0
            sum_rows.extend([
                {"label": "entrate", "month": m, "value": entrate},
                {"label": "uscite", "month": m, "value": uscite},
                {"label": "percentuale risparmi", "month": m, "value": saving_pct},
                {"label": "obiettivo", "month": m, "value": 0.5},
            ])
        summary = pd.DataFrame(sum_rows)
        return long, summary

    def load_log(self) -> pd.DataFrame:
        rng = pd.date_range("2026-04-01", "2026-04-26", freq="D")
        rows = []
        for i, d in enumerate(rng):
            rows.append({
                "data_dt": d,
                "mese": pd.Timestamp(d.year, d.month, 1),
                "categoria": ["Supermercato", "Cibo fuori / Bevute", "Viaggi", "Casa"][i % 4],
                "sottocategoria": ["PAM", "Pizzeria", "Voli", "Bolletta Gas"][i % 4],
                "importo": float([15, 30, 120, 25][i % 4]),
                "importo_signed": float([-15, -30, -120, -25][i % 4]),
                "is_income": False,
            })
        return pd.DataFrame(rows)

    def load_patrimonio(self) -> pd.DataFrame:
        return pd.DataFrame([
            {"asset_class": "Liquidità", "value": -881.0},
            {"asset_class": "Stock", "value": 0.0},
            {"asset_class": "Bond", "value": 0.0},
            {"asset_class": "Crypto", "value": 0.0},
            {"asset_class": "Materie Prime", "value": 0.0},
            {"asset_class": "Fondi pensione", "value": 0.0},
        ])


def has_service_account() -> bool:
    try:
        return "gcp_service_account" in st.secrets
    except Exception:
        return False


def _sheet_id_from_secrets() -> str:
    try:
        return str(st.secrets.get("sheet", {}).get("id", ""))
    except Exception:
        return ""


def get_loader(use_mock: bool = False) -> Loader:
    if use_mock or not has_service_account():
        return MockLoader()
    sheet_id = _sheet_id_from_secrets()
    if not sheet_id:
        return MockLoader()
    return GoogleSheetsLoader(sheet_id)
