from __future__ import annotations

import streamlit as st

from services.data_store import listar_clientes, listar_orcamentos, obter_cliente
from modules.customer_actions import render_customer_actions
from modules.crm_pro import render as render_crm_pro
from modules.ui import client_selector, dataframe, money, page_title


def render() -> None:
    tab_integrado, tab_pro = st.tabs(["CRM Integrado", "CRM Pro"])
    with tab_integrado:
        render_integrado()
    with tab_pro:
        render_crm_pro()


def render_integrado() -> None:
    clientes = listar_clientes()
    page_title("CRM Inteligente", "Carteira, risco, histórico do cliente e ações comerciais compartilhadas.")

    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        status = st.multiselect("Status", sorted({c["status"] for c in clientes}), default=sorted({c["status"] for c in clientes}))
    with col_filter2:
        responsaveis = st.multiselect("Responsável", sorted({c["responsavel"] for c in clientes}), default=sorted({c["responsavel"] for c in clientes}))

    filtrados = [c for c in clientes if c["status"] in status and c["responsavel"] in responsaveis]
    dataframe(filtrados)

    cliente_id = client_selector(filtrados or clientes, "Abrir histórico do cliente")
    cliente = obter_cliente(cliente_id)
    if not cliente:
        st.warning("Cliente não encontrado.")
        return

    st.subheader(cliente["nome"])
    cols = st.columns(5)
    cols[0].metric("Status", cliente["status"])
    cols[1].metric("Score de risco", cliente["score_risco"])
    cols[2].metric("Potencial mensal", money(float(cliente["valor_mensal"])))
    cols[3].metric("Potencial recuperável", money(float(cliente["potencial_recuperavel"])))
    cols[4].metric("Responsável", cliente["responsavel"])

    st.markdown("**IA sugerindo abordagem**")
    if int(cliente["score_risco"]) >= 70:
        st.info("Priorize contato consultivo, valide motivo de queda e ofereça uma condição de retorno com prazo curto.")
    elif cliente["status"] == "Ativo":
        st.info("Cliente ativo: conduza conversa de recompra, destaque previsibilidade e proponha pacote mensal.")
    else:
        st.info("Cliente em atenção: combine diagnóstico rápido com proposta objetiva para destravar a decisão.")

    st.subheader("Orçamentos vinculados")
    dataframe(listar_orcamentos(cliente_id))
    render_customer_actions(cliente_id, "CRM", cliente["responsavel"])
