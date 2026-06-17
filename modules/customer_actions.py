from __future__ import annotations

from datetime import date

import streamlit as st

from services.data_store import (
    listar_agendamentos,
    listar_historico_cliente,
    listar_observacoes,
    marcar_ja_liguei,
    salvar_agendamento,
    salvar_observacao,
)
from modules.ui import render_history


def render_customer_actions(cliente_id: str, origem: str, usuario_padrao: str = "") -> None:
    st.subheader("Ações compartilhadas")
    usuario = st.text_input("Usuário / vendedora", value=usuario_padrao, key=f"{origem}_{cliente_id}_usuario")

    col_obs, col_agenda, col_call = st.columns([1.2, 1.2, 0.8])
    with col_obs:
        with st.form(f"{origem}_{cliente_id}_obs_form", clear_on_submit=True):
            texto = st.text_area("Nova observação", height=100)
            submitted = st.form_submit_button("Salvar observação")
            if submitted and texto.strip():
                salvar_observacao(cliente_id, texto, origem, usuario)
                st.success("Observação salva e compartilhada.")
                st.rerun()

    with col_agenda:
        with st.form(f"{origem}_{cliente_id}_agenda_form", clear_on_submit=True):
            data = st.date_input("Data de retorno", value=date.today())
            hora = st.time_input("Hora")
            observacao = st.text_area("Observação do retorno", height=68)
            submitted = st.form_submit_button("Agendar retorno")
            if submitted:
                salvar_agendamento(cliente_id, data.isoformat(), hora.strftime("%H:%M"), observacao, origem, usuario)
                st.success("Agendamento salvo e compartilhado.")
                st.rerun()

    with col_call:
        st.write("")
        st.write("")
        if st.button("Já liguei", key=f"{origem}_{cliente_id}_ja_liguei"):
            marcar_ja_liguei(cliente_id, usuario, origem)
            st.success("Contato registrado.")
            st.rerun()

    render_history(
        listar_observacoes(cliente_id),
        listar_agendamentos(cliente_id),
        listar_historico_cliente(cliente_id),
    )
