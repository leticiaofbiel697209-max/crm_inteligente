from __future__ import annotations

from datetime import date

import streamlit as st

from services.data_store import listar_clientes, listar_orcamentos, salvar_orcamento
from modules.ui import client_selector, dataframe, page_title


def render() -> None:
    clientes = listar_clientes()
    page_title("Gerador de Orçamentos", "Cadastro de orçamentos vinculado ao cliente e ao histórico comercial.")

    with st.form("novo_orcamento", clear_on_submit=True):
        cliente_id = client_selector(clientes)
        col1, col2, col3 = st.columns(3)
        numero = col1.text_input("Número do orçamento")
        data_orcamento = col2.date_input("Data", value=date.today())
        valor = col3.number_input("Valor", min_value=0.0, step=100.0)
        col4, col5 = st.columns(2)
        situacao = col4.selectbox("Situação", ["Em negociação", "Sem retorno", "Pendente", "Aprovado", "Perdido"])
        responsavel = col5.text_input("Responsável")
        observacoes = st.text_area("Observações / histórico de follow-up")
        submitted = st.form_submit_button("Salvar orçamento")
        if submitted and numero.strip():
            salvar_orcamento(cliente_id, numero, data_orcamento.isoformat(), valor, situacao, responsavel, observacoes)
            st.success("Orçamento salvo e vinculado ao cliente.")
            st.rerun()

    st.subheader("Orçamentos cadastrados")
    dataframe(listar_orcamentos())
