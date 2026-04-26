from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st


TARGET_PCT = 0.5


def _fmt_eur(x: float) -> str:
    return f"€ {x:,.0f}".replace(",", ".")


def _fmt_pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def _select_month(eu_long: pd.DataFrame) -> str:
    months = eu_long.dropna(subset=["month_dt"]).sort_values("month_dt")["month"].unique().tolist()
    if not months:
        st.warning("Nessun mese disponibile nei dati.")
        st.stop()
    return st.selectbox("Mese di riferimento", options=months, index=len(months) - 1)


def render(eu_long: pd.DataFrame, eu_summary: pd.DataFrame, log_df: pd.DataFrame) -> None:
    if eu_long.empty:
        st.info("Nessun dato nel foglio E/U.")
        return

    selected_month = _select_month(eu_long)
    month_data = eu_long[eu_long["month"] == selected_month]

    entrate = month_data[month_data["is_income"]]["amount"].sum()
    uscite_signed = month_data[~month_data["is_income"]]["amount"].sum()
    uscite_abs = abs(uscite_signed)
    risparmio = entrate + uscite_signed
    pct = risparmio / entrate if entrate else 0.0

    months_sorted = eu_long.dropna(subset=["month_dt"]).sort_values("month_dt")["month"].unique().tolist()
    idx = months_sorted.index(selected_month) if selected_month in months_sorted else 0
    prev_month = months_sorted[idx - 1] if idx > 0 else None

    delta_entrate = delta_uscite = delta_risp = None
    if prev_month is not None:
        prev_data = eu_long[eu_long["month"] == prev_month]
        prev_entrate = prev_data[prev_data["is_income"]]["amount"].sum()
        prev_uscite_signed = prev_data[~prev_data["is_income"]]["amount"].sum()
        delta_entrate = entrate - prev_entrate
        delta_uscite = abs(prev_uscite_signed) - uscite_abs
        delta_risp = (entrate + uscite_signed) - (prev_entrate + prev_uscite_signed)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(
            "💸 Entrate",
            _fmt_eur(entrate),
            delta=_fmt_eur(delta_entrate) if delta_entrate is not None else None,
        )
    with c2:
        st.metric(
            "🛒 Uscite",
            _fmt_eur(uscite_abs),
            delta=_fmt_eur(delta_uscite) if delta_uscite is not None else None,
            delta_color="normal" if (delta_uscite or 0) >= 0 else "inverse",
        )
    with c3:
        st.metric(
            "💰 Risparmio",
            _fmt_eur(risparmio),
            delta=_fmt_eur(delta_risp) if delta_risp is not None else None,
        )
    with c4:
        delta_target = pct - TARGET_PCT
        st.metric(
            "🎯 % Risparmio",
            _fmt_pct(pct),
            delta=f"{delta_target * 100:+.1f}p vs target",
            delta_color="normal" if delta_target >= 0 else "inverse",
        )

    if pct < TARGET_PCT and entrate > 0:
        gap = (TARGET_PCT - pct) * entrate
        st.caption(f"Per centrare il target 50%: **{_fmt_eur(gap)}** in meno di spese (o in più di entrate).")

    st.divider()

    monthly = (
        eu_long.dropna(subset=["month_dt"])
        .groupby(["month", "month_dt", "is_income"], as_index=False)["amount"]
        .sum()
    )
    monthly["amount_abs"] = monthly["amount"].abs()
    monthly["tipo"] = monthly["is_income"].map({True: "Entrate", False: "Uscite"})
    monthly = monthly.sort_values("month_dt")

    fig = px.bar(
        monthly,
        x="month",
        y="amount_abs",
        color="tipo",
        barmode="group",
        color_discrete_map={"Entrate": "#00C49A", "Uscite": "#FF6B6B"},
        labels={"amount_abs": "€", "month": "Mese", "tipo": ""},
        title="Entrate vs Uscite per mese",
    )
    fig.update_layout(height=350, margin=dict(t=40, b=10, l=10, r=10))
    st.plotly_chart(fig, use_container_width=True)

    saving_trend = (
        monthly.pivot(index="month", columns="tipo", values="amount_abs")
        .reset_index()
        .merge(
            eu_long.dropna(subset=["month_dt"])[["month", "month_dt"]].drop_duplicates(),
            on="month",
            how="left",
        )
        .sort_values("month_dt")
    )
    if {"Entrate", "Uscite"}.issubset(saving_trend.columns):
        saving_trend["pct"] = (saving_trend["Entrate"] - saving_trend["Uscite"]) / saving_trend["Entrate"].replace(0, pd.NA)
        saving_trend["pct"] = saving_trend["pct"].fillna(0)

        fig2 = px.line(
            saving_trend,
            x="month",
            y="pct",
            markers=True,
            labels={"pct": "% Risparmio", "month": ""},
            title="% Risparmio per mese (target 50%)",
        )
        fig2.add_hline(y=TARGET_PCT, line_dash="dot", line_color="#00C49A", annotation_text="Target 50%")
        fig2.update_yaxes(tickformat=".0%")
        fig2.update_layout(height=320, margin=dict(t=40, b=10, l=10, r=10))
        st.plotly_chart(fig2, use_container_width=True)
