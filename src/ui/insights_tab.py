from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.insights import category_ytd, opportunity_cost, total_savings_ytd


def _fmt_eur(x: float) -> str:
    return f"€ {x:,.0f}".replace(",", ".")


def render(eu_long: pd.DataFrame, log_df: pd.DataFrame) -> None:
    if eu_long.empty:
        st.info("Nessun dato.")
        return

    current_year = pd.Timestamp.today().year
    years_in_data = []
    if "month_dt" in eu_long.columns:
        years_in_data = sorted(eu_long["month_dt"].dropna().dt.year.unique().tolist())
    if not years_in_data:
        years_in_data = [current_year]
    selected_year = st.selectbox("Anno", options=years_in_data, index=len(years_in_data) - 1)

    summary = total_savings_ytd(eu_long, year=selected_year)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("💸 Entrate YTD", _fmt_eur(summary["entrate"]))
    with c2:
        st.metric("🛒 Uscite YTD", _fmt_eur(abs(summary["uscite"])))
    with c3:
        st.metric("💰 Risparmio YTD", _fmt_eur(summary["risparmio"]),
                  delta=f"{summary['pct'] * 100:+.1f}%")

    st.divider()
    st.subheader("🎲 Scommesse — il numero che meriti di vedere")

    scommesse_total = abs(category_ytd(eu_long, "Scommesse", year=selected_year))
    if scommesse_total > 0:
        opp_1y = opportunity_cost(scommesse_total)
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Speso YTD in Scommesse", _fmt_eur(scommesse_total))
        with c2:
            st.metric(
                "Se fossero stati nel PAC (1 anno @ 7%)",
                _fmt_eur(opp_1y),
                delta=_fmt_eur(opp_1y - scommesse_total),
            )
        st.caption(
            "Calcolo neutro: stesso importo, stesso periodo, rendimento storico medio mercato globale. "
            "Nessun giudizio — solo il numero."
        )
    else:
        st.success("Nessuna spesa in Scommesse YTD. 👏")

    st.divider()
    st.subheader("📊 Top categorie YTD")

    expenses = eu_long[~eu_long["is_income"]].copy()
    if "month_dt" in expenses.columns:
        expenses = expenses[expenses["month_dt"].dt.year == selected_year]
    expenses["amount_abs"] = expenses["amount"].abs()
    top = (
        expenses.groupby("category", as_index=False)["amount_abs"]
        .sum()
        .sort_values("amount_abs", ascending=False)
        .head(10)
    )
    if top.empty:
        st.caption("Nessuna uscita registrata per l'anno selezionato.")
        return

    fig = px.bar(
        top.sort_values("amount_abs"),
        x="amount_abs",
        y="category",
        orientation="h",
        labels={"amount_abs": "€ YTD", "category": ""},
        color="amount_abs",
        color_continuous_scale=["#1B1F2A", "#FF6B6B"],
    )
    fig.update_layout(height=420, margin=dict(t=20, b=10, l=10, r=10), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("🎯 Vuoi 300€/mese in più? Ecco dove possono arrivare")

    target_extra = st.slider("Risparmio extra mensile desiderato", 50, 1000, 300, step=50)
    st.write(
        f"Per liberare **{_fmt_eur(target_extra)}/mese**, riducendo del 30% le 3 categorie discrezionali "
        f"più alte YTD (Cibo fuori, Divertimento, Viaggi):"
    )
    discretional = ["Cibo fuori / Bevute", "Divertimento", "Viaggi", "Scommesse"]
    disc_df = expenses[expenses["category"].isin(discretional)].groupby("category", as_index=False)["amount_abs"].sum()
    disc_df["mensile"] = disc_df["amount_abs"] / max(1, expenses["month"].nunique())
    disc_df["taglio_30%"] = disc_df["mensile"] * 0.30
    disc_df["€/mese liberati con -30%"] = disc_df["taglio_30%"].apply(_fmt_eur)
    disc_df["Spesa media mensile"] = disc_df["mensile"].apply(_fmt_eur)
    st.dataframe(
        disc_df[["category", "Spesa media mensile", "€/mese liberati con -30%"]].rename(columns={"category": "Categoria"}),
        hide_index=True,
        use_container_width=True,
    )

    total_freed = disc_df["taglio_30%"].sum()
    if total_freed >= target_extra:
        st.success(f"✅ Tagliando del 30% queste 4 categorie liberi **{_fmt_eur(total_freed)}/mese** — copre il target.")
    else:
        st.info(f"Con -30% su queste 4 categorie liberi {_fmt_eur(total_freed)}/mese (target: {_fmt_eur(target_extra)}).")
