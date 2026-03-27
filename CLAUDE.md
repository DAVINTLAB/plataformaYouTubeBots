# Plataforma de Análise de Comentários e Detecção de Bots no YouTube

Sistema de detecção de bots em comentários do YouTube para pesquisa científica (Iniciação Científica — DaVint Lab / PUCRS).

## Stack

- **Backend:** Python 3.11+ · FastAPI · SQLAlchemy · Alembic · Pytest
- **Backend — qualidade e segurança:** Ruff (linter + formatter) · Bandit (análise estática) · pip-audit (auditoria de dependências)
- **Frontend:** React 18 · TypeScript · Vite · Plotly.js · Tailwind CSS v3
- **Frontend — qualidade e segurança:** ESLint · Prettier · npm audit (auditoria de dependências)
- **Dependências (ambos):** Dependabot ativo no GitHub — PRs automáticos para atualizações de segurança
- **Auth:** JWT + bcrypt (python-jose + passlib)
- **Banco:** Neon (PostgreSQL serverless) — free tier, 0.5 GB, scale-to-zero
- **Deploy:** Vercel — dois projetos separados
  - Frontend: projeto Vercel padrão (Vite + React), domínio próprio
  - Backend: projeto Vercel separado com `@vercel/python`, domínio próprio, timeout 10s no free tier
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
        ├── components/       # componentes reutilizáveis (SRP — uma responsabilidade visual)
        ├── hooks/            # lógica isolada em hooks (useAnnotation, useClean, etc.)
        └── api/              # chamadas ao backend — componentes nunca fazem fetch diretamente (DIP)
```

## Princípios SOLID

Aplicados em backend e frontend.

**SRP — Single Responsibility**
- Backend: `routers/` só lida com HTTP, `services/` só orquestra lógica, `repositories/` só acessa o banco
- Frontend: componentes têm responsabilidade visual; lógica de negócio fica em hooks customizados

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

## Comandos

```bash
# Backend
cd backend && uvicorn main:app --reload     # dev local
cd backend && pytest                        # testes
cd backend && alembic upgrade head          # migrations

# Frontend
cd frontend && npm run dev                  # dev local
cd frontend && npm run build               # build produção

# Banco local (desenvolvimento)
docker compose up -d                        # sobe PostgreSQL local via Docker
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
- Timeout de 10s por request no Vercel free tier — operações longas (coleta, limpeza) devem ser assíncronas ou paginadas

## Regras de negócio críticas

- Remoção de usuário é sempre **soft-delete** (`is_active = False`) — nunca DELETE físico, para preservar anotações de quem sai do laboratório
- Admin pode reativar usuário inativo via `POST /users/{id}/reactivate`
- `GET /users/` retorna todos os usuários (ativos e inativos); frontend ordena ativos primeiro
- Conflito de anotação ocorre automaticamente quando dois anotadores divergem — sem resolução por maioria
- Toda divergência exige decisão explícita do admin via US-05
- Classificações possíveis na anotação: `bot` ou `humano` (sem `incerto`)
- Desempate registra autoria (admin) e timestamp