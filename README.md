# Plataforma de Análise de Comentários e Detecção de Bots no YouTube

Sistema de coleta, limpeza, anotação e análise de comentários do YouTube para detecção de bots, desenvolvido no **DaVint Lab / PUCRS** como projeto de Iniciação Científica.

## Visão geral

A plataforma permite que pesquisadores:
1. Coletem comentários de vídeos do YouTube via API
2. Filtrem usuários suspeitos com critérios estatísticos e comportamentais
3. Anotem comentários colaborativamente como `bot` ou `humano`
4. Resolvam conflitos de classificação via painel do administrador
5. Visualizem métricas e gráficos sobre os dados anotados

## Stack

| Camada    | Tecnologia                                              |
|-----------|---------------------------------------------------------|
| Backend   | Python 3.11 · FastAPI · SQLAlchemy · Alembic            |
| Frontend  | React 18 · TypeScript · Vite · Plotly.js                |
| Banco     | PostgreSQL (Neon serverless — free tier)                |
| Auth      | JWT · bcrypt (python-jose + passlib)                    |
| Deploy    | Vercel (dois projetos separados: frontend e backend)    |
| CI/CD     | GitHub Actions · Dependabot                             |

## Estrutura do repositório

```
plataformaYouTubeBots/
├── backend/               # API FastAPI
│   ├── main.py            # entrypoint Vercel
│   ├── routers/           # endpoints por User Story
│   ├── services/          # lógica de negócio
│   ├── models/            # modelos SQLAlchemy
│   ├── schemas/           # modelos Pydantic
│   └── tests/             # testes Pytest
├── frontend/              # SPA React + TypeScript
│   └── src/
│       ├── pages/         # telas por User Story
│       ├── components/    # componentes reutilizáveis
│       └── api/           # chamadas ao backend
├── .claude/               # contexto para agentes de IA
│   ├── backend.md
│   ├── frontend.md
│   └── skills/            # guias de implementação por US
├── .github/
│   ├── workflows/ci.yml   # pipeline de CI/CD
│   ├── dependabot.yml     # atualizações automáticas
│   └── CONTRIBUTING.md    # guia de contribuição
├── AGENTS.md              # instruções para agentes de IA
├── CLAUDE.md              # convenções do projeto
└── docker-compose.yml     # PostgreSQL local para desenvolvimento
```

## User Stories

| US    | Descrição                              | Rota backend       |
|-------|----------------------------------------|--------------------|
| US-00 | Infraestrutura, CI/CD e segurança      | —                  |
| US-01 | Autenticação e gestão de usuários      | `/auth`, `/users`  |
| US-02 | Coleta de comentários do YouTube       | `/collect`         |
| US-03 | Limpeza e seleção de dataset           | `/clean`           |
| US-04 | Anotação de comentários                | `/annotate`        |
| US-05 | Desempate de conflitos (admin)         | `/review`          |
| US-06 | Dashboard de análise                   | `/dashboard`       |

## Desenvolvimento local

### Pré-requisitos

- Python 3.11+
- Node.js 24+
- Docker (para o banco local)

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # preencher variáveis
docker compose up -d          # sobe PostgreSQL local
alembic upgrade head          # aplica migrations
uvicorn main:app --reload     # http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local    # preencher VITE_API_URL
npm run dev                   # http://localhost:5173
```

### Testes

```bash
cd backend && pytest           # cobertura mínima 80%
```

## Variáveis de ambiente

| Variável                      | Onde           | Descrição                              |
|-------------------------------|----------------|----------------------------------------|
| `DATABASE_URL`                | Backend        | URL do PostgreSQL (Neon em produção)   |
| `SECRET_KEY`                  | Backend        | Chave de assinatura dos JWTs           |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Backend        | Expiração do token (padrão: 60)        |
| `VITE_API_URL`                | Frontend       | URL do backend em produção             |

Em produção, `DATABASE_URL` é injetada automaticamente pela integração Vercel + Neon.
As demais são configuradas em **Vercel Dashboard > Environment Variables**.

## Branches (Gitflow)

```
main      produção — releases estáveis
dev       integração — alvo de PRs de feature
feature/* desenvolvimento de US ou tarefa
hotfix/*  correção urgente em produção
```

Ver [CONTRIBUTING.md](.github/CONTRIBUTING.md) para o fluxo completo.

## Qualidade e segurança

O CI executa automaticamente em todo push e PR:

- **Backend:** Ruff · Bandit · pip-audit · Pytest (≥ 80% cobertura)
- **Frontend:** ESLint · Prettier · tsc · npm audit

## Licença

Projeto acadêmico — DaVint Lab / PUCRS. Uso restrito à pesquisa científica.
