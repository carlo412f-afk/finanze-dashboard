from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd


EMOJI_RE = re.compile(
    "["
    "\U0001F000-\U0001FFFF"
    "☀-⟿"
    "︀-️"
    "‍"
    "]+",
    flags=re.UNICODE,
)


SUMMARY_LABELS = {
    "uscite", "uscite totali",
    "entrate", "entrate totali",
    "percentuale risparmi", "% risparmi",
    "obiettivo",
    "totale generale", "ale generale", "generale",
}


def clean_amount(value) -> float:
    if value is None:
        return 0.0
    s = str(value).strip()
    if not s or s in {"-", "—", "#REF!", "#N/A", "#DIV/0!"}:
        return 0.0
    s = s.replace("\xa0", " ").replace("€", "").replace(" ", "")
    s = s.replace("\\-", "-")
    sign = 1
    if s.startswith("-"):
        sign = -1
        s = s[1:]
    s = s.replace(".", "").replace(",", ".")
    try:
        return sign * float(s)
    except ValueError:
        return 0.0


def clean_category(value) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    if not s:
        return ""
    s = re.sub(r"^Totale\s*", "", s, flags=re.IGNORECASE)
    s = EMOJI_RE.sub("", s).strip()
    return s


def is_summary_row(category_raw: str) -> bool:
    norm = clean_category(category_raw).lower().strip()
    return any(norm == lbl or norm.startswith(lbl) for lbl in SUMMARY_LABELS)


@dataclass(frozen=True)
class EUData:
    long: pd.DataFrame
    summary: pd.DataFrame


def parse_eu(raw: pd.DataFrame) -> EUData:
    if raw.empty:
        return EUData(long=pd.DataFrame(), summary=pd.DataFrame())

    df = raw.copy()
    df.columns = [str(c).strip() for c in df.columns]

    cat_col = df.columns[0]
    sub_col = df.columns[1] if len(df.columns) > 1 else None
    month_cols = [c for c in df.columns[2:] if re.match(r"^\d{4}-\w+$", str(c))]

    if not month_cols:
        return EUData(long=pd.DataFrame(), summary=pd.DataFrame())

    df = df[~df[cat_col].astype(str).str.strip().eq("")]

    summary_mask = df[cat_col].apply(is_summary_row)
    cat_df = df[~summary_mask].copy()
    sum_df = df[summary_mask].copy()

    cat_df["category"] = cat_df[cat_col].apply(clean_category)
    cat_df = cat_df[cat_df["category"] != ""]

    long = cat_df.melt(
        id_vars=["category"],
        value_vars=month_cols,
        var_name="month",
        value_name="amount_raw",
    )
    long["amount"] = long["amount_raw"].apply(clean_amount)
    _IT_TO_EN = [
        ("gen", "jan"), ("mag", "may"), ("giu", "jun"), ("lug", "jul"),
        ("ago", "aug"), ("set", "sep"), ("ott", "oct"), ("dic", "dec"),
    ]
    month_norm = long["month"]
    for it, en in _IT_TO_EN:
        month_norm = month_norm.str.replace(it, en, case=False, regex=False)
    long["month_dt"] = pd.to_datetime(month_norm, format="%Y-%b", errors="coerce")
    long["is_income"] = long["amount"] > 0
    long = long.drop(columns=["amount_raw"])

    if not sum_df.empty:
        sum_df["label"] = sum_df[cat_col].apply(clean_category).str.lower()
        summary_long = sum_df.melt(
            id_vars=["label"],
            value_vars=month_cols,
            var_name="month",
            value_name="value_raw",
        )
        summary_long["value"] = summary_long["value_raw"].apply(clean_amount)
        summary_long = summary_long.drop(columns=["value_raw"])
    else:
        summary_long = pd.DataFrame(columns=["label", "month", "value"])

    return EUData(long=long, summary=summary_long)


def parse_log(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame()

    df = raw.copy()
    df.columns = [str(c).strip() for c in df.columns]

    rename_map = {}
    for c in df.columns:
        cl = c.lower()
        if cl.startswith("data") and "data" not in rename_map.values():
            rename_map[c] = "data"
        elif cl.startswith("categoria"):
            rename_map[c] = "categoria_raw"
        elif cl.startswith("sottocategoria") and "categoria" in cl and not cl.startswith("sottocategoria aggiuntiva"):
            rename_map[c] = "sottocategoria"
        elif cl == "importo":
            rename_map[c] = "importo_raw"
        elif cl.startswith("importo per pivot"):
            rename_map[c] = "importo_signed_raw"
        elif cl == "note":
            rename_map[c] = "note"
        elif cl == "da":
            rename_map[c] = "da"
        elif cl == "a":
            rename_map[c] = "a"

    df = df.rename(columns=rename_map)

    if "data" not in df.columns:
        return pd.DataFrame()

    df["data_dt"] = pd.to_datetime(df["data"], format="%d/%m/%Y", errors="coerce")
    df = df[df["data_dt"].notna()]

    if "importo_signed_raw" in df.columns:
        df["importo_signed"] = df["importo_signed_raw"].apply(clean_amount)
    else:
        df["importo_signed"] = 0.0

    if "importo_raw" in df.columns:
        df["importo"] = df["importo_raw"].apply(clean_amount)
    else:
        df["importo"] = df["importo_signed"].abs()

    df["categoria"] = df.get("categoria_raw", "").apply(clean_category)
    df["sottocategoria"] = df.get("sottocategoria", "").astype(str).str.strip()
    df["mese"] = df["data_dt"].dt.to_period("M").dt.to_timestamp()
    df["is_income"] = df["importo_signed"] > 0

    keep = ["data_dt", "mese", "categoria", "sottocategoria", "importo", "importo_signed", "is_income"]
    keep = [c for c in keep if c in df.columns]
    return df[keep].reset_index(drop=True)


def parse_patrimonio(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame()
    return raw.copy()
