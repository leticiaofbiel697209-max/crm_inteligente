from __future__ import annotations

import streamlit as st

from services.data_store import DB_PATH, init_db
from modules.ui import page_title


def render() -> None:
    page_title("Configurações", "Parâmetros operacionais e manutenção da base local.")
    st.markdown(f"**Banco SQLite local:** `{DB_PATH}`")
    st.info("Observações, agendamentos, histórico, status Já liguei e orçamentos vinculados são persistidos nesse arquivo.")
    if st.button("Garantir estrutura do banco"):
        init_db()
        st.success("Estrutura validada.")
