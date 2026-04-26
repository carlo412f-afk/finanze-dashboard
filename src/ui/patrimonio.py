from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st


def _fmt_eur(x: float) -> str:
    return f"€ {x:,.0f}".replace(",", ".")


def render(patr_df: pd.DataFrame) -> None:
    if patr_df.empty:
        st.info("Foglio Patrimonio vuoto.")
        return

    if "asset_class" in patr_df.columns and "value" in patr_df.columns:
        df = patr_df.copy()
    else:
        df = _try_extract(patr_df)
        if df.empty:
            st.warning(
                "Non riesco a interpretare la struttura del foglio Patrimonio. "
                "Probabilmente formule rotte (lo hai detto tu). "
                "Sospeso fino a quando non lo sistemi."
            )
            with st.expander("Dati raw"):
                st.dataframe(patr_df, use_container_width=True)
            return

    df["value"] = pd.to_numeric(df["value"], errors="coerce").fillna(0.0)
    totale = df["value"].sum()

    c1, c2, c3 = st.columns(3)
    with c1:
        liquidita = df[df["asset_class"].str.lower().str.contains("liquid", na=False)]["value"].sum()
        st.metric("💵 Liquidità", _fmt_eur(liquidita))
    with c2:
        invest = df[~df["asset_class"].str.lower().str.contains("liquid|fondi pension", na=False)]["value"].sum()
        st.metric("📈 Investimenti", _fmt_eur(invest))
    with c3:
        st.metric("🏦 Patrimonio netto", _fmt_eur(totale))

    st.divider()

    plot_df = df[df["value"] != 0].copy()
    if plot_df.empty:
        st.info("Tutti gli asset a zero — il foglio Patrimonio non è ancora popolato.")
        return

    fig = px.pie(
        plot_df,
        values="value",
        names="asset_class",
        title="Asset allocation",
        hole=0.4,
    )
    fig.update_layout(height=400, margin=dict(t=40, b=10, l=10, r=10))
    st.plotly_chart(fig, use_container_width=True)

    st.caption("📌 Andamento patrimonio nel tempo: sospeso (richiede snapshot mensili). Riprenderemo quando sistemerai il foglio Patrimonio in Excel.")


def _try_extract(raw: pd.DataFrame) -> pd.DataFrame:
    """Best-effort extraction from raw Sheet 'Patrimonio' tab."""
    if raw.empty:
        return pd.DataFrame()
    df = raw.copy()
    df.columns = [str(c).strip() for c in df.columns]

    asset_col = next((c for c in df.columns if "asset" in c.lower() or "categoria" in c.lower()), None)
    value_col = next((c for c in df.columns if "controvalore" in c.lower() or "valore" in c.lower()), None)

    if asset_col is None or value_col is None:
        return pd.DataFrame()

    sub = df[[asset_col, value_col]].rename(columns={asset_col: "asset_class", value_col: "value"})
    sub = sub[sub["asset_class"].astype(str).str.strip().ne("")]
    sub = sub[~sub["asset_class"].astype(str).str.contains("#N/A|#REF|#DIV", na=False)]
    return sub.reset_index(drop=True)
