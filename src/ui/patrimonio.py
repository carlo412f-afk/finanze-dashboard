from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.patrimonio_config import DEFAULT_PATRIMONIO, load_patrimonio_manual, save_patrimonio_manual


def _fmt_eur(x: float) -> str:
    return f"€ {x:,.0f}".replace(",", ".")


def render() -> None:
    patr = load_patrimonio_manual()

    liquidita = patr.get("Liquidità", 0.0)
    invest = sum(
        v for k, v in patr.items()
        if k not in ("Liquidità", "Fondi pensione / TFR", "Immobili")
    )
    totale = sum(patr.values())

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("💵 Liquidità", _fmt_eur(liquidita))
    with c2:
        st.metric("📈 Investimenti", _fmt_eur(invest))
    with c3:
        st.metric("🏦 Patrimonio netto", _fmt_eur(totale))

    st.divider()

    plot_df = pd.DataFrame(
        [{"Asset": k, "Valore": v} for k, v in patr.items() if v != 0]
    )
    if not plot_df.empty:
        fig = px.pie(plot_df, values="Valore", names="Asset", title="Asset allocation", hole=0.4)
        fig.update_layout(height=380, margin=dict(t=40, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Inserisci i valori del tuo patrimonio qui sotto per vedere l'allocation.")

    st.divider()
    st.subheader("⚙️ Aggiorna il tuo patrimonio")
    st.caption("Valori salvati localmente in `config/patrimonio.json`.")

    with st.form("patrimonio_form"):
        new_patr: dict[str, float] = {}
        cols = st.columns(3)
        for i, (k, default) in enumerate(DEFAULT_PATRIMONIO.items()):
            with cols[i % 3]:
                new_patr[k] = st.number_input(
                    k,
                    value=float(patr.get(k, default)),
                    step=100.0,
                    format="%.0f",
                    key=f"patr_{k}",
                )
        submitted = st.form_submit_button("💾 Salva patrimonio", type="primary")
        if submitted:
            save_patrimonio_manual(new_patr)
            st.success("Patrimonio salvato.")
            st.rerun()
