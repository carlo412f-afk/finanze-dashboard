from __future__ import annotations

import json
from pathlib import Path

import streamlit as st


CONFIG_PATH = Path("config/budgets.json")


DEFAULT_BUDGETS: dict[str, float] = {
    "Supermercato": 150.0,
    "Cibo fuori / Bevute": 200.0,
    "Casa": 400.0,
    "Auto": 150.0,
    "Viaggi": 300.0,
    "Divertimento": 150.0,
    "Sport": 80.0,
    "Salute": 80.0,
    "Cura / Benessere": 50.0,
    "Cultura": 50.0,
    "Abbigliamento": 100.0,
    "Abbonamenti": 90.0,
    "Tecnologia": 100.0,
    "Trasporto pubblico": 50.0,
    "Regali": 60.0,
    "Altro": 50.0,
    "Scommesse": 30.0,
    "Silvia": 100.0,
}


def load_budgets() -> dict[str, float]:
    if "budgets" in st.session_state:
        return dict(st.session_state["budgets"])

    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            merged = {**DEFAULT_BUDGETS, **{k: float(v) for k, v in data.items()}}
            st.session_state["budgets"] = merged
            return merged
        except (ValueError, OSError):
            pass

    st.session_state["budgets"] = dict(DEFAULT_BUDGETS)
    return dict(DEFAULT_BUDGETS)


def save_budgets(budgets: dict[str, float]) -> None:
    st.session_state["budgets"] = dict(budgets)
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(budgets, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        pass
