from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.budget import DEFAULT_BUDGETS, load_budgets, save_budgets


def render(eu_long: pd.DataFrame) -> None:
    if eu_long.empty:
        st.info("Nessun dato.")
        return

    budgets = load_budgets()

    expenses = eu_long[~eu_long["is_income"]].copy()
    expenses["amount_abs"] = expenses["amount"].abs()

    months = expenses.dropna(subset=["month_dt"]).sort_values("month_dt")["month"].unique().tolist()
    selected = st.selectbox("Mese", options=months, index=len(months) - 1)

    month_df = expenses[expenses["month"] == selected]
    actual_by_cat = month_df.groupby("category", as_index=False)["amount_abs"].sum()

    rows = []
    for cat in sorted(set(list(budgets.keys()) + actual_by_cat["category"].tolist())):
        actual = float(actual_by_cat[actual_by_cat["category"] == cat]["amount_abs"].sum())
        budget = float(budgets.get(cat, 0))
        pct = (actual / budget) if budget > 0 else 0.0
        status = "✅" if pct < 0.8 else ("⚠️" if pct < 1.0 else "🚨")
        rows.append({
            "Categoria": cat,
            "Speso": actual,
            "Budget": budget,
            "%": pct,
            "Stato": status,
        })
    df = pd.DataFrame(rows)

    over_budget = df[df["%"] > 1.0]
    near_budget = df[(df["%"] >= 0.8) & (df["%"] <= 1.0)]
    if not over_budget.empty:
        labels = ", ".join(over_budget["Categoria"].tolist())
        st.error(f"🚨 Sopra budget: {labels}")
    elif not near_budget.empty:
        labels = ", ".join(near_budget["Categoria"].tolist())
        st.warning(f"⚠️ Vicino al limite: {labels}")
    else:
        st.success("✅ Tutte le categorie sotto budget.")

    plot_df = df[df["Budget"] > 0].copy().sort_values("%", ascending=True)
    fig = px.bar(
        plot_df,
        y="Categoria",
        x="%",
        orientation="h",
        labels={"%": "% budget consumato"},
        title=f"% budget consumato — {selected}",
        color="%",
        color_continuous_scale=["#00C49A", "#F4D35E", "#FF6B6B"],
        range_color=[0, 1.5],
    )
    fig.add_vline(x=1.0, line_dash="dot", line_color="#FF6B6B")
    fig.update_layout(height=max(350, 30 * len(plot_df)), margin=dict(t=40, b=10, l=10, r=10))
    fig.update_xaxes(tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("⚙️ Configura i tuoi target")
    st.caption("Modifica i budget mensili per categoria. Salvati localmente nel file `config/budgets.json`.")

    with st.form("budget_form"):
        new_budgets: dict[str, float] = {}
        cols = st.columns(3)
        cats = sorted(set(list(DEFAULT_BUDGETS.keys()) + actual_by_cat["category"].tolist()))
        for i, cat in enumerate(cats):
            with cols[i % 3]:
                new_budgets[cat] = st.number_input(
                    cat,
                    min_value=0.0,
                    step=10.0,
                    value=float(budgets.get(cat, DEFAULT_BUDGETS.get(cat, 0))),
                    key=f"budget_{cat}",
                )
        submitted = st.form_submit_button("💾 Salva budget", type="primary")
        if submitted:
            save_budgets(new_budgets)
            st.success("Budget salvati.")
            st.rerun()
