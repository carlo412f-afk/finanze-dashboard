from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st


SILVIA_KEYWORDS = {"silvia"}


def _is_silvia(cat: str) -> bool:
    return cat.lower().strip() in SILVIA_KEYWORDS


def render(eu_long: pd.DataFrame, log_df: pd.DataFrame) -> None:
    if eu_long.empty:
        st.info("Nessun dato.")
        return

    expenses = eu_long[~eu_long["is_income"]].copy()
    expenses["amount_abs"] = expenses["amount"].abs()
    expenses_personali = expenses[~expenses["category"].apply(_is_silvia)]
    expenses_silvia = expenses[expenses["category"].apply(_is_silvia)]

    section, _ = st.columns([2, 5])
    with section:
        view = st.radio(
            "Vista",
            options=["Personali", "Silvia (separato)", "Tutto"],
            horizontal=True,
            label_visibility="collapsed",
        )

    if view == "Silvia (separato)":
        df = expenses_silvia
    elif view == "Tutto":
        df = expenses
    else:
        df = expenses_personali

    if df.empty:
        st.info("Nessuna spesa per questa vista.")
        return

    df = df.dropna(subset=["month_dt"]).sort_values("month_dt")

    fig = px.bar(
        df,
        x="month",
        y="amount_abs",
        color="category",
        labels={"amount_abs": "€", "month": "", "category": ""},
        title=f"Spese mensili per categoria — {view}",
    )
    fig.update_layout(height=480, margin=dict(t=40, b=10, l=10, r=10), legend_title_text="")
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    months = df["month"].unique().tolist()
    selected = st.selectbox("Drill-down su mese", options=months, index=len(months) - 1)
    month_df = df[df["month"] == selected].sort_values("amount_abs", ascending=False)

    c1, c2 = st.columns([1, 1])
    with c1:
        st.subheader(f"Top categorie — {selected}")
        top = month_df.head(10).copy()
        top["€"] = top["amount_abs"].apply(lambda x: f"{x:,.0f}".replace(",", "."))
        st.dataframe(
            top[["category", "€"]].rename(columns={"category": "Categoria"}),
            hide_index=True,
            use_container_width=True,
        )
    with c2:
        fig2 = px.pie(
            month_df,
            values="amount_abs",
            names="category",
            title=f"Distribuzione — {selected}",
            hole=0.4,
        )
        fig2.update_layout(height=400, margin=dict(t=40, b=10, l=10, r=10))
        st.plotly_chart(fig2, use_container_width=True)

    if not log_df.empty and "categoria" in log_df.columns:
        st.divider()
        st.subheader("Sottocategorie (da log transazioni)")
        last_month = log_df["mese"].max()
        last_log = log_df[log_df["mese"] == last_month]
        if not last_log.empty:
            sub = (
                last_log[~last_log["is_income"]]
                .groupby(["categoria", "sottocategoria"], as_index=False)["importo"]
                .sum()
                .sort_values("importo", ascending=False)
                .head(15)
            )
            sub["€"] = sub["importo"].apply(lambda x: f"{x:,.0f}".replace(",", "."))
            st.dataframe(
                sub[["categoria", "sottocategoria", "€"]],
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.caption("Nessuna transazione nel mese più recente del log.")
