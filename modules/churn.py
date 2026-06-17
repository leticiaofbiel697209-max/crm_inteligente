from __future__ import annotations

import streamlit as st

from services.data_store import listar_clientes
from modules.customer_actions import render_customer_actions
from modules.ui import client_selector, dataframe, money, page_title


def render() -> None:
    clientes = listar_clientes()
    page_title("Churn", "Relatório de clientes em risco com próxima ação, responsável e histórico compartilhado.")

    churn = [c for c in clientes if c["status"] == "Churn" or int(c["score_risco"]) >= 70]
    cols = st.columns(3)
    cols[0].metric("Clientes em churn/alto risco", len(churn))
    cols[1].metric("Potencial recuperável", money(sum(float(c["potencial_recuperavel"]) for c in churn)))
    cols[2].metric("Score médio", round(sum(int(c["score_risco"]) for c in churn) / max(len(churn), 1), 1))

    dataframe(churn)
    cliente_id = client_selector(churn or clientes, "Cliente para ação de churn")
    render_customer_actions(cliente_id, "Churn")
