from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.mortgage import monthly_payment, total_interest, upfront_costs
from src.patrimonio_config import load_patrimonio_manual


def _fmt_eur(x: float) -> str:
    return f"€ {x:,.0f}".replace(",", ".")


def _avg_monthly_income(eu_long: pd.DataFrame) -> float:
    if eu_long.empty or "is_income" not in eu_long.columns:
        return 0.0
    per_month = (
        eu_long[eu_long["is_income"]]
        .groupby("month")["amount"]
        .sum()
    )
    non_zero = per_month[per_month > 0]
    return float(non_zero.mean()) if not non_zero.empty else 0.0


def render(eu_long: pd.DataFrame) -> None:
    patr = load_patrimonio_manual()
    liquidita = patr.get("Liquidità", 0.0)
    patrimonio_totale = sum(patr.values())

    col_params, col_reddito = st.columns([3, 1])

    with col_params:
        prezzo = st.slider("Prezzo immobile (€)", 50_000, 1_000_000, 300_000, step=5_000)
        anticipo_pct = st.slider("Anticipo (%)", 10, 50, 20, step=5)
        tasso = st.slider("Tasso fisso annuo (%)", 1.0, 8.0, 3.5, step=0.1, format="%.1f%%")
        durata = st.slider("Durata mutuo (anni)", 5, 30, 25, step=5)
        prima_casa = st.toggle("Prima casa", value=True)

    with col_reddito:
        avg_inc = _avg_monthly_income(eu_long)
        reddito = st.number_input(
            "Reddito netto mensile (€)",
            min_value=0.0,
            value=round(avg_inc) if avg_inc > 0 else 2000.0,
            step=100.0,
            help="Pre-compilato dalla media dei mesi con stipendio. Modificalo se necessario.",
        )

    loan = prezzo * (1 - anticipo_pct / 100)
    anticipo_eur = prezzo * anticipo_pct / 100
    rata = monthly_payment(loan, tasso, durata)
    interessi = total_interest(loan, tasso, durata)
    costs = upfront_costs(prezzo, prima_casa)
    costi_acc = sum(costs.values())
    liquidita_necessaria = anticipo_eur + costi_acc
    rapporto = rata / reddito if reddito > 0 else 0.0

    st.divider()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("🏦 Importo mutuo", _fmt_eur(loan))
    with c2:
        st.metric("📅 Rata mensile", _fmt_eur(rata))
    with c3:
        st.metric("💸 Totale interessi", _fmt_eur(interessi))
    with c4:
        st.metric("🏷️ Costo totale", _fmt_eur(prezzo + interessi + costi_acc))

    st.divider()

    col_liq, col_rata = st.columns(2)

    with col_liq:
        st.subheader("💰 Liquidità necessaria upfront")
        rows = [{"Voce": "Anticipo", "Importo": _fmt_eur(anticipo_eur)}]
        for k, v in costs.items():
            rows.append({"Voce": k, "Importo": _fmt_eur(v)})
        rows.append({"Voce": "TOTALE", "Importo": _fmt_eur(liquidita_necessaria)})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

        delta = liquidita - liquidita_necessaria
        if delta >= 0:
            st.success(f"✅ Liquidità sufficiente — avanzo {_fmt_eur(delta)}")
        else:
            st.error(f"🚨 Liquidità mancante: {_fmt_eur(abs(delta))}")
            if patrimonio_totale >= liquidita_necessaria:
                st.info(
                    f"💡 Liquidando parte degli investimenti potresti coprirla "
                    f"(patrimonio totale: {_fmt_eur(patrimonio_totale)})"
                )
        st.caption(
            f"Patrimonio inserito — Liquidità: {_fmt_eur(liquidita)} | "
            f"Totale: {_fmt_eur(patrimonio_totale)}"
        )

    with col_rata:
        st.subheader("📊 Sostenibilità della rata")

        if rapporto <= 0.30:
            colore = "#00C49A"
            label = "✅ Sostenibile (< 30%)"
            fn = st.success
        elif rapporto <= 0.35:
            colore = "#F4D35E"
            label = "⚠️ Al limite (30–35%)"
            fn = st.warning
        else:
            colore = "#FF6B6B"
            label = "🚨 Oltre la soglia (> 35%)"
            fn = st.error
        fn(f"{label} — rata/reddito: {rapporto * 100:.1f}%")

        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=rapporto * 100,
            number={"suffix": "%", "font": {"size": 32}},
            gauge={
                "axis": {"range": [0, 60], "ticksuffix": "%"},
                "bar": {"color": colore},
                "steps": [
                    {"range": [0, 30], "color": "#1B2E2E"},
                    {"range": [30, 35], "color": "#2E2B1B"},
                    {"range": [35, 60], "color": "#2E1B1B"},
                ],
                "threshold": {
                    "line": {"color": "#FF6B6B", "width": 2},
                    "thickness": 0.75,
                    "value": 35,
                },
            },
            title={"text": "Rata / Reddito mensile"},
        ))
        fig.update_layout(height=260, margin=dict(t=30, b=10, l=20, r=20))
        st.plotly_chart(fig, use_container_width=True)
