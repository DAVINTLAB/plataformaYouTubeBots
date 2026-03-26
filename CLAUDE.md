# Plataforma de Análise de Comentários e Detecção de Bots no YouTube

Sistema de detecção de bots em comentários do YouTube para pesquisa científica (Iniciação Científica — DaVint Lab / PUCRS).

## Stack

- **Backend:** Python 3.11+ · FastAPI · SQLAlchemy · Alembic · Pytest
- **Backend — qualidade e segurança:** Ruff (linter + formatter) · Bandit (análise estática) · pip-audit (auditoria de dependências)
- **Frontend:** React 18 · TypeScript · Vite · Plotly.js
- **Frontend — qualidade e segurança:** ESLint · Prettier · npm audit (auditoria de dependências)
- **Dependências (ambos):** Dependabot ativo no GitHub — PRs automáticos para atualizações de segurança
- **Auth:** JWT + bcrypt (python-jose + passlib)
- **Banco:** Neon (PostgreSQL serverless) — free tier, 0.5 GB, scale-to-zero
- **Deploy:** Vercel — dois projetos separados
  - Frontend: projeto Vercel padrão (Vite + React), domínio próprio
  - Backend: projeto Vercel separado com `@vercel/python`, domínio próprio, timeout 10s no free tier
  - Frontend consome backend via variável de ambiente `VITE_API_URL`

## Estrutura

```
botwatch/
├── backend/
│   ├── main.py               # entrypoint Vercel (@vercel/python)
│   ├── vercel.json           # configuração do runtime Python no Vercel
│   ├── requirements.txt
│   ├── routers/              # endpoints por domínio
│   │   ├── auth.py           # US-01 — login, logout, gestão de usuários
│   │   ├── collect.py        # US-02 — coleta de comentários YouTube
│   │   ├── clean.py          # US-03 — limpeza e seleção de dataset
│   │   ├── annotate.py       # US-04 — anotação de comentários
│   │   ├── review.py         # US-05 — desempate pelo admin
│   │   └── dashboard.py      # US-06 — dashboard Plotly
│   ├── services/             # lógica de negócio
│   ├── models/               # modelos SQLAlchemy (tabelas)
│   ├── schemas/              # modelos Pydantic (validação)
│   └── tests/                # testes Pytest
└── frontend/
    ├── src/
    │   ├── pages/            # telas por US
    │   ├── components/       # componentes reutilizáveis
    │   └── api/              # chamadas ao backend (fetch/axios)
    └── vite.config.ts
```

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

- Conflito de anotação ocorre automaticamente quando dois anotadores divergem — sem resolução por maioria
- Toda divergência exige decisão explícita do admin via US-05
- Classificações possíveis na anotação: `bot` ou `humano` (sem `incerto`)
- Desempate registra autoria (admin) e timestamp