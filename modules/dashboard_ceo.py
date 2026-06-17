from __future__ import annotations

import pandas as pd
import streamlit as st

from services.data_store import listar_agendamentos, listar_clientes, listar_orcamentos
from modules.ui import dataframe, metric_row, money, page_title


def render() -> None:
    clientes = listar_clientes()
    orcamentos = listar_orcamentos()
    agendamentos = listar_agendamentos()

    page_title("Dashboard CEO", "Visão executiva integrada da operação comercial Novaprint.")
    metric_row(clientes, orcamentos)

    st.subheader("Resumo diário")
    col1, col2 = st.columns(2)
    with col1:
        proximos = sorted(clientes, key=lambda c: c["ultima_compra"], reverse=True)[:5]
        st.markdown('<div class="np-card"><span class="np-badge">Clientes próximos da recompra</span></div>', unsafe_allow_html=True)
        dataframe(proximos)
    with col2:
        inativos = [c for c in clientes if c["status"] in {"Inativo", "Churn"} or int(c["score_risco"]) >= 70]
        st.markdown('<div class="np-card"><span class="np-badge">Clientes inativos / risco alto</span></div>', unsafe_allow_html=True)
        dataframe(inativos)

    st.subheader("Potencial mensal e recuperável")
    chart_df = pd.DataFrame(
        {
            "Cliente": [c["nome"] for c in clientes],
            "Potencial mensal": [float(c["valor_mensal"]) for c in clientes],
            "Potencial recuperável": [float(c["potencial_recuperavel"]) for c in clientes],
        }
    ).set_index("Cliente")
    st.bar_chart(chart_df)

    total_mensal = sum(float(c["valor_mensal"]) for c in clientes)
    st.info(f"Potencial mensal total: {money(total_mensal)}")

    st.subheader("Agendamentos de retorno")
    dataframe(agendamentos)
