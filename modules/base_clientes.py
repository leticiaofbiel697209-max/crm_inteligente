from __future__ import annotations

import streamlit as st

from services.data_store import listar_clientes, listar_ja_liguei
from modules.customer_actions import render_customer_actions
from modules.ui import client_selector, dataframe, page_title


def render() -> None:
    clientes = listar_clientes()
    page_title("Base de Clientes", "Base completa com status, responsável, próxima ação e registros compartilhados.")

    busca = st.text_input("Buscar cliente")
    base = clientes
    if busca.strip():
        termo = busca.lower().strip()
        base = [c for c in clientes if termo in c["nome"].lower() or termo in c["cliente_id"].lower()]

    dataframe(base)
    st.subheader("Status Já liguei")
    dataframe(listar_ja_liguei())

    cliente_id = client_selector(base or clientes, "Cliente para atualizar")
    render_customer_actions(cliente_id, "Base de Clientes")
