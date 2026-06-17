from __future__ import annotations

import pandas as pd
import streamlit as st

from services.data_store import listar_agendamentos, listar_clientes, listar_ja_liguei, listar_orcamentos
from modules.ui import dataframe, money, page_title


def render() -> None:
    clientes = listar_clientes()
    orcamentos = listar_orcamentos()
    agendamentos = listar_agendamentos()
    ligacoes = listar_ja_liguei()

    page_title("Relatórios", "Relatórios comerciais, clientes, orçamentos, churn, base e métricas do CEO.")

    tabs = st.tabs(["Comercial", "Clientes", "Orçamentos", "Churn", "Base", "Métricas CEO"])
    with tabs[0]:
        st.metric("Pipeline total", money(sum(float(o["valor"]) for o in orcamentos)))
        dataframe(orcamentos)
    with tabs[1]:
        dataframe(clientes)
    with tabs[2]:
        por_situacao = pd.DataFrame(orcamentos).groupby("situacao", as_index=False)["valor"].sum() if orcamentos else pd.DataFrame()
        dataframe(por_situacao.to_dict("records") if not por_situacao.empty else [])
        dataframe(orcamentos)
    with tabs[3]:
        dataframe([c for c in clientes if c["status"] == "Churn" or int(c["score_risco"]) >= 70])
    with tabs[4]:
        dataframe(clientes)
        st.write("Contatos realizados")
        dataframe(ligacoes)
    with tabs[5]:
        cols = st.columns(4)
        cols[0].metric("Clientes", len(clientes))
        cols[1].metric("Agendamentos", len(agendamentos))
        cols[2].metric("Orçamentos", len(orcamentos))
        cols[3].metric("Já liguei", len(ligacoes))
