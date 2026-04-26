from __future__ import annotations

import json
from pathlib import Path

import streamlit as st


CONFIG_PATH = Path("config/patrimonio.json")

DEFAULT_PATRIMONIO: dict[str, float] = {
    "Liquidità": 0.0,
    "PAC / Fondi comuni": 0.0,
    "Azioni": 0.0,
    "Crypto": 0.0,
    "Fondi pensione / TFR": 0.0,
    "Immobili": 0.0,
    "Altro": 0.0,
}


def load_patrimonio_manual() -> dict[str, float]:
    if "patrimonio_manual" in st.session_state:
        return dict(st.session_state["patrimonio_manual"])
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            merged = {**DEFAULT_PATRIMONIO, **{k: float(v) for k, v in data.items()}}
            st.session_state["patrimonio_manual"] = merged
            return merged
        except (ValueError, OSError):
            pass
    st.session_state["patrimonio_manual"] = dict(DEFAULT_PATRIMONIO)
    return dict(DEFAULT_PATRIMONIO)


def save_patrimonio_manual(values: dict[str, float]) -> None:
    st.session_state["patrimonio_manual"] = dict(values)
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(values, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        pass
