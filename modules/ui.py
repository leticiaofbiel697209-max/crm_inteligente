from __future__ import annotations

import pandas as pd
import streamlit as st


BRAND_BLUE = "#123B6D"
BRAND_CYAN = "#00A6D6"
BRAND_GREEN = "#18A058"
BRAND_BG = "#F4F7FA"


def apply_ceo_style() -> None:
    st.markdown(
        f"""
        <style>
        .stApp {{
            background: {BRAND_BG};
            color: #17202a;
        }}
        [data-testid="stSidebar"] {{
            background: #0F2F54;
        }}
        [data-testid="stSidebar"] * {{
            color: #ffffff;
        }}
        .main .block-container {{
            padding-top: 1.6rem;
            max-width: 1280px;
        }}
        h1, h2, h3 {{
            color: {BRAND_BLUE};
            letter-spacing: 0;
        }}
        div[data-testid="stMetric"] {{
            background: #ffffff;
            border: 1px solid #E1E7EF;
            border-left: 5px solid {BRAND_CYAN};
            border-radius: 8px;
            padding: 14px 16px;
            box-shadow: 0 3px 12px rgba(18, 59, 109, 0.07);
        }}
        .np-card {{
            background: #ffffff;
            border: 1px solid #E1E7EF;
            border-radius: 8px;
            padding: 18px;
            box-shadow: 0 3px 12px rgba(18, 59, 109, 0.07);
            margin-bottom: 14px;
        }}
        .np-badge {{
            display: inline-block;
            padding: 4px 9px;
            border-radius: 999px;
            background: #E8F6FB;
            color: {BRAND_BLUE};
            font-size: 0.82rem;
            font-weight: 700;
        }}
        .stButton button {{
            border-radius: 6px;
            border: 1px solid {BRAND_BLUE};
            background: {BRAND_BLUE};
            color: #ffffff;
        }}
        .stButton button:hover {{
            border: 1px solid {BRAND_CYAN};
            background: {BRAND_CYAN};
            color: #ffffff;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_title(title: str, subtitle: str) -> None:
    st.title(title)
    st.caption(subtitle)


def money(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def metric_row(clientes: list[dict], orcamentos: list[dict]) -> None:
    ativos = sum(1 for c in clientes if c.get("status") == "Ativo")
    risco = sum(1 for c in clientes if int(c.get("score_risco") or 0) >= 70)
    potencial = sum(float(c.get("potencial_recuperavel") or 0) for c in clientes)
    pipeline = sum(float(o.get("valor") or 0) for o in orcamentos)
    cols = st.columns(4)
    cols[0].metric("Clientes ativos", ativos)
    cols[1].metric("Clientes em risco", risco)
    cols[2].metric("Potencial recuperável", money(potencial))
    cols[3].metric("Pipeline orçamentos", money(pipeline))


def dataframe(data: list[dict], *, hide_index: bool = True) -> None:
    if not data:
        st.info("Nenhum registro encontrado.")
        return
    st.dataframe(pd.DataFrame(data), width="stretch", hide_index=hide_index)


def client_selector(clientes: list[dict], label: str = "Cliente") -> str:
    labels = {f"{c['nome']} ({c['cliente_id']})": c["cliente_id"] for c in clientes}
    selected = st.selectbox(label, list(labels.keys()))
    return labels[selected]


def render_history(observacoes: list[dict], agendamentos: list[dict], historico: list[dict]) -> None:
    tabs = st.tabs(["Observações", "Agendamentos", "Histórico"])
    with tabs[0]:
        dataframe(observacoes)
    with tabs[1]:
        dataframe(agendamentos)
    with tabs[2]:
        dataframe(historico)
