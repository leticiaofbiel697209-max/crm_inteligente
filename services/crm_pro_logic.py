from __future__ import annotations

import re
import time
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
from html import escape
from typing import Any

import pandas as pd


API_BASE = "https://api.gestaoclick.com"


class GestaoClickAPI:
    def __init__(self, access_token: str, secret_token: str):
        self.headers = {
            "Content-Type": "application/json",
            "access-token": access_token,
            "secret-access-token": secret_token,
        }
        self.last_request = 0.0

    def request(self, path: str, params: dict[str, Any] | None = None, method: str = "GET", body: dict[str, Any] | None = None) -> dict[str, Any]:
        elapsed = time.monotonic() - self.last_request
        if elapsed < 0.36:
            time.sleep(0.36 - elapsed)
        url = API_BASE + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(url, data=data, headers=self.headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"GestãoClick retornou erro {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Não foi possível acessar o GestãoClick: {exc.reason}") from exc
        finally:
            self.last_request = time.monotonic()
        if payload.get("status") != "success":
            raise RuntimeError(payload.get("message") or "Resposta inesperada do GestãoClick.")
        return payload

    def list_all(self, path: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        records = []
        page = 1
        while True:
            query = dict(params or {})
            query.update({"pagina": page, "limite": 100})
            payload = self.request(path, query)
            page_records = payload.get("data") or []
            records.extend(page_records)
            meta = payload.get("meta") or {}
            if not meta.get("proxima_pagina") and len(page_records) < 100:
                break
            page += 1
            if page > 200:
                raise RuntimeError("A consulta excedeu 200 páginas.")
        return records

    def stores(self) -> list[dict[str, Any]]:
        return self.list_all("/lojas")

    def users(self, store_id: str) -> list[dict[str, Any]]:
        return self.list_all("/usuarios", {"loja_id": store_id})

    def sales(self, start_date: date, end_date: date, store_id: str) -> list[dict[str, Any]]:
        return self.list_all("/vendas", {"loja_id": store_id, "data_inicio": start_date.isoformat(), "data_fim": end_date.isoformat()})

    def budgets(self, start_date: date, end_date: date, store_id: str) -> list[dict[str, Any]]:
        return self.list_all("/orcamentos", {"loja_id": store_id, "data_inicio": start_date.isoformat(), "data_fim": end_date.isoformat()})

    def open_receivables(self, store_id: str) -> list[dict[str, Any]]:
        records = []
        seen = set()
        for status in ("ab", "at"):
            for item in self.list_all("/recebimentos", {"loja_id": store_id, "liquidado": status}):
                key = str(item.get("id") or item.get("codigo") or "")
                if key and key in seen:
                    continue
                if key:
                    seen.add(key)
                copy = dict(item)
                copy["_status_financeiro"] = "ATRASADO" if status == "at" else "EM ABERTO"
                records.append(copy)
        return records


def deduplicar_registros(registros: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unicos: dict[str, dict[str, Any]] = {}
    sem_id = []
    for item in registros:
        key = str(item.get("id") or "").strip()
        if key:
            unicos[key] = item
        else:
            sem_id.append(item)
    return list(unicos.values()) + sem_id


def custo_total_venda(item: dict[str, Any]) -> float:
    custo = 0.0
    for campo in ("produtos", "servicos"):
        for wrapper in item.get(campo) or []:
            detalhe = wrapper.get("produto") or wrapper.get("servico") or {}
            quantidade = pd.to_numeric(pd.Series([detalhe.get("quantidade") or 1]), errors="coerce").fillna(1).iloc[0]
            custo_unitario = pd.to_numeric(pd.Series([detalhe.get("valor_custo") or 0]), errors="coerce").fillna(0).iloc[0]
            custo += float(quantidade) * float(custo_unitario)
    if custo == 0:
        custo = float(pd.to_numeric(pd.Series([item.get("valor_custo") or 0]), errors="coerce").fillna(0).iloc[0])
    return custo


def fmt(v: Any) -> str:
    try:
        return f"R${float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$0,00"


def fmt_html(v: Any) -> str:
    return fmt(v).replace("$", "&#36;")


def html_seguro(v: Any) -> str:
    return escape(str(v), quote=True)


def norm(x: Any) -> str:
    return str(x).strip().lower().replace("º", "o").replace("°", "o")


def achar_coluna(df: pd.DataFrame, termos: list[str]) -> str | None:
    for coluna in df.columns:
        nome = norm(coluna)
        if any(norm(termo) in nome for termo in termos):
            return coluna
    return None


def data_coluna(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, dayfirst=True, errors="coerce")


def numero_coluna(s: pd.Series) -> pd.Series:
    def converter(v: Any) -> float:
        if pd.isna(v):
            return 0.0
        if isinstance(v, (int, float)):
            return float(v)
        texto = re.sub(r"[^\d,.\-]", "", str(v).strip())
        if not texto:
            return 0.0
        if "," in texto and "." in texto:
            texto = texto.replace(".", "").replace(",", ".") if texto.rfind(",") > texto.rfind(".") else texto.replace(",", "")
        elif "," in texto:
            texto = texto.replace(".", "").replace(",", ".")
        elif re.fullmatch(r"-?\d{1,3}(\.\d{3})+", texto):
            texto = texto.replace(".", "")
        try:
            return float(texto)
        except ValueError:
            return 0.0

    return s.apply(converter)


def status_orcamento(dias: int) -> str:
    if dias <= 1:
        return "Aceitável"
    if dias == 2:
        return "Ligar hoje"
    if dias == 3:
        return "Urgente"
    return "Risco de ter perdido"


def score_risco(media_atraso: float) -> int:
    if pd.isna(media_atraso) or media_atraso <= 0:
        return 100
    return max(0, min(100, int(100 - media_atraso * 2)))


def descricao_score(score: int) -> str:
    if score >= 85:
        return "Baixo risco de inadimplência"
    if score >= 65:
        return "Risco moderado de inadimplência"
    if score >= 40:
        return "Alto risco de inadimplência"
    return "Risco crítico de inadimplência"


def temperatura_cliente(dias: int, intervalo: float) -> str:
    if intervalo <= 0:
        if dias <= 30:
            return "NOVO"
        if dias <= 60:
            return "ATENÇÃO"
        return "CLIENTE INATIVO"
    if intervalo * 0.9 <= dias <= intervalo * 1.2:
        return "QUENTE"
    if intervalo * 1.2 < dias <= intervalo * 1.5:
        return "ATENÇÃO"
    if intervalo * 1.5 < dias <= intervalo * 2:
        return "ATRASADO NA RECOMPRA"
    if dias > intervalo * 2:
        return "CLIENTE INATIVO"
    return "CEDO"


def sugestao_ia(dias: int, intervalo: float, orcs: int, inad: float, potencial: float) -> str:
    temp = temperatura_cliente(dias, intervalo)
    if inad > 0:
        return "Cliente com inadimplência. Priorizar cobrança antes de nova venda."
    if orcs > 0 and temp in ["QUENTE", "ATENÇÃO"]:
        return "Cliente com orçamento em aberto e bom momento de compra. Priorizar fechamento hoje."
    if temp == "QUENTE":
        return f"Momento ideal. Ligar com oferta direta. Potencial mensal: {fmt(potencial)}."
    if temp == "ATENÇÃO":
        return "Cliente passou levemente do ciclo. Fazer contato de retomada antes que esfrie."
    if temp == "ATRASADO NA RECOMPRA":
        return "Cliente atrasado na recompra. Entender se comprou de concorrente ou se esqueceu."
    if temp == "CLIENTE INATIVO":
        return "Cliente inativo. Usar abordagem de reativação com condição especial."
    if orcs > 0:
        return "Cliente com orçamento em aberto. Fazer follow-up comercial."
    if temp == "CEDO":
        return "Ainda cedo para venda direta. Manter relacionamento ou aquecer contato."
    return "Cliente novo. Iniciar relacionamento comercial."


def score_comercial(row: pd.Series) -> int:
    score = 0
    temp = row["temperatura"]
    if temp == "QUENTE":
        score += 40
    elif temp == "ATENÇÃO":
        score += 30
    elif temp == "ATRASADO NA RECOMPRA":
        score += 20
    elif temp == "CLIENTE INATIVO":
        score += 10
    if row["orcamentos_em_aberto"] > 0:
        score += 20
    if row["score_risco"] >= 85:
        score += 20
    elif row["score_risco"] >= 65:
        score += 10
    if row["potencial_mensal"] > 0:
        score += 20
    return min(score, 100)


def carregar_excel(file: Any, grupos_busca: list[list[str]]) -> pd.DataFrame:
    bruto = pd.read_excel(file, header=None, engine="openpyxl")
    melhor_linha, melhor_score = 0, -1
    for i in range(min(15, len(bruto))):
        valores = [norm(x) for x in bruto.iloc[i].tolist()]
        score = sum(1 for grupo in grupos_busca if any(any(norm(t) in v for v in valores) for t in grupo))
        if score > melhor_score:
            melhor_linha, melhor_score = i, score
    df = pd.read_excel(file, header=melhor_linha, engine="openpyxl")
    df = df.dropna(how="all")
    df.columns = [str(c).strip() for c in df.columns]
    return df


def preparar_financeiro(contas: pd.DataFrame, col_cliente: str, col_vencimento: str | None, col_valor: str, col_status: str | None) -> pd.DataFrame:
    financeiro = pd.DataFrame(
        {
            "Cliente": contas[col_cliente].astype(str).str.strip(),
            "Vencimento": contas[col_vencimento] if col_vencimento else pd.Series(pd.NaT, index=contas.index),
            "Valor": contas[col_valor],
            "Situacao": contas[col_status].astype(str) if col_status else pd.Series("EM ABERTO", index=contas.index),
        }
    )
    financeiro["Vencimento"] = pd.to_datetime(financeiro["Vencimento"], errors="coerce")
    financeiro["Valor"] = pd.to_numeric(financeiro["Valor"], errors="coerce").fillna(0)
    financeiro["Situacao"] = financeiro["Situacao"].str.upper().str.strip()
    liquidado = financeiro["Situacao"].str.contains("PAGO|LIQUIDADO|RECEBIDO|CONFIRMADO|QUITADO", na=False, regex=True)
    financeiro = financeiro[(~liquidado) & financeiro["Cliente"].ne("") & financeiro["Vencimento"].notna() & financeiro["Valor"].gt(0)].copy()
    hoje = pd.Timestamp(date.today())
    financeiro["Dias_para_vencer"] = (financeiro["Vencimento"].dt.normalize() - hoje).dt.days
    financeiro["Vencida"] = financeiro["Dias_para_vencer"].lt(0) | financeiro["Situacao"].str.contains("ATRASADO|VENCIDO", na=False, regex=True)
    financeiro["Dias_atraso"] = (-financeiro["Dias_para_vencer"]).clip(lower=0)
    return financeiro.sort_values(["Vencida", "Vencimento"], ascending=[False, True])


def calcular_metricas_financeiras(financeiro: pd.DataFrame | None) -> dict[str, float]:
    vazio = {"total_aberto": 0.0, "total_vencido": 0.0, "percentual_vencido": 0.0, "vence_7": 0.0, "vence_15": 0.0, "vence_30": 0.0}
    if financeiro is None or financeiro.empty:
        return vazio
    total = float(financeiro["Valor"].sum())
    vencido = float(financeiro.loc[financeiro["Vencida"], "Valor"].sum())
    futuro = financeiro[~financeiro["Vencida"]]
    return {
        **vazio,
        "total_aberto": total,
        "total_vencido": vencido,
        "percentual_vencido": (vencido / total * 100) if total else 0.0,
        "vence_7": float(futuro.loc[futuro["Dias_para_vencer"].between(0, 7), "Valor"].sum()),
        "vence_15": float(futuro.loc[futuro["Dias_para_vencer"].between(8, 15), "Valor"].sum()),
        "vence_30": float(futuro.loc[futuro["Dias_para_vencer"].between(16, 30), "Valor"].sum()),
    }


def processar_dataframes(vendas: pd.DataFrame, orc: pd.DataFrame, contas: pd.DataFrame) -> dict[str, Any]:
    hoje = datetime.now()
    cv_cli = achar_coluna(vendas, ["cliente"])
    cv_cli_id = achar_coluna(vendas, ["cliente id"])
    cv_data = achar_coluna(vendas, ["data"])
    cv_valor = achar_coluna(vendas, ["valor"])
    cv_status = achar_coluna(vendas, ["situacao", "status"])
    cv_vendedor = achar_coluna(vendas, ["vendedor"])
    co_num = achar_coluna(orc, ["nº", "n°", "numero", "número"])
    co_cli = achar_coluna(orc, ["cliente"])
    co_data = achar_coluna(orc, ["data"])
    co_status = achar_coluna(orc, ["situação", "situacao", "status"])
    co_valor = achar_coluna(orc, ["valor"])
    cc_cli = achar_coluna(contas, ["cliente", "destinado"])
    cc_cli_id = achar_coluna(contas, ["cliente id"])
    cc_venc = achar_coluna(contas, ["vencimento"])
    cc_status = achar_coluna(contas, ["situação", "situacao", "status"])
    cc_valor = achar_coluna(contas, ["valor total", "valor"])
    faltando = [nome for nome, col in {"Cliente vendas": cv_cli, "Data vendas": cv_data, "Valor vendas": cv_valor, "Nº orçamento": co_num, "Cliente orçamento": co_cli, "Data orçamento": co_data, "Status orçamento": co_status, "Cliente contas": cc_cli, "Valor contas": cc_valor}.items() if col is None]
    if faltando:
        raise ValueError("Colunas não encontradas: " + ", ".join(faltando))

    vendas = vendas.copy()
    orc = orc.copy()
    contas = contas.copy()
    vendas[cv_data] = data_coluna(vendas[cv_data])
    vendas[cv_valor] = numero_coluna(vendas[cv_valor])
    vendas = vendas.dropna(subset=[cv_cli, cv_data])
    vendas["_cliente_chave"] = vendas[cv_cli_id].astype(str).str.strip() if cv_cli_id else vendas[cv_cli].map(norm)
    vendas["_cliente_nome"] = vendas[cv_cli].astype(str).str.strip()
    if cv_status:
        cancelada = vendas[cv_status].astype(str).str.upper().str.contains("CANCEL|DEVOL|ESTORN|REPROV|PERDID", na=False, regex=True)
        vendas = vendas[~cancelada].copy()

    orc[co_data] = data_coluna(orc[co_data])
    if co_valor:
        orc[co_valor] = numero_coluna(orc[co_valor])
    contas[cc_valor] = numero_coluna(contas[cc_valor])
    if cc_venc:
        contas[cc_venc] = data_coluna(contas[cc_venc])

    financeiro = preparar_financeiro(contas, cc_cli, cc_venc, cc_valor, cc_status)
    contas["_cliente_chave"] = contas[cc_cli_id].astype(str).str.strip() if cc_cli_id else contas[cc_cli].map(norm)

    clientes = vendas.groupby("_cliente_chave").agg({"_cliente_nome": "last", cv_data: ["max", "count"], cv_valor: "sum"})
    clientes.columns = ["Cliente", "ultima_compra", "qtd_compras", "faturamento"]
    clientes = clientes.reset_index().rename(columns={"_cliente_chave": "Cliente ID"})
    vendas_recentes = vendas.sort_values(cv_data).drop_duplicates("_cliente_chave", keep="last").set_index("_cliente_chave")
    clientes["Vendedor"] = clientes["Cliente ID"].map(vendas_recentes[cv_vendedor]).fillna("Sem vendedor") if cv_vendedor else "Sem vendedor"
    intervalo = vendas.sort_values(cv_data).groupby("_cliente_chave")[cv_data].apply(lambda x: x.diff().mean().days if len(x.dropna()) > 1 else 0)
    clientes["intervalo"] = clientes["Cliente ID"].map(intervalo).fillna(0)
    clientes["dias_sem_comprar"] = (hoje - clientes["ultima_compra"]).dt.days
    clientes["ticket_medio"] = clientes["faturamento"] / clientes["qtd_compras"]
    vendas_3m = vendas[vendas[cv_data] >= hoje - pd.DateOffset(months=3)].copy()
    clientes["potencial_mensal"] = clientes["Cliente ID"].map(vendas_3m.groupby("_cliente_chave")[cv_valor].sum() / 3).fillna(0)

    status_fechado = "CONCRETIZADO|CANCELADO|PERDIDO|REPROVADO|FATURADO|FINALIZADO|FECHADO|VENDIDO"
    orc_aberto = orc[~orc[co_status].astype(str).str.upper().str.contains(status_fechado, na=False, regex=True)].copy()
    orc_aberto = orc_aberto[orc_aberto[co_data] >= hoje - pd.Timedelta(days=30)].copy()
    orc_aberto["dias_no_sistema"] = (hoje - orc_aberto[co_data]).dt.days
    orc_aberto["acao_recomendada_orcamento"] = orc_aberto["dias_no_sistema"].apply(status_orcamento)
    clientes["orcamentos_em_aberto"] = clientes["Cliente"].map(orc_aberto.groupby(co_cli)[co_num].count()).fillna(0)

    contas_atraso = contas[contas[cc_status].astype(str).str.upper().str.contains("ATRASADO|VENCIDO", na=False)].copy() if cc_status else contas.iloc[0:0].copy()
    if cc_venc and not contas_atraso.empty:
        contas_atraso["dias_atraso"] = (hoje - contas_atraso[cc_venc]).dt.days.clip(lower=0)
    inad = contas_atraso.groupby("_cliente_chave")[cc_valor].sum() if not contas_atraso.empty else pd.Series(dtype=float)
    media_atraso = contas_atraso.groupby("_cliente_chave")["dias_atraso"].mean() if "dias_atraso" in contas_atraso else pd.Series(dtype=float)
    clientes["inadimplencia"] = clientes["Cliente ID"].map(inad).fillna(0)
    clientes["media_dias_atraso"] = clientes["Cliente ID"].map(media_atraso).fillna(0)
    clientes["score_risco"] = clientes["media_dias_atraso"].apply(score_risco)
    clientes["risco_inadimplencia"] = clientes["score_risco"].apply(descricao_score)
    clientes["temperatura"] = clientes.apply(lambda x: temperatura_cliente(x["dias_sem_comprar"], x["intervalo"]), axis=1)
    limite_estrategico = clientes["faturamento"].quantile(0.90)
    clientes["cliente_estrategico"] = clientes["faturamento"] >= limite_estrategico
    clientes["potencial_recuperavel"] = clientes.apply(lambda x: x["potencial_mensal"] if x["temperatura"] in ["ATRASADO NA RECOMPRA", "CLIENTE INATIVO"] else 0, axis=1)
    clientes["acao_ia"] = clientes.apply(lambda x: sugestao_ia(x["dias_sem_comprar"], x["intervalo"], x["orcamentos_em_aberto"], x["inadimplencia"], x["potencial_mensal"]), axis=1)
    clientes["score_comercial"] = clientes.apply(score_comercial, axis=1)

    return {"clientes": clientes, "orc_aberto": orc_aberto, "orcamentos_todos": orc, "co_num": co_num, "co_cli": co_cli, "co_valor": co_valor, "financeiro": financeiro, "periodo_inicio": vendas[cv_data].min(), "periodo_fim": vendas[cv_data].max()}


def processar_dados(vendas_file: Any, orc_file: Any, contas_file: Any) -> dict[str, Any]:
    vendas = carregar_excel(vendas_file, [["cliente"], ["data"], ["valor"]])
    orc = carregar_excel(orc_file, [["nº", "n°", "numero", "número"], ["cliente"], ["data"], ["situação", "status"]])
    contas = carregar_excel(contas_file, [["cliente", "destinado"], ["vencimento"], ["valor"], ["situação", "status"]])
    dados = processar_dataframes(vendas, orc, contas)
    dados["origem"] = "excel"
    return dados


def api_para_dataframes(
    vendas_api: list[dict[str, Any]],
    orcamentos_api: list[dict[str, Any]],
    recebimentos_api: list[dict[str, Any]],
    vendedor_id: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    vendas_api = deduplicar_registros(vendas_api)
    orcamentos_api = deduplicar_registros(orcamentos_api)
    recebimentos_api = deduplicar_registros(recebimentos_api)
    if vendedor_id:
        vendas_api = [item for item in vendas_api if str(item.get("vendedor_id") or "") == str(vendedor_id)]
        orcamentos_api = [item for item in orcamentos_api if str(item.get("vendedor_id") or "") == str(vendedor_id)]

    vendas = pd.DataFrame(
        [
            {
                "Cliente": item.get("nome_cliente") or "Cliente sem nome",
                "Cliente ID": item.get("cliente_id"),
                "Data": pd.to_datetime(item.get("data"), format="%Y-%m-%d", errors="coerce"),
                "Valor": item.get("valor_total") or 0,
                "Custo": custo_total_venda(item),
                "Situacao": item.get("nome_situacao") or "",
                "Vendedor": item.get("nome_vendedor") or "Sem vendedor",
                "Vendedor ID": item.get("vendedor_id"),
            }
            for item in vendas_api
        ]
    )
    orcamentos = pd.DataFrame(
        [
            {
                "Numero": item.get("codigo") or item.get("id"),
                "Cliente": item.get("nome_cliente") or "Cliente sem nome",
                "Cliente ID": item.get("cliente_id"),
                "Data": pd.to_datetime(item.get("data"), format="%Y-%m-%d", errors="coerce"),
                "Situacao": item.get("nome_situacao") or "",
                "Valor": item.get("valor_total") or 0,
                "Vendedor": item.get("nome_vendedor") or "Sem vendedor",
            }
            for item in orcamentos_api
        ]
    )
    contas = pd.DataFrame(
        [
            {
                "Cliente": item.get("nome_cliente") or "Cliente sem nome",
                "Cliente ID": item.get("cliente_id"),
                "Vencimento": pd.to_datetime(item.get("data_vencimento"), format="%Y-%m-%d", errors="coerce"),
                "Valor Total": item.get("valor_total") or item.get("valor") or 0,
                "Situacao": item.get("_status_financeiro") or "EM ABERTO",
            }
            for item in recebimentos_api
        ]
    )
    if vendas.empty:
        vendas = pd.DataFrame(columns=["Cliente", "Cliente ID", "Data", "Valor", "Custo", "Situacao", "Vendedor", "Vendedor ID"])
    if orcamentos.empty:
        orcamentos = pd.DataFrame(columns=["Numero", "Cliente", "Cliente ID", "Data", "Situacao", "Valor", "Vendedor"])
    if contas.empty:
        contas = pd.DataFrame(columns=["Cliente", "Cliente ID", "Vencimento", "Valor Total", "Situacao"])
    return vendas, orcamentos, contas


def processar_api(
    api: GestaoClickAPI,
    inicio: date,
    fim: date,
    loja_id: str,
    vendedor_id: str | None = None,
    vendedor_nome: str = "Todos",
) -> dict[str, Any]:
    vendas_api = api.sales(inicio, fim, loja_id)
    orcamentos_api = api.budgets(inicio, fim, loja_id)
    recebimentos_api = api.open_receivables(loja_id)
    vendas, orcamentos, contas = api_para_dataframes(vendas_api, orcamentos_api, recebimentos_api, vendedor_id)
    if vendas.empty:
        raise RuntimeError("Nenhuma venda foi encontrada para os filtros selecionados.")
    dados = processar_dataframes(vendas, orcamentos, contas)
    dados.update(
        {
            "origem": "api",
            "loja_id": str(loja_id),
            "vendedor_id": str(vendedor_id or ""),
            "vendedor_nome": vendedor_nome,
            "atualizado_em": datetime.now(),
        }
    )
    return dados


def calcular_churn(clientes: pd.DataFrame) -> tuple[float, int, int]:
    clientes_com_ciclo = clientes[clientes["intervalo"] > 0]
    if clientes_com_ciclo.empty:
        return 0.0, 0, 0
    clientes_churn = clientes_com_ciclo[clientes_com_ciclo["dias_sem_comprar"] > clientes_com_ciclo["intervalo"] * 2]
    return len(clientes_churn) / len(clientes_com_ciclo) * 100, len(clientes_churn), len(clientes_com_ciclo)


def listar_clientes_churn(clientes: pd.DataFrame) -> pd.DataFrame:
    churn = clientes[(clientes["intervalo"] > 0) & (clientes["dias_sem_comprar"] > clientes["intervalo"] * 2)].copy()
    if churn.empty:
        return churn
    churn["limite_churn_dias"] = (churn["intervalo"] * 2).round().astype(int)
    churn["dias_alem_limite"] = (churn["dias_sem_comprar"] - churn["limite_churn_dias"]).clip(lower=0).astype(int)
    return churn.sort_values(["potencial_mensal", "dias_alem_limite"], ascending=[False, False])


def montar_prioridade(clientes: pd.DataFrame) -> pd.DataFrame:
    return clientes[
        clientes["temperatura"].isin(["QUENTE", "ATENÇÃO", "ATRASADO NA RECOMPRA", "CLIENTE INATIVO"])
        | clientes["orcamentos_em_aberto"].gt(0)
    ].sort_values("score_comercial", ascending=False)


def gerar_texto_email(dados: dict[str, Any]) -> str:
    clientes = dados["clientes"]
    prioridade = montar_prioridade(clientes)
    taxa_churn, qtd_churn, base_churn = calcular_churn(clientes)
    periodo_inicio = dados.get("periodo_inicio")
    periodo_fim = dados.get("periodo_fim")
    periodo = f"{periodo_inicio:%d/%m/%Y} a {periodo_fim:%d/%m/%Y}" if pd.notna(periodo_inicio) and pd.notna(periodo_fim) else "período importado"
    linhas = [
        f"RESUMO COMERCIAL DIÁRIO - {datetime.now():%d/%m/%Y}",
        f"Período analisado: {periodo}",
        "",
        "VISÃO EXECUTIVA",
        f"- Faturamento histórico importado: {fmt(clientes['faturamento'].sum())}",
        f"- Potencial mensal da carteira: {fmt(clientes['potencial_mensal'].sum())}",
        f"- Potencial recuperável: {fmt(clientes['potencial_recuperavel'].sum())}",
        f"- Inadimplência identificada: {fmt(clientes['inadimplencia'].sum())}",
        f"- Churn estimado: {taxa_churn:.1f}% ({qtd_churn} de {base_churn} clientes com ciclo conhecido)",
        "",
        f"PRIORIDADES DE HOJE ({len(prioridade)})",
    ]
    for i, (_, r) in enumerate(prioridade.head(10).iterrows(), 1):
        linhas.append(f"{i}. {r['Cliente']} | Ticket {fmt(r['ticket_medio'])} | Potencial {fmt(r['potencial_mensal'])} | {r['acao_ia']}")
    return "\n".join(linhas)
