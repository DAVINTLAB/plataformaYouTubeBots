# Backend — Guia para Agentes de IA

Contexto específico do backend para desenvolvimento assistido por IA.
As regras gerais do projeto estão em `CLAUDE.md` na raiz — leia-o primeiro.

## Runtime e entrypoint

- **Python 3.11+**, FastAPI, rodando no Vercel via `@vercel/python`
- Entrypoint: `backend/main.py` — exporta a instância `app = FastAPI()`
- Configurações de runtime do Vercel em `backend/vercel.json`

## Estrutura de rotas

Cada router mapeia para um User Story (US) específico:

| Arquivo              | US    | Responsabilidade                          |
|----------------------|-------|-------------------------------------------|
| `routers/auth.py`    | US-01 | Login, logout, gestão de usuários         |
| `routers/collect.py` | US-02 | Coleta de comentários via YouTube API     |
| `routers/clean.py`   | US-03 | Limpeza e seleção de dataset              |
| `routers/annotate.py`| US-04 | Anotação de comentários                   |
| `routers/review.py`  | US-05 | Desempate de conflitos (admin)            |
| `routers/dashboard.py`| US-06| Dados para o dashboard Plotly             |

## Camadas da aplicação

- `models/` — classes SQLAlchemy (mapeamento para tabelas PostgreSQL)
- `schemas/` — modelos Pydantic para validação de entrada/saída
- `services/` — lógica de negócio, sem acesso direto à camada HTTP
- `routers/` — endpoints: validação de entrada, chamada de service, resposta HTTP

Nunca coloque lógica de negócio diretamente nos routers. Use services.

## Banco de dados

- **Produção:** Neon (PostgreSQL serverless) — free tier, 0.5 GB, scale-to-zero
- **Local:** PostgreSQL via Docker Compose (`docker compose up -d`)
- **Migrations:** Alembic (`alembic upgrade head`)
- `DATABASE_URL` é injetada automaticamente pelo Vercel via integração com Neon

## Autenticação e autorização

- JWT assinado com `python-jose`, senha com `passlib[bcrypt]`
- Variáveis: `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES` (padrão: 60)
- Papéis (roles):
  - `admin` — obrigatório para rotas `/review/*`
  - `master` — obrigatório para rotas `/users/*` (criação de contas)
  - Outros usuários acessam apenas endpoints de coleta, limpeza e anotação

## Regras de negócio críticas

- **API keys externas** (YouTube Data API v3, SocialBlade) são recebidas por requisição
  como `SecretStr` — nunca persistidas em banco, log ou variável de ambiente
- **Anotação `bot`** exige campo `justificativa` preenchido — retorna HTTP 422 se ausente
- **Conflito de anotação** ocorre quando dois anotadores divergem — não há resolução por maioria, toda divergência exige decisão explícita do admin (US-05)
- **Classificações válidas:** `bot` ou `humano` (sem `incerto`)
- **Datasets:** nomeados como `{idVideo}_{critérios}` — ex: `abc123_media`
- Apenas comentários selecionados (suspeitos) são persistidos — excluídos não são armazenados
- Timeout de 10s no Vercel free tier — operações longas (coleta, limpeza) devem ser assíncronas ou paginadas

## Qualidade e segurança

```bash
cd backend

# Lint e formatação
ruff check .
ruff format --check .

# Análise estática de segurança
bandit -r .

# Auditoria de dependências
pip-audit

# Testes (cobertura mínima 80%)
pytest
```

Nunca commitar código que falhe em qualquer um desses checks.

## Comandos de desenvolvimento

```bash
cd backend

# Servidor local
uvicorn main:app --reload

# Migrations
alembic upgrade head

# Novo revision de migration
alembic revision --autogenerate -m "descrição"
```

## Convenções de código

- Schemas Pydantic para toda entrada/saída de endpoints — sem dicts soltos
- `SecretStr` para qualquer valor sensível recebido por requisição
- Dependências FastAPI (`Depends`) para injeção de sessão de banco e usuário autenticado
- Testes em `tests/` com Pytest — fixtures em `tests/conftest.py`
- Cobertura mínima de 80% obrigatória no CI
