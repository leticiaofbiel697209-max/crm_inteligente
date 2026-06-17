from __future__ import annotations

import streamlit as st

from services.data_store import listar_agendamentos, listar_clientes, listar_orcamentos
from modules.customer_actions import render_customer_actions
from modules.ui import client_selector, dataframe, page_title


def render() -> None:
    clientes = listar_clientes()
    vendedoras = sorted({c["vendedora"] for c in clientes})
    page_title("Portal das Vendedoras", "Carteira, oportunidades, retornos e registros sincronizados com o CRM.")

    vendedora = st.selectbox("Vendedora", vendedoras)
    carteira = [c for c in clientes if c["vendedora"] == vendedora]
    orcamentos = [o for o in listar_orcamentos() if o["responsavel"] == vendedora]
    retornos = [a for a in listar_agendamentos() if a["vendedora"] == vendedora or a["responsavel"] == vendedora]

    tabs = st.tabs(["Minha carteira", "Clientes para ligar", "Orçamentos sem retorno", "Oportunidades quentes", "Retornos agendados"])
    with tabs[0]:
        dataframe(carteira)
    with tabs[1]:
        dataframe([c for c in carteira if int(c["score_risco"]) >= 45 or c["status"] != "Ativo"])
    with tabs[2]:
        dataframe([o for o in orcamentos if o["situacao"] in {"Sem retorno", "Pendente"}])
    with tabs[3]:
        dataframe([c for c in carteira if float(c["potencial_recuperavel"]) >= 15000])
    with tabs[4]:
        dataframe(retornos)

    cliente_id = client_selector(carteira or clientes, "Registrar ação para cliente")
    render_customer_actions(cliente_id, "Portal das Vendedoras", vendedora)
