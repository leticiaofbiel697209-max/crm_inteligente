from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from services.crm_pro_logic import (
    GestaoClickAPI,
    calcular_churn,
    calcular_metricas_financeiras,
    fmt,
    gerar_texto_email,
    listar_clientes_churn,
    montar_prioridade,
    processar_api,
    processar_dados,
)


def render() -> None:
    st.subheader("CRM Pro")
    st.caption("Baseado no código CRM Inteligente - Nível CEO anexado.")

    fonte_api, fonte_excel = st.tabs(["API GestãoClick", "Excel"])

    with fonte_api:
        render_api_loader()

    with fonte_excel:
        vendas_file = st.file_uploader("Relatório de Vendas", type=["xlsx"], key="crm_pro_vendas")
        orc_file = st.file_uploader("Relatório de Orçamentos", type=["xlsx"], key="crm_pro_orc")
        contas_file = st.file_uploader("Contas a Receber", type=["xlsx"], key="crm_pro_contas")

        if st.button("Analisar arquivos CRM Pro", type="primary"):
            if not vendas_file or not orc_file or not contas_file:
                st.error("Envie os três arquivos para processar o CRM Pro.")
            else:
                try:
                    with st.spinner("Processando relatórios..."):
                        st.session_state.crm_pro_dados = processar_dados(vendas_file, orc_file, contas_file)
                    st.success("Dados processados.")
                except Exception as exc:
                    st.error(f"Erro ao processar: {exc}")

    dados = st.session_state.get("crm_pro_dados")
    if not dados:
        st.info("Carregue dados pela API GestãoClick ou pelos arquivos Excel para ativar os cálculos do CRM Pro.")
        return

    clientes = dados["clientes"]
    prioridade = montar_prioridade(clientes)
    clientes_churn = listar_clientes_churn(clientes)
    taxa_churn, qtd_churn, base_churn = calcular_churn(clientes)
    financeiro = calcular_metricas_financeiras(dados.get("financeiro"))

    cols = st.columns(4)
    cols[0].metric("Faturamento histórico", fmt(clientes["faturamento"].sum()))
    cols[1].metric("Potencial mensal", fmt(clientes["potencial_mensal"].sum()))
    cols[2].metric("Churn estimado", f"{taxa_churn:.1f}%")
    cols[3].metric("Clientes em churn", f"{qtd_churn}/{base_churn}")

    cols2 = st.columns(4)
    cols2[0].metric("Potencial recuperável", fmt(clientes["potencial_recuperavel"].sum()))
    cols2[1].metric("Inadimplência", fmt(clientes["inadimplencia"].sum()))
    cols2[2].metric("Carteira a receber", fmt(financeiro["total_aberto"]))
    cols2[3].metric("Total vencido", fmt(financeiro["total_vencido"]), f"{financeiro['percentual_vencido']:.1f}%")

    tabs = st.tabs(["Prioridade", "Churn", "Orçamentos", "Base", "Resumo E-mail"])
    with tabs[0]:
        st.dataframe(prioridade, width="stretch", hide_index=True)
    with tabs[1]:
        st.dataframe(clientes_churn, width="stretch", hide_index=True)
    with tabs[2]:
        st.dataframe(dados["orc_aberto"], width="stretch", hide_index=True)
    with tabs[3]:
        st.dataframe(clientes, width="stretch", hide_index=True)
    with tabs[4]:
        texto = gerar_texto_email(dados)
        st.text_area("Texto pronto para envio", texto, height=520)
        st.download_button("Baixar resumo em .txt", texto, "Resumo_Comercial_CRM_Pro.txt", "text/plain")


def get_api_from_secrets() -> GestaoClickAPI | None:
    try:
        config = st.secrets.get("gestaoclick", {})
        access = str(config.get("access_token", "")).strip()
        secret = str(config.get("secret_token", "")).strip()
    except Exception:
        access = ""
        secret = ""
    if not access:
        access = str(st.secrets.get("GESTAOCLICK_ACCESS_TOKEN", "")).strip()
    if not secret:
        secret = str(st.secrets.get("GESTAOCLICK_SECRET_TOKEN", "")).strip()
    if not access or not secret:
        return None
    return GestaoClickAPI(access, secret)


def render_api_loader() -> None:
    st.caption("Versão API GestãoClick: 2026-06-16.3")

    try:
        config = st.secrets.get("gestaoclick", {})
        access = str(config.get("access_token", "")).strip() or str(st.secrets.get("GESTAOCLICK_ACCESS_TOKEN", "")).strip()
        secret = str(config.get("secret_token", "")).strip() or str(st.secrets.get("GESTAOCLICK_SECRET_TOKEN", "")).strip()
    except Exception:
        access = ""
        secret = ""

    col_status1, col_status2 = st.columns(2)
    col_status1.metric("Access token encontrado", "Sim" if access else "Não")
    col_status2.metric("Secret token encontrado", "Sim" if secret else "Não")

    if not access or not secret:
        st.warning(
            "Tokens não encontrados. Cadastre em Secrets como "
            "`[gestaoclick] access_token = \"...\" secret_token = \"...\"`."
        )
        return

    api = GestaoClickAPI(access, secret)
    st.success("Tokens da API encontrados nos Secrets.")

    if st.button("Testar conexão com GestãoClick"):
        try:
            with st.spinner("Testando conexão..."):
                lojas_teste = api.stores()
            st.success(f"Conexão OK. Lojas encontradas: {len(lojas_teste)}")
            st.session_state.crm_pro_lojas = lojas_teste
        except Exception as exc:
            st.error(f"A API respondeu com erro: {exc}")
            st.info(
                "Confira se os tokens foram copiados completos, sem espaços antes/depois, "
                "e se pertencem ao mesmo ambiente/conta do GestãoClick."
            )

    if st.button("Carregar lojas do GestãoClick"):
        try:
            with st.spinner("Conectando ao GestãoClick..."):
                st.session_state.crm_pro_lojas = api.stores()
            st.success("Lojas carregadas.")
        except Exception as exc:
            st.error(f"Erro ao carregar lojas: {exc}")

    lojas = st.session_state.get("crm_pro_lojas", [])
    if not lojas:
        st.info("Clique em carregar lojas para selecionar a loja e buscar os dados.")
        return

    lojas_validas = [loja for loja in lojas if str(loja.get("id") or "").strip()]
    loja = st.selectbox(
        "Loja",
        lojas_validas,
        format_func=lambda item: item.get("nome") or item.get("nome_fantasia") or f"Loja {item.get('id')}",
    )
    loja_id = str(loja.get("id"))

    if st.button("Carregar vendedores"):
        try:
            with st.spinner("Carregando vendedores..."):
                st.session_state.crm_pro_vendedores = api.users(loja_id)
            st.success("Vendedores carregados.")
        except Exception as exc:
            st.error(f"Erro ao carregar vendedores: {exc}")

    vendedores = [
        usuario for usuario in st.session_state.get("crm_pro_vendedores", [])
        if str(usuario.get("id") or "").strip() and str(usuario.get("nome") or "").strip()
    ]
    vendedor = st.selectbox(
        "Vendedor",
        [{"id": "", "nome": "Todos"}, *vendedores],
        format_func=lambda item: item.get("nome") or "Sem nome",
    )

    fim_padrao = date.today()
    inicio_padrao = fim_padrao - timedelta(days=365)
    col1, col2 = st.columns(2)
    inicio = col1.date_input("Vendas desde", value=inicio_padrao, max_value=fim_padrao)
    fim = col2.date_input("Até", value=fim_padrao, min_value=inicio, max_value=fim_padrao)

    if st.button("Atualizar dados do GestãoClick", type="primary"):
        try:
            with st.spinner("Buscando vendas, orçamentos e contas a receber..."):
                st.session_state.crm_pro_dados = processar_api(
                    api,
                    inicio,
                    fim,
                    loja_id,
                    vendedor.get("id") or None,
                    vendedor.get("nome") or "Todos",
                )
            st.success("Dados atualizados pelo GestãoClick.")
            st.rerun()
        except Exception as exc:
            st.error(f"Erro ao buscar dados do GestãoClick: {exc}")
            st.info(
                "Se a conexão funcionou mas não vieram vendas, aumente o período em "
                "`Vendas desde`. Para churn, use 12 a 24 meses."
            )
