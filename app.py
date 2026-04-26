import streamlit as st

from src.loader import get_loader, has_service_account
from src.ui import budget_tab, insights_tab, overview, patrimonio, spese


st.set_page_config(
    page_title="Finanze - Carlo",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main() -> None:
    with st.sidebar:
        st.markdown("## 💰 Finanze")
        st.caption("Dati da *Situazione patrimoniale - CS*")

        has_sa = has_service_account()
        default_mock = not has_sa
        use_mock = st.toggle(
            "Usa dati mock",
            value=default_mock,
            help="Disattiva per leggere dal Google Sheet reale (richiede secrets configurati).",
        )

        if not has_sa and not use_mock:
            st.warning("Service Account non configurato — torno ai dati mock.")
            use_mock = True

        if st.button("🔄 Ricarica dati", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.divider()
        st.caption(f"Sorgente: {'mock' if use_mock else 'Google Sheets'}")

    loader = get_loader(use_mock=use_mock)

    try:
        eu_long, eu_summary = loader.load_eu()
        log_df = loader.load_log()
        patrimonio_df = loader.load_patrimonio()
    except Exception as e:
        st.error(f"Errore nel caricamento dati: {e}")
        st.info(
            "Se hai appena configurato il Service Account, controlla che il foglio sia stato "
            "condiviso con l'email del SA come *Lettore*."
        )
        st.stop()

    tabs = st.tabs([
        "📊 Overview",
        "🏷️ Spese per categoria",
        "🎯 Budget & Target",
        "🏦 Patrimonio",
        "💡 Insights",
    ])

    with tabs[0]:
        overview.render(eu_long, eu_summary, log_df)
    with tabs[1]:
        spese.render(eu_long, log_df)
    with tabs[2]:
        budget_tab.render(eu_long)
    with tabs[3]:
        patrimonio.render(patrimonio_df)
    with tabs[4]:
        insights_tab.render(eu_long, log_df)


if __name__ == "__main__":
    main()
