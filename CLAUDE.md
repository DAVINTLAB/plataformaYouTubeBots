# Plataforma de Análise de Comentários e Detecção de Bots no YouTube

Sistema de detecção de bots em comentários do YouTube para pesquisa científica (Iniciação Científica — DaVint Lab / PUCRS).

## Stack

- **Backend:** Python 3.11+ · FastAPI · SQLAlchemy · Alembic · Pytest
- **Backend — qualidade e segurança:** Ruff (linter + formatter) · Bandit (análise estática) · pip-audit (auditoria de dependências)
- **Frontend:** React 18 · TypeScript · Vite · Plotly.js · Tailwind CSS v3
- **Frontend — qualidade e segurança:** ESLint · Prettier · npm audit (auditoria de dependências)
- **Dependências (ambos):** Dependabot ativo no GitHub — PRs automáticos para atualizações de segurança
- **Auth:** JWT + bcrypt (python-jose + passlib) — access token (60min) + refresh token (7 dias)
- **Banco:** Neon (PostgreSQL serverless) — free tier, 0.5 GB, scale-to-zero
- **Deploy:** Vercel — dois projetos separados
  - Frontend: projeto Vercel padrão (Vite + React), domínio próprio
  - Backend: projeto Vercel separado com `@vercel/python`, domínio próprio, Vercel Pro (maxDuration 60s)
  - Frontend consome backend via variável de ambiente `VITE_API_URL`

## Arquitetura

Arquitetura em Camadas com princípios de Clean Architecture aplicados onde agrega valor. As camadas só se comunicam na direção: `routers → services → repositories → models`.

```
/
├── backend/
│   ├── main.py               # entrypoint Vercel (@vercel/python)
│   ├── vercel.json
│   ├── requirements.txt
│   ├── routers/              # Camada de apresentação — HTTP, validação entrada/saída
│   │   ├── auth.py           # US-01
│   │   ├── collect.py        # US-02
│   │   ├── clean.py          # US-03
│   │   ├── annotate.py       # US-04
│   │   ├── review.py         # US-05
│   │   └── dashboard.py      # US-06
│   ├── services/             # Camada de aplicação — regras de negócio, orquestração
│   │   ├── auth.py
│   │   ├── collect.py
│   │   ├── clean/            # algoritmos de seleção (OCP — cada critério é uma classe)
│   │   │   ├── base.py       # SelectorBase (ABC)
│   │   │   ├── percentile.py
│   │   │   ├── mean.py
│   │   │   ├── median.py
│   │   │   ├── mode.py
│   │   │   ├── short_comments.py
│   │   │   ├── time_interval.py
│   │   │   ├── identical.py
│   │   │   └── profile.py
│   │   ├── annotate.py
│   │   ├── review.py
│   │   └── dashboard.py
│   ├── repositories/         # Camada de acesso a dados — isola o banco dos serviços
│   │   ├── base.py           # RepositoryBase (ABC)
│   │   ├── user.py
│   │   ├── comment.py
│   │   ├── dataset.py
│   │   ├── annotation.py
│   │   └── resolution.py
│   ├── models/               # Entidades SQLAlchemy
│   ├── schemas/              # DTOs Pydantic — entrada e saída de cada endpoint
│   ├── core/                 # Configurações, segurança, dependências compartilhadas
│   │   ├── config.py         # variáveis de ambiente via pydantic-settings
│   │   ├── security.py       # JWT, bcrypt
│   │   └── dependencies.py   # get_db, get_current_user, require_admin, require_master
│   └── tests/
└── frontend/
    └── src/
        ├── pages/            # telas por US
        ├── components/       # componentes reutilizáveis — obrigatório para qualquer elemento usado em 2+ páginas
        │   ├── PageHeader.tsx    # header padrão (logo, breadcrumb, usuário) — obrigatório em toda página autenticada
        │   ├── StatusBadge.tsx   # badge colorido de status de coleta
        │   ├── ProgressBar.tsx   # barra de progresso determinada ou indeterminada
        │   └── ProtectedRoute.tsx
        ├── hooks/            # lógica isolada em hooks (useAnnotation, useClean, etc.)
        ├── contexts/         # AuthContext — token, user (username + name + role), isAdmin
        └── api/              # chamadas ao backend — componentes nunca fazem fetch diretamente (DIP)
            └── http.ts       # request() centralizado — trata erros 422 (detail array → string)
```

## Princípios SOLID

Aplicados em backend e frontend.

**SRP — Single Responsibility**
- Backend: `routers/` só lida com HTTP, `services/` só orquestra lógica, `repositories/` só acessa o banco
- Frontend: componentes têm responsabilidade visual; lógica de negócio fica em hooks customizados
- Frontend — componentização obrigatória: qualquer elemento visual usado em 2+ páginas **deve** viver em `components/`; páginas nunca reimplementam inline o que já existe como componente (header, badges, barras de progresso)

**OCP — Open/Closed**
- Algoritmos de limpeza da US-03 implementam `SelectorBase` — adicionar novo critério = nova classe, sem modificar as existentes
- Componentes de gráfico Plotly recebem `data` e `layout` como props — extensíveis sem modificação

**LSP — Liskov Substitution**
- Qualquer implementação de `SelectorBase` ou `RepositoryBase` pode ser substituída sem quebrar o sistema
- Repositórios reais substituídos por mocks nos testes implementando a mesma interface

**ISP — Interface Segregation**
- Repositórios com interfaces específicas por domínio (`CommentRepository`, `UserRepository`, `DatasetRepository`) — sem interface genérica com métodos desnecessários

**DIP — Dependency Inversion**
- Backend: serviços recebem repositórios injetados via construtor — nunca os instanciam; FastAPI injeta via `Depends()`
- Frontend: componentes consomem dados via hooks e `api/` — nunca fazem `fetch` diretamente

## Banco de dados

**Regra absoluta: nunca usar SQLite — nem em testes.**

| Ambiente | Banco | Como configurar |
|----------|-------|-----------------|
| Desenvolvimento local | PostgreSQL via Docker Compose | `docker compose up -d` → `DATABASE_URL=postgresql://davint:davint@localhost:5432/davint` |
| Testes locais | PostgreSQL via Docker Compose (banco `davint_test`) | `DATABASE_URL=postgresql://davint:davint@localhost:5432/davint` (conftest deriva `davint_test` automaticamente) |
| CI/CD (GitHub Actions) | PostgreSQL service container | definir `DATABASE_URL` no workflow |
| Produção (Vercel) | Neon PostgreSQL serverless | injetado automaticamente via integração Neon |

Os testes usam transações com `join_transaction_mode="create_savepoint"` — cada teste roda num SAVEPOINT que é revertido ao final, sem deixar dados residuais. É o equivalente Python ao H2 in-memory do ecossistema Java.

## Comandos

```bash
# Pré-requisito: Docker rodando
docker compose up -d

# Backend — sem --reload no Windows (StatReload não recarrega módulos corretamente)
cd backend
source .venv/Scripts/activate
DATABASE_URL=postgresql://davint:davint@localhost:5432/davint uvicorn main:app --port 8000

# Testes — PostgreSQL obrigatório, davint_test criado automaticamente pelo conftest
cd backend
DATABASE_URL=postgresql://davint:davint@localhost:5432/davint pytest

# Migrations
cd backend && DATABASE_URL=postgresql://davint:davint@localhost:5432/davint alembic upgrade head

# Frontend
cd frontend && npm run dev                  # dev local
cd frontend && npm run build               # build produção
```

## Variáveis de ambiente

```env
# Injetadas automaticamente pelo Vercel via integração com Neon
DATABASE_URL=postgresql://...

# Configurar manualmente no Vercel Dashboard > Environment Variables
SECRET_KEY=...          # chave para assinar JWTs
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Frontend
VITE_API_URL=https://<backend-projeto>.vercel.app
```

## Qualidade e segurança

### Pre-commit hooks (local)

Todo commit deve passar por:

```bash
# Backend
ruff check .          # lint
ruff format --check . # format
bandit -r .           # análise estática de segurança

# Frontend
eslint . --ext .ts,.tsx
prettier --check .
```

Configurar via `.pre-commit-config.yaml` na raiz do repositório.

### CI/CD (GitHub Actions — a cada push)

Pipeline `.github/workflows/ci.yml` deve executar:

```
Backend:
  - ruff check + ruff format --check
  - bandit -r backend/
  - pip-audit (falha se houver vulnerabilidade conhecida)
  - pytest (cobertura mínima 80%)

Frontend:
  - eslint
  - prettier --check
  - npm audit --audit-level=high (falha se severidade alta ou crítica)
  - tsc --noEmit (checagem de tipos)
```

### Dependabot

Arquivo `.github/dependabot.yml` configurado para:
- `pip` no diretório `backend/` — frequência semanal
- `npm` no diretório `frontend/` — frequência semanal
- PRs automáticos para vulnerabilidades de segurança com merge automático para patches

## Convenções

- Senhas sempre com bcrypt via `passlib` — nunca texto plano
- API keys (YouTube Data API v3, SocialBlade) recebidas por requisição como `SecretStr` — nunca persistidas em banco, log ou variável de ambiente
- Endpoints protegidos exigem `Authorization: Bearer <token>` no header
- Papel `admin` obrigatório para rotas `/review/*`
- Papel `master` obrigatório para rotas `/users/*` (criação de contas)
- Rótulo `bot` na anotação exige campo `justificativa` preenchido — validado no backend (HTTP 422) e bloqueado no frontend
- Datasets nomeados como `{idVideo}_{critérios}` — ex: `abc123_media`, `abc123_percentil_intervalo`
- Apenas datasets selecionados (suspeitos) são persistidos — excluídos não são armazenados
- Vercel Pro com `maxDuration: 60` no `vercel.json` — timeout httpx de 15s
- Coletas são compartilhadas — todos os usuários veem todas as coletas (sem filtro por `collected_by`)
- Enriquecimento pós-coleta separado em endpoint `POST /collect/{id}/enrich` com 3 fases (video, replies, channels)
- Bulk insert com `ON CONFLICT DO NOTHING` — nunca SELECT+INSERT um a um
- Canais não retornados pela YouTube API recebem epoch (1970-01-01) para evitar loop infinito
- Refresh token (7 dias) no `localStorage`, access token (60min) no `sessionStorage` — interceptor transparente no `http.ts`
- API keys pessoais e intransferíveis — avisos obrigatórios em CollectPage, UsersPage e CreateUserModal
- **Cards de instrução obrigatórios em páginas de US**: toda página de US deve orientar o usuário em cada etapa do fluxo — use `<StepsCard>` no estado inicial, notice `bg-davint-50` durante processamento ativo, banner `bg-yellow-50` para estados interrompidos, CTA claro ao concluir. Ver `.claude/frontend.md` § "Cards de instrução por etapa"

## Regras de negócio críticas

- Remoção de usuário é sempre **soft-delete** (`is_active = False`) — nunca DELETE físico, para preservar anotações de quem sai do laboratório
- Admin pode reativar usuário inativo via `POST /users/{id}/reactivate`
- `GET /users/` retorna todos os usuários (ativos e inativos); frontend ordena ativos primeiro
- Conflito de anotação ocorre automaticamente quando dois anotadores divergem — sem resolução por maioria
- Toda divergência exige decisão explícita do admin via US-05
- Classificações possíveis na anotação: `bot` ou `humano` (sem `incerto`)
- Desempate registra autoria (admin) e timestamp