from __future__ import annotations

import streamlit as st

from modules import base_clientes, churn, configuracoes, crm, dashboard_ceo, gerador_orcamentos, portal_vendedoras, relatorios
from modules.ui import apply_ceo_style
from services.data_store import init_db


st.set_page_config(
    page_title="Novaprint | Plataforma Comercial",
    page_icon="NP",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()
apply_ceo_style()

st.sidebar.title("Novaprint")
st.sidebar.caption("Plataforma comercial integrada")

PAGES = {
    "Dashboard CEO": dashboard_ceo.render,
    "CRM": crm.render,
    "Portal das Vendedoras": portal_vendedoras.render,
    "Gerador de Orçamentos": gerador_orcamentos.render,
    "Relatórios": relatorios.render,
    "Churn": churn.render,
    "Base de Clientes": base_clientes.render,
    "Configurações": configuracoes.render,
}

selected = st.sidebar.radio("Escolha a plataforma", list(PAGES.keys()))
st.sidebar.divider()
st.sidebar.caption("Dados compartilhados: SQLite local.")

PAGES[selected]()
