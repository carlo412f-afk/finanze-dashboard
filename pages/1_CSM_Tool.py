from __future__ import annotations

import io

import pandas as pd
import plotly.express as px
import streamlit as st

from src.csm.engine import compute_ec_var
from src.csm.mkt_parser import get_delta, parse_mkt
from src.csm.sens_parser import load_both

st.set_page_config(page_title="CSM Tool", page_icon="📊", layout="wide")
st.title("📊 CSM / PVFP Economic Variance Tool")
st.caption("IFRS 17 VFA · SII — Sensitivity-based estimation · EUR mln")

# ── File upload ──────────────────────────────────────────────────────────────
uploaded = st.file_uploader(
    "Carica il file Excel (deve contenere SENS_IFRS17_VFA_YE25, SENS_SII_YE25, Econ_financial_assumptions)",
    type=["xlsx"],
)
if not uploaded:
    st.info("Carica il file per iniziare.")
    st.stop()

file_bytes = uploaded.read()

with st.spinner("Parsing..."):
    try:
        ifrs17_sens, sii_sens = load_both(file_bytes)
        mkt = parse_mkt(file_bytes)
    except Exception as e:
        st.error(f"Errore nel parsing: {e}")
        st.stop()

has_mkt = not mkt.empty

# ── Period ───────────────────────────────────────────────────────────────────
st.divider()
col_from, col_to = st.columns(2)
with col_from:
    date_from = pd.Timestamp(st.date_input("From", value=pd.Timestamp("2025-12-31")))
with col_to:
    date_to = pd.Timestamp(st.date_input("To", value=pd.Timestamp("2026-03-31")))

# ── Market deltas ─────────────────────────────────────────────────────────────
st.divider()
st.subheader("Movimenti di mercato")
st.caption("Auto-calcolati dal file se disponibili — modificabili manualmente.")

def _auto(var: str) -> float:
    if not has_mkt:
        return 0.0
    d = get_delta(mkt, var, date_from, date_to)
    return round(d * 10_000, 2) if d is not None else 0.0  # convert to bps

c1, c2, c3, c4 = st.columns(4)
with c1:
    ir_bps = st.number_input(
        "SWAP EUR 10y (Δbps)", value=_auto("SWAP EUR 10yrs par"), step=1.0,
        help="Variazione del tasso swap EUR 10 anni tra Start e End (in bps)",
    )
with c2:
    gov_bps = st.number_input(
        "Gov Spread (Δbps)", value=_auto("Spread ITA 10yrs"), step=1.0,
        help="Variazione media spread governativi (in bps)",
    )
with c3:
    corp_bps = st.number_input(
        "Corp Spread EUR (Δbps)", value=_auto("Implied Corp Spread EUR"), step=1.0,
        help="Variazione implied corp spread EUR (in bps)",
    )
with c4:
    eq_pct = st.number_input(
        "Equity (Δ%)", value=0.0, step=0.1,
        help="Movimento equity effettivo ponderato per portfolio Generali (%)",
    )

delta_ir   = ir_bps   / 10_000
delta_gov  = gov_bps  / 10_000
delta_corp = corp_bps / 10_000
delta_eq   = eq_pct   / 100

# ── Compute ──────────────────────────────────────────────────────────────────
ec_ifrs17 = compute_ec_var(ifrs17_sens, delta_ir, delta_gov, delta_corp, delta_eq)
ec_sii    = compute_ec_var(sii_sens,    delta_ir, delta_gov, delta_corp, delta_eq)

# ── Output ───────────────────────────────────────────────────────────────────
def _show_results(title: str, ec: pd.DataFrame) -> None:
    st.subheader(title)
    if ec.empty:
        st.warning("Nessun dato — verifica il parsing del file sensi.")
        return

    numeric_cols = [c for c in ec.columns if c != "Ec. Var."]
    total_row = ec.sum(numeric_only=True).rename("TOTAL")
    display = pd.concat([ec, total_row.to_frame().T])
    st.dataframe(
        display.style.format("{:.2f}", na_rep="—")
               .applymap(lambda v: "color: #FF6B6B" if isinstance(v, float) and v < 0 else
                                   "color: #00C49A" if isinstance(v, float) and v > 0 else ""),
        use_container_width=True,
    )

    # Waterfall of Ec. Var. by entity (top 10 non-zero)
    plot_df = ec[["Ec. Var."]].reset_index()
    plot_df = plot_df[plot_df["Ec. Var."] != 0].sort_values("Ec. Var.")
    if not plot_df.empty:
        fig = px.bar(
            plot_df, x="Ec. Var.", y="Entity", orientation="h",
            color="Ec. Var.",
            color_continuous_scale=["#FF6B6B", "#1B1F2A", "#00C49A"],
            color_continuous_midpoint=0,
            labels={"Ec. Var.": "Ec. Var. (EUR mln)"},
        )
        fig.add_vline(x=0, line_width=1, line_color="white")
        fig.update_layout(height=max(300, 28 * len(plot_df)), margin=dict(t=20, b=10))
        st.plotly_chart(fig, use_container_width=True)

    # Factor breakdown for TOTAL
    factor_cols = [c for c in ec.columns if c != "Ec. Var."]
    factor_totals = ec[factor_cols].sum()
    factor_df = factor_totals.reset_index()
    factor_df.columns = ["Factor", "EUR mln"]
    factor_df = factor_df[factor_df["EUR mln"] != 0]
    if not factor_df.empty:
        fig2 = px.bar(
            factor_df, x="Factor", y="EUR mln",
            color="EUR mln",
            color_continuous_scale=["#FF6B6B", "#1B1F2A", "#00C49A"],
            color_continuous_midpoint=0,
            title="Decomposizione per fattore di rischio (Group total)",
        )
        fig2.add_hline(y=0, line_width=1, line_color="white")
        fig2.update_layout(height=320, margin=dict(t=40, b=10))
        st.plotly_chart(fig2, use_container_width=True)


st.divider()
tab_ifrs, tab_sii = st.tabs(["IFRS 17 VFA — CSM", "SII — PVFP"])
with tab_ifrs:
    _show_results("Varianza economica su CSM (IFRS 17 VFA)", ec_ifrs17)
with tab_sii:
    _show_results("Varianza economica su PVFP (SII)", ec_sii)
