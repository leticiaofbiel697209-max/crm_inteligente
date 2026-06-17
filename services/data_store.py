from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = ROOT_DIR / "database" / "novaprint.db"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS clientes (
                cliente_id TEXT PRIMARY KEY,
                nome TEXT NOT NULL,
                responsavel TEXT,
                vendedora TEXT,
                telefone TEXT,
                email TEXT,
                ultima_compra TEXT,
                valor_mensal REAL DEFAULT 0,
                potencial_recuperavel REAL DEFAULT 0,
                status TEXT DEFAULT 'Ativo',
                score_risco INTEGER DEFAULT 0,
                proxima_acao TEXT
            );

            CREATE TABLE IF NOT EXISTS observacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id TEXT NOT NULL,
                texto TEXT NOT NULL,
                origem TEXT NOT NULL,
                usuario TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (cliente_id) REFERENCES clientes(cliente_id)
            );

            CREATE TABLE IF NOT EXISTS agendamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id TEXT NOT NULL,
                data TEXT NOT NULL,
                hora TEXT,
                observacao TEXT,
                origem TEXT NOT NULL,
                usuario TEXT,
                status TEXT DEFAULT 'Aberto',
                created_at TEXT NOT NULL,
                FOREIGN KEY (cliente_id) REFERENCES clientes(cliente_id)
            );

            CREATE TABLE IF NOT EXISTS historico_contatos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id TEXT NOT NULL,
                tipo TEXT NOT NULL,
                descricao TEXT NOT NULL,
                origem TEXT NOT NULL,
                usuario TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (cliente_id) REFERENCES clientes(cliente_id)
            );

            CREATE TABLE IF NOT EXISTS ja_liguei (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id TEXT NOT NULL,
                usuario TEXT,
                origem TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (cliente_id) REFERENCES clientes(cliente_id)
            );

            CREATE TABLE IF NOT EXISTS orcamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id TEXT NOT NULL,
                numero TEXT NOT NULL,
                data TEXT NOT NULL,
                valor REAL DEFAULT 0,
                situacao TEXT NOT NULL,
                responsavel TEXT,
                observacoes TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (cliente_id) REFERENCES clientes(cliente_id)
            );
            """
        )
        if conn.execute("SELECT COUNT(*) FROM clientes").fetchone()[0] == 0:
            seed_demo_data(conn)


def seed_demo_data(conn: sqlite3.Connection) -> None:
    today = date.today()
    clientes = [
        ("CLI-001", "Grafica Horizonte", "Ana", "Ana", "(11) 90000-1001", "compras@horizonte.com", today - timedelta(days=18), 18500, 42000, "Ativo", 18, "Recompra de embalagens"),
        ("CLI-002", "Mercado Sol", "Bruna", "Bruna", "(11) 90000-1002", "financeiro@mercadosol.com", today - timedelta(days=74), 9200, 28000, "Inativo", 71, "Recuperar contrato mensal"),
        ("CLI-003", "Clínica Vida", "Carla", "Carla", "(11) 90000-1003", "adm@clinicavida.com", today - timedelta(days=43), 12600, 19000, "Atenção", 49, "Follow-up de orçamento"),
        ("CLI-004", "Padaria Central", "Ana", "Ana", "(11) 90000-1004", "pedidos@padariacentral.com", today - timedelta(days=11), 6400, 8500, "Ativo", 12, "Reposição de sacolas"),
        ("CLI-005", "Studio Lumina", "Bruna", "Bruna", "(11) 90000-1005", "contato@studiolumina.com", today - timedelta(days=96), 4500, 17500, "Churn", 88, "Reativação"),
    ]
    conn.executemany(
        """
        INSERT INTO clientes (
            cliente_id, nome, responsavel, vendedora, telefone, email, ultima_compra,
            valor_mensal, potencial_recuperavel, status, score_risco, proxima_acao
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (cid, nome, resp, vend, tel, email, dt.isoformat(), mensal, rec, status, risco, acao)
            for cid, nome, resp, vend, tel, email, dt, mensal, rec, status, risco, acao in clientes
        ],
    )
    now = datetime.now().isoformat(timespec="seconds")
    conn.executemany(
        """
        INSERT INTO orcamentos (cliente_id, numero, data, valor, situacao, responsavel, observacoes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ("CLI-001", "ORC-2401", today.isoformat(), 12800, "Em negociação", "Ana", "Cliente pediu prazo.", now),
            ("CLI-003", "ORC-2402", (today - timedelta(days=5)).isoformat(), 7600, "Sem retorno", "Carla", "Enviar nova proposta.", now),
            ("CLI-005", "ORC-2403", (today - timedelta(days=12)).isoformat(), 5300, "Pendente", "Bruna", "Reativação com desconto.", now),
        ],
    )


def rows(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with get_connection() as conn:
        return [dict(row) for row in conn.execute(query, params).fetchall()]


def execute(query: str, params: tuple[Any, ...] = ()) -> int:
    with get_connection() as conn:
        cur = conn.execute(query, params)
        conn.commit()
        return int(cur.lastrowid or 0)


def listar_clientes() -> list[dict[str, Any]]:
    return rows("SELECT * FROM clientes ORDER BY nome")


def obter_cliente(cliente_id: str) -> dict[str, Any] | None:
    result = rows("SELECT * FROM clientes WHERE cliente_id = ?", (cliente_id,))
    return result[0] if result else None


def salvar_observacao(cliente_id: str, texto: str, origem: str, usuario: str) -> int:
    created_at = datetime.now().isoformat(timespec="seconds")
    obs_id = execute(
        "INSERT INTO observacoes (cliente_id, texto, origem, usuario, created_at) VALUES (?, ?, ?, ?, ?)",
        (cliente_id, texto.strip(), origem, usuario.strip(), created_at),
    )
    registrar_historico(cliente_id, "Observação", texto.strip(), origem, usuario)
    return obs_id


def listar_observacoes(cliente_id: str) -> list[dict[str, Any]]:
    return rows(
        "SELECT * FROM observacoes WHERE cliente_id = ? ORDER BY created_at DESC",
        (cliente_id,),
    )


def salvar_agendamento(cliente_id: str, data: str, hora: str, observacao: str, origem: str, usuario: str) -> int:
    created_at = datetime.now().isoformat(timespec="seconds")
    agenda_id = execute(
        """
        INSERT INTO agendamentos (cliente_id, data, hora, observacao, origem, usuario, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (cliente_id, data, hora, observacao.strip(), origem, usuario.strip(), created_at),
    )
    registrar_historico(cliente_id, "Agendamento", f"{data} {hora} - {observacao}".strip(), origem, usuario)
    return agenda_id


def listar_agendamentos(cliente_id: str | None = None) -> list[dict[str, Any]]:
    if cliente_id:
        return rows(
            "SELECT * FROM agendamentos WHERE cliente_id = ? ORDER BY data, hora",
            (cliente_id,),
        )
    return rows(
        """
        SELECT a.*, c.nome, c.responsavel, c.vendedora
        FROM agendamentos a
        JOIN clientes c ON c.cliente_id = a.cliente_id
        ORDER BY a.data, a.hora
        """
    )


def marcar_ja_liguei(cliente_id: str, usuario: str, origem: str) -> int:
    created_at = datetime.now().isoformat(timespec="seconds")
    call_id = execute(
        "INSERT INTO ja_liguei (cliente_id, usuario, origem, created_at) VALUES (?, ?, ?, ?)",
        (cliente_id, usuario.strip(), origem, created_at),
    )
    registrar_historico(cliente_id, "Já liguei", "Contato marcado como realizado.", origem, usuario)
    return call_id


def listar_ja_liguei(cliente_id: str | None = None) -> list[dict[str, Any]]:
    if cliente_id:
        return rows("SELECT * FROM ja_liguei WHERE cliente_id = ? ORDER BY created_at DESC", (cliente_id,))
    return rows(
        """
        SELECT j.*, c.nome, c.responsavel, c.vendedora
        FROM ja_liguei j
        JOIN clientes c ON c.cliente_id = j.cliente_id
        ORDER BY j.created_at DESC
        """
    )


def registrar_historico(cliente_id: str, tipo: str, descricao: str, origem: str, usuario: str) -> int:
    return execute(
        """
        INSERT INTO historico_contatos (cliente_id, tipo, descricao, origem, usuario, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (cliente_id, tipo, descricao, origem, usuario.strip(), datetime.now().isoformat(timespec="seconds")),
    )


def listar_historico_cliente(cliente_id: str) -> list[dict[str, Any]]:
    return rows(
        "SELECT * FROM historico_contatos WHERE cliente_id = ? ORDER BY created_at DESC",
        (cliente_id,),
    )


def salvar_orcamento(
    cliente_id: str,
    numero: str,
    data: str,
    valor: float,
    situacao: str,
    responsavel: str,
    observacoes: str,
) -> int:
    orc_id = execute(
        """
        INSERT INTO orcamentos (cliente_id, numero, data, valor, situacao, responsavel, observacoes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            cliente_id,
            numero.strip(),
            data,
            float(valor),
            situacao,
            responsavel.strip(),
            observacoes.strip(),
            datetime.now().isoformat(timespec="seconds"),
        ),
    )
    registrar_historico(cliente_id, "Orçamento", f"{numero} - {situacao} - R$ {valor:,.2f}", "Gerador de Orçamentos", responsavel)
    return orc_id


def listar_orcamentos(cliente_id: str | None = None) -> list[dict[str, Any]]:
    if cliente_id:
        return rows(
            "SELECT * FROM orcamentos WHERE cliente_id = ? ORDER BY data DESC",
            (cliente_id,),
        )
    return rows(
        """
        SELECT o.*, c.nome, c.status
        FROM orcamentos o
        JOIN clientes c ON c.cliente_id = o.cliente_id
        ORDER BY o.data DESC
        """
    )
