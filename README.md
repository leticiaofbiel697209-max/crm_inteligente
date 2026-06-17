# Novaprint - Plataforma Comercial Streamlit

Aplicacao Streamlit unificada para:

- Dashboard CEO
- CRM
- Portal das Vendedoras
- Gerador de Orcamentos
- Relatorios
- Churn
- Base de Clientes
- Configuracoes

## Rodar localmente

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

Ou:

```bash
./run_app.sh
```

Depois abra:

```text
http://localhost:8501
```

## Publicar no Streamlit Cloud

1. Suba estes arquivos para um repositorio no GitHub.
2. Acesse https://share.streamlit.io
3. Clique em `Create app`.
4. Escolha o repositorio.
5. Branch: `main`
6. Main file path: `app.py`
7. Clique em `Deploy`.

## Secrets de API

Nao coloque tokens no GitHub.

No Streamlit Cloud, va em:

```text
App > Settings > Secrets
```

E cadastre:

```toml
[gestaoclick]
access_token = "SEU_ACCESS_TOKEN"
secret_token = "SEU_SECRET_TOKEN"
```

Para testar localmente, crie:

```text
.streamlit/secrets.toml
```

Com o mesmo conteudo acima. Esse arquivo esta no `.gitignore`.

## Persistencia

O MVP usa SQLite local em `database/novaprint.db`, criado automaticamente quando o app inicia.

No Streamlit Cloud, arquivos locais podem ser recriados quando o app reinicia. Para persistencia permanente online, use Google Sheets, Supabase, PostgreSQL ou outro banco externo.
